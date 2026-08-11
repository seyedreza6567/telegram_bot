import pandas as pd
import numpy as np

from scanner import get_klines
from analysis_engine import analyze


# =========================================================
# تنظیمات اصلی
# =========================================================

SYMBOLS = [
    "BTC-SWAP-USDT",
    "ETH-SWAP-USDT",
    "BNB-SWAP-USDT",
    "SOL-SWAP-USDT",
    "XRP-SWAP-USDT",
    "DOGE-SWAP-USDT",
    "ADA-SWAP-USDT",
    "LINK-SWAP-USDT",
    "DOT-SWAP-USDT",
    "LTC-SWAP-USDT",
    "UNI-SWAP-USDT",
    "SUI-SWAP-USDT",
    "AVAX-SWAP-USDT",
]

TIMEFRAME = "1h"

CANDLE_LIMIT = 1000

MIN_CANDLES = 250

# درصد داده برای پیدا کردن تنظیمات
TRAIN_PERCENT = 0.60

# فقط سیگنال‌هایی که حداقل این امتیاز را دارند
MIN_SCORES = [6, 7, 8, 9]

# فاصله حد ضرر بر اساس ATR
STOP_MULTIPLIERS = [
    1.5,
    1.75,
    2.0,
    2.25,
]

# TP2 بر اساس ATR
TP_MULTIPLIERS = [
    3.0,
    3.5,
    4.0,
    4.5,
]

# حداقل تعداد معاملات برای اینکه یک تنظیم معتبر باشد
MIN_TRADES = 8


# =========================================================
# محاسبه نتیجه معامله
# =========================================================

def check_trade_result(
    df,
    entry_index,
    signal,
    stop_loss,
    tp1,
    tp2
):

    for i in range(
        entry_index + 1,
        len(df)
    ):

        candle = df.iloc[i]

        high = float(candle["high"])
        low = float(candle["low"])

        if signal == "LONG":

            hit_sl = low <= stop_loss
            hit_tp2 = high >= tp2
            hit_tp1 = high >= tp1

            # حالت محافظه کارانه
            if hit_sl and (
                hit_tp1 or hit_tp2
            ):
                return "SL"

            if hit_sl:
                return "SL"

            if hit_tp2:
                return "TP2"

            if hit_tp1:
                return "TP1"

        elif signal == "SHORT":

            hit_sl = high >= stop_loss
            hit_tp2 = low <= tp2
            hit_tp1 = low <= tp1

            if hit_sl and (
                hit_tp1 or hit_tp2
            ):
                return "SL"

            if hit_sl:
                return "SL"

            if hit_tp2:
                return "TP2"

            if hit_tp1:
                return "TP1"

    return "OPEN"


# =========================================================
# اجرای بک تست با تنظیمات مشخص
# =========================================================

