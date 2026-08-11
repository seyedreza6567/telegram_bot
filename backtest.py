import pandas as pd
import numpy as np

from scanner import get_klines
from analysis_engine import analyze


# =========================================================
# تنظیمات
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
# امتیاز تاریخی اولیه
#
# این اعداد از آخرین بک‌تست خودمان گرفته شده‌اند.
# بعد از اجرای بک‌تست جدید، خود سیستم دوباره آنها را
# با نتایج جدید مقایسه می‌کند.
# =========================================================

HISTORICAL_RESULTS = {

    "XRP-SWAP-USDT": {
        "win_rate": 51.0,
        "profit": 1.0,
    },

    "DOT-SWAP-USDT": {
        "win_rate": 50.0,
        "profit": 1.0,
    },

    "LINK-SWAP-USDT": {
        "win_rate": 47.83,
        "profit": 1.0,
    },

    "LTC-SWAP-USDT": {
        "win_rate": 49.0,
        "profit": -1.0,
    },

    "ADA-SWAP-USDT": {
        "win_rate": 44.0,
        "profit": -3.0,
    },

    "DOGE-SWAP-USDT": {
        "win_rate": 44.0,
        "profit": -4.0,
    },

    "BTC-SWAP-USDT": {
        "win_rate": 43.48,
        "profit": -4.0,
    },

    "SOL-SWAP-USDT": {
        "win_rate": 45.0,
        "profit": -5.0,
    },

    "BNB-SWAP-USDT": {
        "win_rate": 43.0,
        "profit": -6.0,
    },

    "UNI-SWAP-USDT": {
        "win_rate": 40.0,
        "profit": -9.0,
    },

    "ETH-SWAP-USDT": {
        "win_rate": 33.0,
        "profit": -9.0,
    },

    "AVAX-SWAP-USDT": {
        "win_rate": 27.50,
        "profit": -14.0,
    },

    "SUI-SWAP-USDT": {
        "win_rate": 0.0,
        "profit": 0.0,
    },
}


# =========================================================
# ارزهای فعلاً ممنوع برای سیگنال اصلی
#
# اینها حذف دائمی نیستند.
# فقط تا زمانی که بک‌تست جدید نتیجه بهتری بدهد
# وارد فرصت‌های اصلی نمی‌شوند.
# =========================================================

BLOCKED_SYMBOLS = {
    "AVAX-SWAP-USDT",
    "ETH-SWAP-USDT",
    "UNI-SWAP-USDT",
}


# =========================================================
# محاسبه امتیاز تاریخی
# =========================================================

def historical_score(symbol):

    data = HISTORICAL_RESULTS.get(
        symbol,
        {}
    )

    win_rate = float(
        data.get("win_rate", 0)
    )

    profit = float(
        data.get("profit", 0)
    )

    score = 0.0

    # Win Rate
    if win_rate >= 50:
        score += 3
    elif win_rate >= 47:
        score += 2
    elif win_rate >= 45:
        score += 1

    # Profit
    if profit > 0:
        score += 3
    elif profit == 0:
        score += 1
    elif profit <= -10:
        score -= 3
    elif profit <= -5:
        score -= 2
    elif profit < 0:
        score -= 1

    return score


