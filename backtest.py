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
    "AVAX-SWAP-USDT",
    "LINK-SWAP-USDT",
    "DOT-SWAP-USDT",
    "LTC-SWAP-USDT",
    "UNI-SWAP-USDT",
    "SUI-SWAP-USDT",
]

TIMEFRAMES = [
    "1h",
    "2h",
    "3h",
    "4h",
    "1d",
]

CANDLE_LIMIT = 1000

MIN_CANDLES = 250

MIN_CONFIRMATION = 4

MIN_SCORE = 6

MIN_CONFIDENCE = 60

ATR_SL = 2.0
ATR_TP1 = 2.0
ATR_TP2 = 4.0


# =========================================================
# دریافت داده
# =========================================================

def load_data(symbol):

    data = {}

    for timeframe in TIMEFRAMES:

        print(
            f"   دریافت {timeframe} ..."
        )

        df = get_klines(
            symbol=symbol,
            interval=timeframe,
            limit=CANDLE_LIMIT
        )

        if df is None:
            print(
                f"   ❌ {timeframe}: بدون داده"
            )
            return None

        if len(df) < MIN_CANDLES:
            print(
                f"   ❌ {timeframe}: داده کافی نیست"
            )
            return None

        df = df.copy()

        if "open_time" not in df.columns:
            df["open_time"] = np.arange(
                len(df)
            )

        data[timeframe] = df

    return data


# =========================================================
# تحلیل یک کندل تاریخی
# =========================================================

def analyze_at_index(
    data,
    index
):

    results = {}

    for timeframe in TIMEFRAMES:

        df = data[timeframe]

        if index >= len(df):
            return None

        historical_df = df.iloc[
            :index + 1
        ].copy()

        if len(historical_df) < MIN_CANDLES:
            return None

        try:

            result = analyze(
                historical_df
            )

        except Exception:
            return None

        results[timeframe] = result

    return results


# =========================================================
# ساخت سیگنال نهایی
# =========================================================

def build_signal(
    results
):

    long_count = 0
    short_count = 0

    long_score = []
    short_score = []

    for timeframe in TIMEFRAMES:

        result = results.get(
            timeframe,
            {}
        )

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        score = float(
            result.get(
                "score",
                0
            )
        )

        confidence = float(
            result.get(
                "confidence",
                0
            )
        )

        if confidence < MIN_CONFIDENCE:
            continue

        if score < MIN_SCORE:
            continue

        if signal == "LONG":

            long_count += 1
            long_score.append(
                score
            )

        elif signal == "SHORT":

            short_count += 1
            short_score.append(
                score
            )

    # -----------------------------------------------------
    # فقط 4 از 5
    # -----------------------------------------------------

    if (
        long_count >= MIN_CONFIRMATION
        and short_count == 0
    ):

        signal = "LONG"

        scores = long_score

    elif (
        short_count >= MIN_CONFIRMATION
        and long_count == 0
    ):

        signal = "SHORT"

        scores = short_score

    else:

        return {
            "signal": "NO TRADE",
            "confirmation": 0,
            "average_score": 0
        }

    average_score = (
        sum(scores) / len(scores)
        if scores
        else 0
    )

    return {
        "signal": signal,
        "confirmation": max(
            long_count,
            short_count
        ),
        "average_score": average_score
    }


# =========================================================
# بررسی نتیجه معامله
# =========================================================