def run_backtest(
    df,
    min_score,
    stop_multiplier,
    tp_multiplier,
    start_index,
    end_index
):

    trades = []

    tp2_count = 0
    tp1_count = 0
    sl_count = 0
    open_count = 0

    profit_r = 0.0

    i = max(
        MIN_CANDLES,
        start_index
    )

    while i < end_index - 5:

        historical_df = df.iloc[
            :i
        ].copy()

        result = analyze(
            historical_df
        )

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        score = result.get(
            "score",
            0
        )

        # -------------------------------------------------
        # فیلتر امتیاز
        # -------------------------------------------------

        if signal not in [
            "LONG",
            "SHORT"
        ]:

            i += 1
            continue

        if score < min_score:

            i += 1
            continue

        entry = result.get(
            "price"
        )

        atr = result.get(
            "atr"
        )

        if entry is None or atr is None:

            i += 1
            continue

        try:

            entry = float(entry)
            atr = float(atr)

        except Exception:

            i += 1
            continue

        if not np.isfinite(atr):
            i += 1
            continue

        if atr <= 0:
            i += 1
            continue

        # -------------------------------------------------
        # حد ضرر و سود
        # -------------------------------------------------

        stop_distance = (
            atr * stop_multiplier
        )

        tp_distance = (
            atr * tp_multiplier
        )

        # TP1 نصف مسیر TP2
        tp1_distance = (
            tp_distance / 2
        )

        if signal == "LONG":

            stop_loss = (
                entry
                - stop_distance
            )

            tp1 = (
                entry
                + tp1_distance
            )

            tp2 = (
                entry
                + tp_distance
            )

        else:

            stop_loss = (
                entry
                + stop_distance
            )

            tp1 = (
                entry
                - tp1_distance
            )

            tp2 = (
                entry
                - tp_distance
            )

        # -------------------------------------------------
        # نتیجه
        # -------------------------------------------------

        result_trade = check_trade_result(
            df=df,
            entry_index=i,
            signal=signal,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2
        )

        if result_trade == "TP2":

            tp2_count += 1

            # TP2 نسبت به ریسک
            risk_distance = stop_distance

            reward_distance = tp_distance

            r_value = (
                reward_distance
                / risk_distance
            )

            profit_r += r_value

        elif result_trade == "TP1":

            tp1_count += 1

            risk_distance = stop_distance

            reward_distance = tp1_distance

            r_value = (
                reward_distance
                / risk_distance
            )

            profit_r += r_value

        elif result_trade == "SL":

            sl_count += 1

            profit_r -= 1.0

        else:

            open_count += 1

        trades.append({
            "index": i,
            "signal": signal,
            "score": score,
            "entry": entry,
            "stop": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "result": result_trade
        })

        # -------------------------------------------------
        # جلوگیری از معاملات پشت سر هم
        # -------------------------------------------------

        trade_end = i + 1

        while trade_end < end_index:

            candle = df.iloc[
                trade_end
            ]

            high = float(
                candle["high"]
            )

            low = float(
                candle["low"]
            )

            finished = False

            if signal == "LONG":

                if low <= stop_loss:
                    finished = True

                elif high >= tp2:
                    finished = True

                elif high >= tp1:
                    finished = True

            else:

                if high >= stop_loss:
                    finished = True

                elif low <= tp2:
                    finished = True

                elif low <= tp1:
                    finished = True

            if finished:
                break

            trade_end += 1

        i = max(
            i + 1,
            trade_end + 1
        )

    completed = (
        tp2_count
        + tp1_count
        + sl_count
    )

    if completed > 0:

        win_rate = (
            (
                tp2_count
                + tp1_count
            )
            / completed
        ) * 100

    else:

        win_rate = 0.0

    return {
        "trades": len(trades),
        "tp2": tp2_count,
        "tp1": tp1_count,
        "sl": sl_count,
        "open": open_count,
        "win_rate": win_rate,
        "profit_r": profit_r,
        "trade_data": trades
    }


# =========================================================
# پیدا کردن بهترین تنظیمات
# =========================================================

def optimize_symbol(
    symbol,
    df
):

    split = int(
        len(df)
        * TRAIN_PERCENT
    )

    best = None

    print(
        f"\n🔍 بهینه‌سازی {symbol} ..."
    )

    for min_score in MIN_SCORES:

        for stop_multiplier in STOP_MULTIPLIERS:

            for tp_multiplier in TP_MULTIPLIERS:

                result = run_backtest(
                    df=df,
                    min_score=min_score,
                    stop_multiplier=stop_multiplier,
                    tp_multiplier=tp_multiplier,
                    start_index=MIN_CANDLES,
                    end_index=split
                )

                if result["trades"] < MIN_TRADES:
                    continue

                # امتیاز تنظیمات
                #
                # سود بیشتر بهتر
                # معاملات خیلی کم امتیاز نمی‌گیرند
                #

                optimization_score = (
                    result["profit_r"]
                    + (
                        result["win_rate"]
                        / 100
                    )
                )

                candidate = {
                    "min_score": min_score,
                    "stop_multiplier": stop_multiplier,
                    "tp_multiplier": tp_multiplier,
                    "profit_r": result["profit_r"],
                    "win_rate": result["win_rate"],
                    "trades": result["trades"],
                    "tp2": result["tp2"],
                    "tp1": result["tp1"],
                    "sl": result["sl"],
                    "optimization_score":
                        optimization_score
                }

                if (
                    best is None
                    or candidate[
                        "optimization_score"
                    ]
                    >
                    best[
                        "optimization_score"
                    ]
                ):

                    best = candidate

    return best


