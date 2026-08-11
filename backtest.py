import pandas as pd
import numpy as np

from scanner import get_klines
from analysis_engine import analyze


# =========================================================
# تنظیمات بک‌تست
# =========================================================

SYMBOLS = [
    "BTC-SWAP-USDT",
    "ETH-SWAP-USDT",
    "BNB-SWAP-USDT",
    "SOL-SWAP-USDT",
    "XRP-SWAP-USDT",
    "DOGE-SWAP-USDT",
    "ADA-SWAP-USDT",
    "AVAX-SWAP-USDT",
    "LINK-SWAP-USDT",
    "DOT-SWAP-USDT",
    "LTC-SWAP-USDT",
    "UNI-SWAP-USDT",
    "SUI-SWAP-USDT",
]

TIMEFRAME = "1h"

CANDLE_LIMIT = 1000

MIN_TRAIN_CANDLES = 250

ATR_STOP_MULTIPLIER = 2.0

ATR_TP1_MULTIPLIER = 2.0

ATR_TP2_MULTIPLIER = 4.0


# =========================================================
# بررسی نتیجه معامله
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

            # اگر در یک کندل هم SL و هم TP دیده شوند
            # حالت محافظه‌کارانه: SL را اول در نظر می‌گیریم
            if hit_sl and hit_tp2:
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

            if hit_sl and hit_tp2:
                return "SL"

            if hit_sl:
                return "SL"

            if hit_tp2:
                return "TP2"

            if hit_tp1:
                return "TP1"

    return "OPEN"


# =========================================================
# بک‌تست یک ارز
# =========================================================

def backtest_symbol(symbol):

    print("\n" + "=" * 60)
    print(f"BACKTEST: {symbol}")
    print("=" * 60)

    df = get_klines(
        symbol=symbol,
        interval=TIMEFRAME,
        limit=CANDLE_LIMIT
    )

    if df is None:
        print("❌ داده دریافت نشد")
        return None

    if len(df) < MIN_TRAIN_CANDLES + 20:
        print(
            f"❌ داده کافی نیست: {len(df)} کندل"
        )
        return None

    df = df.copy()

    trades = []

    wins_tp2 = 0
    wins_tp1 = 0
    losses = 0
    open_trades = 0

    total_profit_r = 0.0

    # =====================================================
    # حرکت تاریخی
    # =====================================================

    i = MIN_TRAIN_CANDLES

    while i < len(df) - 5:

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

        if signal not in [
            "LONG",
            "SHORT"
        ]:

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

        if not np.isfinite(
            float(atr)
        ):
            i += 1
            continue

        entry = float(entry)
        atr = float(atr)

        # =================================================
        # حد ضرر و سود
        # =================================================

        if signal == "LONG":

            stop_loss = (
                entry
                - atr * ATR_STOP_MULTIPLIER
            )

            tp1 = (
                entry
                + atr * ATR_TP1_MULTIPLIER
            )

            tp2 = (
                entry
                + atr * ATR_TP2_MULTIPLIER
            )

        else:

            stop_loss = (
                entry
                + atr * ATR_STOP_MULTIPLIER
            )

            tp1 = (
                entry
                - atr * ATR_TP1_MULTIPLIER
            )

            tp2 = (
                entry
                - atr * ATR_TP2_MULTIPLIER
            )

        # =================================================
        # بررسی کندل‌های بعدی
        # =================================================

        result_trade = check_trade_result(
            df=df,
            entry_index=i,
            signal=signal,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2
        )

        # =================================================
        # ثبت نتیجه
        # =================================================

        if result_trade == "TP2":

            wins_tp2 += 1

            # ریسک = 1R
            # TP2 = 2R
            total_profit_r += 2.0

        elif result_trade == "TP1":

            wins_tp1 += 1

            # TP1 = 1R
            total_profit_r += 1.0

        elif result_trade == "SL":

            losses += 1

            total_profit_r -= 1.0

        else:

            open_trades += 1

        trades.append({
            "symbol": symbol,
            "index": i,
            "time": df.iloc[i]["open_time"],
            "signal": signal,
            "entry": entry,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "result": result_trade
        })

        # =================================================
        # جلوگیری از ورودهای پشت سر هم
        # =================================================

        # بعد از هر معامله تا پایان نتیجه آن جلو می‌رویم
        trade_end = i + 1

        while trade_end < len(df):

            candle = df.iloc[
                trade_end
            ]

            high = float(
                candle["high"]
            )

            low = float(
                candle["low"]
            )

            if signal == "LONG":

                if (
                    low <= stop_loss
                    or high >= tp2
                    or high >= tp1
                ):
                    break

            else:

                if (
                    high >= stop_loss
                    or low <= tp2
                    or low <= tp1
                ):
                    break

            trade_end += 1

        i = max(
            i + 1,
            trade_end + 1
        )

    # =====================================================
    # آمار
    # =====================================================

    total_trades = len(trades)

    completed_trades = (
        wins_tp2
        + wins_tp1
        + losses
    )

    if completed_trades > 0:

        win_rate = (
            (wins_tp2 + wins_tp1)
            / completed_trades
        ) * 100

    else:

        win_rate = 0

    print(
        f"\n📊 {symbol}"
    )

    print(
        f"تعداد معاملات: {total_trades}"
    )

    print(
        f"🟢 TP2: {wins_tp2}"
    )

    print(
        f"🟢 TP1: {wins_tp1}"
    )

    print(
        f"🔴 SL: {losses}"
    )

    print(
        f"⚪ باز: {open_trades}"
    )

    print(
        f"🎯 Win Rate: {win_rate:.2f}%"
    )

    print(
        f"💰 نتیجه فرضی: {total_profit_r:.2f}R"
    )

    return {
        "symbol": symbol,
        "trades": total_trades,
        "tp2": wins_tp2,
        "tp1": wins_tp1,
        "sl": losses,
        "open": open_trades,
        "win_rate": win_rate,
        "profit_r": total_profit_r,
        "trade_data": trades
    }