def check_trade(
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

        high = float(
            candle["high"]
        )

        low = float(
            candle["low"]
        )

        # -------------------------------------------------
        # LONG
        # -------------------------------------------------

        if signal == "LONG":

            hit_sl = (
                low <= stop_loss
            )

            hit_tp2 = (
                high >= tp2
            )

            hit_tp1 = (
                high >= tp1
            )

            # حالت محافظه کارانه
            if hit_sl and hit_tp2:
                return "SL", i

            if hit_sl:
                return "SL", i

            if hit_tp2:
                return "TP2", i

            if hit_tp1:
                return "TP1", i

        # -------------------------------------------------
        # SHORT
        # -------------------------------------------------

        elif signal == "SHORT":

            hit_sl = (
                high >= stop_loss
            )

            hit_tp2 = (
                low <= tp2
            )

            hit_tp1 = (
                low <= tp1
            )

            if hit_sl and hit_tp2:
                return "SL", i

            if hit_sl:
                return "SL", i

            if hit_tp2:
                return "TP2", i

            if hit_tp1:
                return "TP1", i

    return "OPEN", len(df) - 1


# =========================================================
# بک‌تست یک ارز
# =========================================================

def backtest_symbol(
    symbol
):

    print(
        "\n"
        + "=" * 60
    )

    print(
        f"🔎 BACKTEST: {symbol}"
    )

    print(
        "=" * 60
    )

    data = load_data(
        symbol
    )

    if data is None:
        return None

    # -----------------------------------------------------
    # کوتاه‌ترین داده
    # -----------------------------------------------------

    max_index = min(
        len(data[tf])
        for tf in TIMEFRAMES
    )

    if max_index < MIN_CANDLES + 20:

        print(
            "❌ داده کافی نیست"
        )

        return None

    trades = []

    tp2_count = 0
    tp1_count = 0
    sl_count = 0
    open_count = 0

    profit_r = 0.0

    i = MIN_CANDLES

    # -----------------------------------------------------
    # حرکت تاریخی
    # -----------------------------------------------------

    while i < max_index - 5:

        print(
            f"   تحلیل کندل {i}/{max_index}"
        )

        results = analyze_at_index(
            data,
            i
        )

        if results is None:

            i += 1
            continue

        final = build_signal(
            results
        )

        signal = final[
            "signal"
        ]

        if signal == "NO TRADE":

            i += 1
            continue

        confirmation = final[
            "confirmation"
        ]

        average_score = final[
            "average_score"
        ]

        # -------------------------------------------------
        # قیمت و ATR از 1H
        # -------------------------------------------------

        base_result = results[
            "1h"
        ]

        entry = base_result.get(
            "price"
        )

        atr = base_result.get(
            "atr"
        )

        if entry is None or atr is None:

            i += 1
            continue

        entry = float(entry)
        atr = float(atr)

        if not np.isfinite(
            entry
        ):

            i += 1
            continue

        if not np.isfinite(
            atr
        ):

            i += 1
            continue

        if atr <= 0:

            i += 1
            continue

        # -------------------------------------------------
        # SL / TP
        # -------------------------------------------------

        if signal == "LONG":

            stop_loss = (
                entry
                - atr * ATR_SL
            )

            tp1 = (
                entry
                + atr * ATR_TP1
            )

            tp2 = (
                entry
                + atr * ATR_TP2
            )

        else:

            stop_loss = (
                entry
                + atr * ATR_SL
            )

            tp1 = (
                entry
                - atr * ATR_TP1
            )

            tp2 = (
                entry
                - atr * ATR_TP2
            )

        # -------------------------------------------------
        # بررسی نتیجه
        # -------------------------------------------------

        result, end_index = check_trade(
            data["1h"],
            i,
            signal,
            stop_loss,
            tp1,
            tp2
        )

        # -------------------------------------------------
        # محاسبه R
        # -------------------------------------------------

        if result == "TP2":

            tp2_count += 1

            profit_r += 2.0

        elif result == "TP1":

            tp1_count += 1

            profit_r += 1.0

        elif result == "SL":

            sl_count += 1

            profit_r -= 1.0

        else:

            open_count += 1

        trades.append({

            "index": i,

            "signal": signal,

            "confirmation": confirmation,

            "score": average_score,

            "entry": entry,

            "stop_loss": stop_loss,

            "tp1": tp1,

            "tp2": tp2,

            "result": result

        })

        # -------------------------------------------------
        # بعد از پایان معامله
        # دوباره بلافاصله وارد نشو
        # -------------------------------------------------

        i = max(
            i + 1,
            end_index + 1
        )

    # =====================================================
    # آمار
    # =====================================================

    total = len(trades)

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

        win_rate = 0

    print(
        "\n📊 نتیجه",
    )

    print(
        f"ارز: {symbol}"
    )

    print(
        f"معاملات: {total}"
    )

    print(
        f"TP2: {tp2_count}"
    )

    print(
        f"TP1: {tp1_count}"
    )

    print(
        f"SL: {sl_count}"
    )

    print(
        f"باز: {open_count}"
    )

    print(
        f"Win Rate: {win_rate:.2f}%"
    )

    print(
        f"Profit: {profit_r:.2f}R"
    )

    return {

        "symbol": symbol,

        "trades": total,

        "tp2": tp2_count,

        "tp1": tp1_count,

        "sl": sl_count,

        "open": open_count,

        "win_rate": win_rate,

        "profit": profit_r,

        "trade_data": trades

    }


# =========================================================
# رتبه بندی
# =========================================================

def rank_results(
    results
):

    ranked = []

    for result in results:

        profit = result[
            "profit"
        ]

        win_rate = result[
            "win_rate"
        ]

        trades = result[
            "trades"
        ]

        # -------------------------------------------------
        # امتیاز رتبه بندی
        # -------------------------------------------------

        score = 0

        # سود
        score += profit * 3

        # Win Rate
        score += (
            win_rate - 40
        )

        # تعداد معاملات
        if trades >= 30:

            score += 3

        elif trades >= 20:

            score += 2

        elif trades >= 10:

            score += 1

        ranked.append({

            "symbol": result[
                "symbol"
            ],

            "score": score,

            "win_rate": win_rate,

            "profit": profit,

            "trades": trades

        })

    ranked.sort(
        key=lambda x: x[
            "score"
        ],
        reverse=True
    )

    return ranked


# =========================================================
# گزارش نهایی
# =========================================================

def main():

    print(
        "\n🚀 شروع بک‌تست چندتایم‌فریمی"
    )

    print(
        "\n⏱️ 1H → 2H → 3H → 4H → 1D"
    )

    print(
        f"🎯 حداقل تأیید: "
        f"{MIN_CONFIRMATION}/5"
    )

    print(
        f"⭐ حداقل Score: "
        f"{MIN_SCORE}"
    )

    print(
        f"📈 حداقل Confidence: "
        f"{MIN_CONFIDENCE}%"
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
                f"\n❌ خطا در {symbol}"
            )

            print(
                str(e)
            )

    if not all_results:

        print(
            "\n❌ هیچ نتیجه‌ای پیدا نشد."
        )

        return

    # =====================================================
    # رتبه بندی
    # =====================================================

    ranked = rank_results(
        all_results
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
        ranked,
        start=1
    ):

        name = (
            item["symbol"]
            .replace(
                "-SWAP-USDT",
                ""
            )
        )

        print(
            f"\n{number}. {name}"
        )

        print(
            f"   🎯 Win Rate: "
            f"{item['win_rate']:.2f}%"
        )

        print(
            f"   💰 Profit: "
            f"{item['profit']:.2f}R"
        )

        print(
            f"   📈 Trades: "
            f"{item['trades']}"
        )

        print(
            f"   ⭐ Ranking Score: "
            f"{item['score']:.2f}"
        )

    # =====================================================
    # مجموع
    # =====================================================

    total_trades = sum(
        x["trades"]
        for x in all_results
    )

    total_tp2 = sum(
        x["tp2"]
        for x in all_results
    )

    total_tp1 = sum(
        x["tp1"]
        for x in all_results
    )

    total_sl = sum(
        x["sl"]
        for x in all_results
    )

    total_open = sum(
        x["open"]
        for x in all_results
    )

    total_profit = sum(
        x["profit"]
        for x in all_results
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
        + "=" * 65
    )

    print(
        "📊 گزارش کلی"
    )

    print(
        "=" * 65
    )

    print(
        f"📈 مجموع معاملات: "
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
        f"⚪ معاملات باز: "
        f"{total_open}"
    )

    print(
        f"🎯 Win Rate کلی: "
        f"{overall_win_rate:.2f}%"
    )

    print(
        f"💰 نتیجه فرضی کلی: "
        f"{total_profit:.2f}R"
    )

    print(
        "\n⚠️ این بک‌تست تضمین‌کننده سود واقعی نیست."
    )


# =========================================================
# اجرا
# =========================================================

if __name__ == "__main__":

    main()
