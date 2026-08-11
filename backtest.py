import time
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
    "TRX-SWAP-USDT",
    "AVAX-SWAP-USDT",
    "LINK-SWAP-USDT",
    "DOT-SWAP-USDT",
    "LTC-SWAP-USDT",
    "BCH-SWAP-USDT",
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


# تعداد کندل‌هایی که برای تست می‌گیریم
CANDLE_LIMIT = 250


# حداقل تأیید لازم
MIN_CONFIRMATION = 4


# حداقل امتیاز میانگین
MIN_AVERAGE_SCORE = 6.5


# =========================================================
# تحلیل چند تایم‌فریمی
# =========================================================

def analyze_symbol(symbol):

    results = {}

    for timeframe in TIMEFRAMES:

        print(
            f"   بررسی {symbol} - {timeframe}"
        )

        try:

            df = get_klines(
                symbol=symbol,
                interval=timeframe,
                limit=CANDLE_LIMIT
            )

            if df is None or len(df) < 200:

                results[timeframe] = {
                    "signal": "NO TRADE",
                    "score": 0
                }

                continue

            result = analyze(df)

            results[timeframe] = result

        except Exception as e:

            print(
                f"   ERROR {symbol} {timeframe}: {e}"
            )

            results[timeframe] = {
                "signal": "NO TRADE",
                "score": 0
            }

    return results


# =========================================================
# ساخت سیگنال نهایی
# =========================================================

def get_final_signal(results):

    long_count = 0
    short_count = 0

    long_scores = []
    short_scores = []

    for timeframe in TIMEFRAMES:

        result = results.get(
            timeframe,
            {}
        )

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        score = result.get(
            "score",
            0
        )

        if signal == "LONG":

            long_count += 1
            long_scores.append(score)

        elif signal == "SHORT":

            short_count += 1
            short_scores.append(score)

    # -----------------------------------------------------
    # LONG
    # -----------------------------------------------------

    if long_count >= MIN_CONFIRMATION:

        average_score = (
            sum(long_scores) /
            len(long_scores)
        )

        if average_score >= MIN_AVERAGE_SCORE:

            return {
                "signal": "LONG",
                "confirmation": long_count,
                "average_score": average_score
            }

    # -----------------------------------------------------
    # SHORT
    # -----------------------------------------------------

    if short_count >= MIN_CONFIRMATION:

        average_score = (
            sum(short_scores) /
            len(short_scores)
        )

        if average_score >= MIN_AVERAGE_SCORE:

            return {
                "signal": "SHORT",
                "confirmation": short_count,
                "average_score": average_score
            }

    return {
        "signal": "NO TRADE",
        "confirmation": 0,
        "average_score": 0
    }


# =========================================================
# بررسی نتیجه معامله
# =========================================================

def check_trade(
    df,
    signal,
    entry,
    stop_loss,
    tp1,
    tp2
):

    if df is None or len(df) == 0:

        return "NO DATA"

    for _, candle in df.iterrows():

        high = float(
            candle["high"]
        )

        low = float(
            candle["low"]
        )

        # =================================================
        # LONG
        # =================================================

        if signal == "LONG":

            # اول بررسی Stop Loss
            if low <= stop_loss:

                return "STOP LOSS"

            # سپس TP2
            if high >= tp2:

                return "TP2"

            # سپس TP1
            if high >= tp1:

                return "TP1"

        # =================================================
        # SHORT
        # =================================================

        elif signal == "SHORT":

            # اول بررسی Stop Loss
            if high >= stop_loss:

                return "STOP LOSS"

            # سپس TP2
            if low <= tp2:

                return "TP2"

            # سپس TP1
            if low <= tp1:

                return "TP1"

    return "OPEN"


# =========================================================
# اجرای بک‌تست
# =========================================================