# =========================================================
# اجرای تمام ارزها
# =========================================================

def main():

    print(
        "\n🚀 شروع بک‌تست تاریخی..."
    )

    print(
        f"\n⏱️ تایم‌فریم: {TIMEFRAME}"
    )

    print(
        f"📊 تعداد کندل: {CANDLE_LIMIT}"
    )

    print(
        "\n⚠️ این بک‌تست فقط تحلیلی است."
    )

    all_results = []

    for symbol in SYMBOLS:

        try:

            result = backtest_symbol(
                symbol
            )

            if result is not None:

                all_results.append(
                    result
                )

        except Exception as e:

            print(
                f"\n❌ خطا در {symbol}:"
            )

            print(e)

    # =====================================================
    # گزارش نهایی
    # =====================================================

    print(
        "\n\n"
        + "=" * 60
    )

    print(
        "🏆 گزارش نهایی بک‌تست"
    )

    print(
        "=" * 60
    )

    total_trades = 0
    total_tp2 = 0
    total_tp1 = 0
    total_sl = 0
    total_open = 0
    total_profit_r = 0

    for result in all_results:

        total_trades += result[
            "trades"
        ]

        total_tp2 += result[
            "tp2"
        ]

        total_tp1 += result[
            "tp1"
        ]

        total_sl += result[
            "sl"
        ]

        total_open += result[
            "open"
        ]

        total_profit_r += result[
            "profit_r"
        ]

        print(
            f"\n{result['symbol']}"
        )

        print(
            f"Trades: {result['trades']}"
        )

        print(
            f"TP2: {result['tp2']}"
        )

        print(
            f"TP1: {result['tp1']}"
        )

        print(
            f"SL: {result['sl']}"
        )

        print(
            f"Win Rate: "
            f"{result['win_rate']:.2f}%"
        )

        print(
            f"Profit: "
            f"{result['profit_r']:.2f}R"
        )

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
        "\n"
        + "=" * 60
    )

    print(
        "📈 مجموع معاملات:",
        total_trades
    )

    print(
        "🟢 مجموع TP2:",
        total_tp2
    )

    print(
        "🟢 مجموع TP1:",
        total_tp1
    )

    print(
        "🔴 مجموع SL:",
        total_sl
    )

    print(
        "⚪ معاملات باز:",
        total_open
    )

    print(
        f"🎯 Win Rate کلی: "
        f"{overall_win_rate:.2f}%"
    )

    print(
        f"💰 نتیجه فرضی کلی: "
        f"{total_profit_r:.2f}R"
    )

    print(
        "\n⚠️ این نتیجه سود واقعی یا تضمین سود نیست."
    )


if __name__ == "__main__":

    main()