# =========================================================
# بررسی برخورد TP / SL
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

        high = float(
            candle["high"]
        )

        low = float(
            candle["low"]
        )

        if signal == "LONG":

            hit_sl = low <= stop_loss
            hit_tp2 = high >= tp2
            hit_tp1 = high >= tp1

            # حالت محافظه‌کارانه
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

    print("\n" + "=" * 65)

    print(
        f"🔎 BACKTEST: {symbol}"
    )

    print("=" * 65)

    df = get_klines(
        symbol=symbol,
        interval=TIMEFRAME,
        limit=CANDLE_LIMIT
    )

    if df is None:

        print(
            "❌ داده دریافت نشد."
        )

        return None

    if len(df) < MIN_TRAIN_CANDLES + 20:

        print(
            f"❌ داده کافی نیست: {len(df)}"
        )

        return None

    df = df.copy()

    trades = []

    tp2_count = 0
    tp1_count = 0
    sl_count = 0
    open_count = 0

    total_profit_r = 0.0

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

        # =================================================
        # فیلتر کیفیت سیگنال
        # =================================================

        if signal not in [
            "LONG",
            "SHORT"
        ]:

            i += 1
            continue

        # سیگنال‌های ضعیف وارد بک‌تست نمی‌شوند
        if score < 6:

            i += 1
            continue

        # اعتماد کمتر از 60 درصد قبول نمی‌شود
        if confidence < 60:

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

        entry = float(entry)
        atr = float(atr)

        if not np.isfinite(atr):

            i += 1
            continue

        if atr <= 0:

            i += 1
            continue

        # =================================================
        # حد ضرر و حد سود
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
        # نتیجه معامله
        # =================================================

        trade_result = check_trade_result(
            df=df,
            entry_index=i,
            signal=signal,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2
        )

        if trade_result == "TP2":

            tp2_count += 1

            total_profit_r += 2.0

        elif trade_result == "TP1":

            tp1_count += 1

            total_profit_r += 1.0

        elif trade_result == "SL":

            sl_count += 1

            total_profit_r -= 1.0

        else:

            open_count += 1

        trades.append({
            "symbol": symbol,
            "index": i,
            "signal": signal,
            "score": score,
            "confidence": confidence,
            "entry": entry,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "result": trade_result,
        })

        # =================================================
        # جلوگیری از معاملات پشت سر هم
        # =================================================

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

            finished = False

            if signal == "LONG":

                if (
                    low <= stop_loss
                    or high >= tp1
                    or high >= tp2
                ):

                    finished = True

            else:

                if (
                    high >= stop_loss
                    or low <= tp1
                    or low <= tp2
                ):

                    finished = True

            if finished:

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

    old = HISTORICAL_RESULTS.get(
        symbol,
        {}
    )

    old_profit = float(
        old.get("profit", 0)
    )

    old_win = float(
        old.get("win_rate", 0)
    )

    new_score = historical_score(
        symbol
    )

    print(
        f"\n📊 {symbol}"
    )

    print(
        f"📈 معاملات: {total_trades}"
    )

    print(
        f"🟢 TP2: {tp2_count}"
    )

    print(
        f"🟢 TP1: {tp1_count}"
    )

    print(
        f"🔴 SL: {sl_count}"
    )

    print(
        f"⚪ باز: {open_count}"
    )

    print(
        f"🎯 Win Rate جدید: "
        f"{win_rate:.2f}%"
    )

    print(
        f"💰 Profit جدید: "
        f"{total_profit_r:.2f}R"
    )

    print(
        f"📚 Win Rate قبلی: "
        f"{old_win:.2f}%"
    )

    print(
        f"📚 Profit قبلی: "
        f"{old_profit:.2f}R"
    )

    print(
        f"⭐ امتیاز تاریخی: "
        f"{new_score:.1f}"
    )

    return {
        "symbol": symbol,
        "trades": total_trades,
        "tp2": tp2_count,
        "tp1": tp1_count,
        "sl": sl_count,
        "open": open_count,
        "win_rate": win_rate,
        "profit_r": total_profit_r,
        "historical_score": new_score,
        "trade_data": trades,
    }


# =========================================================
# رتبه‌بندی
# =========================================================