def run_backtest():

    print(
        "\n"
        "========================================"
    )

    print(
        "🚀 شروع BACKTEST"
    )

    print(
        "========================================\n"
    )

    total_trades = 0

    tp1_count = 0
    tp2_count = 0
    stop_count = 0
    open_count = 0

    long_trades = 0
    short_trades = 0

    results_table = []

    # =====================================================
    # هر ارز
    # =====================================================

    for symbol in SYMBOLS:

        print(
            f"\n=============================="
        )

        print(
            f"📊 {symbol}"
        )

        print(
            f"=============================="
        )

        results = analyze_symbol(
            symbol
        )

        final = get_final_signal(
            results
        )

        signal = final["signal"]

        if signal == "NO TRADE":

            print(
                "⚪ سیگنال معتبر پیدا نشد."
            )

            continue

        # =================================================
        # پیدا کردن قیمت ورود
        # =================================================

        entry = None

        source_df = None

        for timeframe in TIMEFRAMES:

            result = results.get(
                timeframe,
                {}
            )

            price = result.get(
                "price"
            )

            if price is not None:

                entry = float(price)

                try:

                    source_df = get_klines(
                        symbol=symbol,
                        interval=timeframe,
                        limit=100
                    )

                except Exception:

                    source_df = None

                break

        if entry is None:

            continue

        # =================================================
        # ATR
        # =================================================

        atr = None

        for timeframe in TIMEFRAMES:

            result = results.get(
                timeframe,
                {}
            )

            value = result.get(
                "atr"
            )

            if value is not None:

                try:

                    atr = float(value)

                    break

                except Exception:

                    pass

        if atr is None or atr <= 0:

            print(
                "❌ ATR معتبر نیست."
            )

            continue

        # =================================================
        # تعیین SL و TP
        # =================================================

        if signal == "LONG":

            stop_loss = entry - (
                atr * 2
            )

            tp1 = entry + (
                atr * 2
            )

            tp2 = entry + (
                atr * 4
            )

            long_trades += 1

        else:

            stop_loss = entry + (
                atr * 2
            )

            tp1 = entry - (
                atr * 2
            )

            tp2 = entry - (
                atr * 4
            )

            short_trades += 1

        # =================================================
        # نتیجه
        # =================================================

        outcome = check_trade(
            source_df,
            signal,
            entry,
            stop_loss,
            tp1,
            tp2
        )

        total_trades += 1

        if outcome == "TP1":

            tp1_count += 1

        elif outcome == "TP2":

            tp2_count += 1

        elif outcome == "STOP LOSS":

            stop_count += 1

        elif outcome == "OPEN":

            open_count += 1

        results_table.append({
            "symbol": symbol,
            "signal": signal,
            "confirmation":
                final["confirmation"],
            "average_score":
                round(
                    final["average_score"],
                    2
                ),
            "entry":
                entry,
            "stop_loss":
                stop_loss,
            "tp1":
                tp1,
            "tp2":
                tp2,
            "outcome":
                outcome
        })

        print(
            f"\n{signal}"
        )

        print(
            f"⭐ Score: "
            f"{final['average_score']:.2f}"
        )

        print(
            f"🎯 تأیید: "
            f"{final['confirmation']}/5"
        )

        print(
            f"📍 Entry: {entry}"
        )

        print(
            f"🛑 SL: {stop_loss}"
        )

        print(
            f"🎯 TP1: {tp1}"
        )

        print(
            f"🎯 TP2: {tp2}"
        )

        print(
            f"📊 نتیجه: {outcome}"
        )

        # جلوگیری از فشار زیاد به API
        time.sleep(0.5)

    # =====================================================
    # گزارش نهایی
    # =====================================================

    print(
        "\n\n"
        "========================================"
    )

    print(
        "📊 گزارش نهایی BACKTEST"
    )

    print(
        "========================================"
    )

    print(
        f"\n📌 کل معاملات: "
        f"{total_trades}"
    )

    print(
        f"🟢 LONG: "
        f"{long_trades}"
    )

    print(
        f"🔴 SHORT: "
        f"{short_trades}"
    )

    print(
        f"\n🎯 TP1: "
        f"{tp1_count}"
    )

    print(
        f"🏆 TP2: "
        f"{tp2_count}"
    )

    print(
        f"🛑 Stop Loss: "
        f"{stop_count}"
    )

    print(
        f"⏳ هنوز باز: "
        f"{open_count}"
    )

    # =====================================================
    # درصدها
    # =====================================================

    if total_trades > 0:

        tp1_percent = (
            tp1_count /
            total_trades
        ) * 100

        tp2_percent = (
            tp2_count /
            total_trades
        ) * 100

        stop_percent = (
            stop_count /
            total_trades
        ) * 100

        print(
            f"\n📈 درصد TP1: "
            f"{tp1_percent:.1f}%"
        )

        print(
            f"📈 درصد TP2: "
            f"{tp2_percent:.1f}%"
        )

        print(
            f"📉 درصد Stop Loss: "
            f"{stop_percent:.1f}%"
        )

    # =====================================================
    # نمایش جزئیات
    # =====================================================

    if results_table:

        print(
            "\n\n"
            "========================================"
        )

        print(
            "📋 جزئیات معاملات"
        )

        print(
            "========================================\n"
        )

        for item in results_table:

            print(
                f"{item['symbol']} | "
                f"{item['signal']} | "
                f"Score {item['average_score']} | "
                f"{item['confirmation']}/5 | "
                f"{item['outcome']}"
            )

    print(
        "\n========================================"
    )

    print(
        "✅ BACKTEST تمام شد."
    )

    print(
        "⚠️ این تست هیچ سفارش واقعی ارسال نمی‌کند."
    )

    print(
        "========================================"
    )


# =========================================================
# اجرای مستقیم
# =========================================================

if __name__ == "__main__":

    run_backtest()