# =========================================================
# تست نهایی روی داده ندیده
# =========================================================

def validate_symbol(
    symbol,
    df,
    settings
):

    split = int(
        len(df)
        * TRAIN_PERCENT
    )

    result = run_backtest(
        df=df,
        min_score=settings[
            "min_score"
        ],
        stop_multiplier=settings[
            "stop_multiplier"
        ],
        tp_multiplier=settings[
            "tp_multiplier"
        ],
        start_index=split,
        end_index=len(df) - 1
    )

    return result


# =========================================================
# اجرای یک ارز
# =========================================================

def process_symbol(symbol):

    print(
        "\n"
        + "=" * 65
    )

    print(
        f"📊 {symbol}"
    )

    print(
        "=" * 65
    )

    df = get_klines(
        symbol=symbol,
        interval=TIMEFRAME,
        limit=CANDLE_LIMIT
    )

    if df is None:

        print(
            "❌ داده دریافت نشد"
        )

        return None

    if len(df) < MIN_CANDLES + 50:

        print(
            f"❌ داده کافی نیست: "
            f"{len(df)}"
        )

        return None

    df = df.copy()

    # -----------------------------------------------------
    # بهینه سازی
    # -----------------------------------------------------

    best = optimize_symbol(
        symbol,
        df
    )

    if best is None:

        print(
            "⚪ تنظیم مناسب پیدا نشد"
        )

        return None

    print(
        "\n🏆 بهترین تنظیمات:"
    )

    print(
        f"Minimum Score: "
        f"{best['min_score']}"
    )

    print(
        f"ATR Stop: "
        f"{best['stop_multiplier']}"
    )

    print(
        f"ATR TP2: "
        f"{best['tp_multiplier']}"
    )

    print(
        f"Train Trades: "
        f"{best['trades']}"
    )

    print(
        f"Train Win Rate: "
        f"{best['win_rate']:.2f}%"
    )

    print(
        f"Train Profit: "
        f"{best['profit_r']:.2f}R"
    )

    # -----------------------------------------------------
    # تست داده ندیده
    # -----------------------------------------------------

    validation = validate_symbol(
        symbol,
        df,
        best
    )

    print(
        "\n🧪 نتیجه روی داده ندیده:"
    )

    print(
        f"Trades: "
        f"{validation['trades']}"
    )

    print(
        f"TP2: "
        f"{validation['tp2']}"
    )

    print(
        f"TP1: "
        f"{validation['tp1']}"
    )

    print(
        f"SL: "
        f"{validation['sl']}"
    )

    print(
        f"Win Rate: "
        f"{validation['win_rate']:.2f}%"
    )

    print(
        f"Profit: "
        f"{validation['profit_r']:.2f}R"
    )

    return {
        "symbol": symbol,
        "settings": best,
        "validation": validation
    }


# =========================================================
# گزارش نهایی
# =========================================================