def rank_symbols(results):

    ranked = []

    for result in results:

        symbol = result["symbol"]

        win_rate = result[
            "win_rate"
        ]

        profit = result[
            "profit_r"
        ]

        trades = result[
            "trades"
        ]

        # -------------------------------------------------
        # امتیاز جدید
        # -------------------------------------------------

        ranking_score = 0.0

        # سود
        ranking_score += profit * 2

        # Win Rate
        ranking_score += (
            win_rate - 40
        ) * 0.5

        # تعداد معاملات
        if trades >= 20:
            ranking_score += 2

        elif trades >= 10:
            ranking_score += 1

        # جریمه ارزهای بسیار ضعیف
        if profit <= -10:
            ranking_score -= 5

        elif profit <= -5:
            ranking_score -= 2

        ranked.append({
            "symbol": symbol,
            "ranking_score": ranking_score,
            "win_rate": win_rate,
            "profit": profit,
            "trades": trades,
        })

    ranked.sort(
        key=lambda x: x[
            "ranking_score"
        ],
        reverse=True
    )

    return ranked


# =========================================================
# گزارش نهایی
# =========================================================

def print_final_report(
    results
):

    print(
        "\n\n"
        + "=" * 65
    )

    print(
        "🏆 رتبه‌بندی نهایی ارزها"
    )

    print(
        "=" * 65
    )

    ranked = rank_symbols(
        results
    )

    for index, item in enumerate(
        ranked,
        start=1
    ):

        symbol = item[
            "symbol"
        ]

        name = (
            symbol
            .replace(
                "-SWAP-USDT",
                ""
            )
        )

        print(
            f"\n{index}. {name}"
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
            f"{item['ranking_score']:.2f}"
        )

    print(
        "\n"
        + "=" * 65
    )

    # =====================================================
    # پیشنهاد ارزهای قابل بررسی
    # =====================================================

    candidates = []

    for item in ranked:

        symbol = item[
            "symbol"
        ]

        if symbol in BLOCKED_SYMBOLS:
            continue

        if item["profit"] <= 0:
            continue

        if item["win_rate"] < 45:
            continue

        candidates.append(
            symbol
        )

    print(
        "\n🟢 ارزهای منتخب فعلی:"
    )

    if candidates:

        for symbol in candidates:

            print(
                "   ✅",
                symbol.replace(
                    "-SWAP-USDT",
                    ""
                )
            )

    else:

        print(
            "   ⚪ هیچ ارز مناسبی پیدا نشد."
        )

    print(
        "\n🔴 ارزهای فعلاً حذف‌شده:"
    )

    for symbol in BLOCKED_SYMBOLS:

        print(
            "   ❌",
            symbol.replace(
                "-SWAP-USDT",
                ""
            )
        )

    print(
        "\n⚠️ این رتبه‌بندی تضمین سود آینده نیست."
    )


# =========================================================
# اجرای اصلی
# =========================================================

def main():

    print(
        "\n🚀 شروع بک‌تست جدید..."
    )

    print(
        f"⏱️ تایم‌فریم: {TIMEFRAME}"
    )

    print(
        f"📊 کندل: {CANDLE_LIMIT}"
    )

    print(
        "\n🛡️ فیلتر کیفیت فعال است."
    )

    print(
        "🛡️ Score حداقل: 6"
    )

    print(
        "🛡️ Confidence حداقل: 60%"
    )

    results = []

    for symbol in SYMBOLS:

        try:

            result = backtest_symbol(
                symbol
            )

            if result is not None:

                results.append(
                    result
                )

        except Exception as e:

            print(
                f"\n❌ خطا در {symbol}:"
            )

            print(
                str(e)
            )

    if not results:

        print(
            "\n❌ هیچ نتیجه‌ای دریافت نشد."
        )

        return

    # =====================================================
    # گزارش ارزها
    # =====================================================

    print_final_report(
        results
    )

    # =====================================================
    # مجموع
    # =====================================================

    total_trades = sum(
        x["trades"]
        for x in results
    )

    total_tp2 = sum(
        x["tp2"]
        for x in results
    )

    total_tp1 = sum(
        x["tp1"]
        for x in results
    )

    total_sl = sum(
        x["sl"]
        for x in results
    )

    total_open = sum(
        x["open"]
        for x in results
    )

    total_profit = sum(
        x["profit_r"]
        for x in results
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
        "\n⚠️ این بک‌تست سود واقعی یا تضمین سود آینده نیست."
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