def main():

    print(
        "\n"
        + "=" * 65
    )

    print(
        "🚀 BACKTEST + OPTIMIZATION"
    )

    print(
        "=" * 65
    )

    print(
        "\n⏱️ تایم‌فریم:",
        TIMEFRAME
    )

    print(
        "📊 تعداد کندل:",
        CANDLE_LIMIT
    )

    print(
        "🧠 حالت: Train / Validation"
    )

    print(
        "\n⚠️ هیچ سفارش واقعی ارسال نمی‌شود."
    )

    results = []

    for symbol in SYMBOLS:

        try:

            result = process_symbol(
                symbol
            )

            if result is not None:

                results.append(
                    result
                )

        except Exception as e:

            print(
                f"\n❌ خطا در {symbol}"
            )

            print(e)

    # =====================================================
    # رتبه بندی
    # =====================================================

    results.sort(
        key=lambda x:
        x["validation"]["profit_r"],
        reverse=True
    )

    print(
        "\n\n"
        + "=" * 65
    )

    print(
        "🏆 رتبه‌بندی نهایی"
    )

    print(
        "=" * 65
    )

    for number, item in enumerate(
        results,
        start=1
    ):

        symbol = item[
            "symbol"
        ]

        settings = item[
            "settings"
        ]

        validation = item[
            "validation"
        ]

        print(
            f"\n#{number} "
            f"{symbol}"
        )

        print(
            f"💰 Profit: "
            f"{validation['profit_r']:.2f}R"
        )

        print(
            f"🎯 Win Rate: "
            f"{validation['win_rate']:.2f}%"
        )

        print(
            f"📊 Trades: "
            f"{validation['trades']}"
        )

        print(
            f"🟢 TP2: "
            f"{validation['tp2']}"
        )

        print(
            f"🟢 TP1: "
            f"{validation['tp1']}"
        )

        print(
            f"🔴 SL: "
            f"{validation['sl']}"
        )

        print(
            f"⚙️ Score >= "
            f"{settings['min_score']}"
        )

        print(
            f"🛑 ATR Stop = "
            f"{settings['stop_multiplier']}"
        )

        print(
            f"🎯 ATR TP2 = "
            f"{settings['tp_multiplier']}"
        )

    # =====================================================
    # مجموع
    # =====================================================

    total_trades = 0
    total_tp2 = 0
    total_tp1 = 0
    total_sl = 0
    total_profit = 0.0

    for item in results:

        validation = item[
            "validation"
        ]

        total_trades += validation[
            "trades"
        ]

        total_tp2 += validation[
            "tp2"
        ]

        total_tp1 += validation[
            "tp1"
        ]

        total_sl += validation[
            "sl"
        ]

        total_profit += validation[
            "profit_r"
        ]

    completed = (
        total_tp2
        + total_tp1
        + total_sl
    )

    if completed > 0:

        overall_win_rate = (
            (
                total_tp2
                + total_tp1
            )
            / completed
        ) * 100

    else:

        overall_win_rate = 0

    print(
        "\n\n"
        + "=" * 65
    )

    print(
        "📈 گزارش نهایی"
    )

    print(
        "=" * 65
    )

    print(
        f"📊 مجموع معاملات: "
        f"{total_trades}"
    )

    print(
        f"🟢 مجموع TP2: "
        f"{total_tp2}"
    )

    print(
        f"🟢 مجموع TP1: "
        f"{total_tp1}"
    )

    print(
        f"🔴 مجموع SL: "
        f"{total_sl}"
    )

    print(
        f"🎯 Win Rate کلی: "
        f"{overall_win_rate:.2f}%"
    )

    print(
        f"💰 نتیجه کلی: "
        f"{total_profit:.2f}R"
    )

    print(
        "\n"
        + "=" * 65
    )

    if total_profit > 0:

        print(
            "✅ نتیجه تست مثبت است."
        )

    elif total_profit == 0:

        print(
            "⚪ نتیجه تست سر به سر است."
        )

    else:

        print(
            "🔴 نتیجه تست هنوز منفی است."
        )

    print(
        "\n⚠️ نتیجه بک‌تست تضمین سود آینده نیست."
    )


if __name__ == "__main__":

    main()
