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

TIMEFRAMES = [
    "1h",
    "2h",
    "3h",
    "4h",
    "1d",
]

CANDLE_LIMIT = 1000
MIN_CANDLES = 200

MIN_CONFIRMATION = 4
MIN_AVERAGE_SCORE = 6.0

ATR_STOP = 2.0
ATR_TP1 = 2.0
ATR_TP2 = 4.0


# =========================================================
# دریافت اطلاعات
# =========================================================

def load_symbol_data(symbol):

    data = {}

    print("\n" + "-" * 60)
    print(f"📥 دریافت اطلاعات {symbol}")

    for timeframe in TIMEFRAMES:

        try:

            df = get_klines(
                symbol=symbol,
                interval=timeframe,
                limit=CANDLE_LIMIT
            )

            if df is None:
                print(
                    f"⚠️ {timeframe}: داده دریافت نشد"
                )
                continue

            if len(df) < MIN_CANDLES:
                print(
                    f"⚠️ {timeframe}: داده کافی نیست"
                )
                continue

            df = df.copy()

            if "open_time" not in df.columns:
                print(
                    f"⚠️ {timeframe}: open_time موجود نیست"
                )
                continue

            df["open_time"] = pd.to_datetime(
                df["open_time"]
            )

            data[timeframe] = df

            print(
                f"✅ {timeframe}: {len(df)} کندل"
            )

        except Exception as e:

            print(
                f"❌ خطا {symbol} {timeframe}: {e}"
            )

    return data


# =========================================================
# تحلیل تاریخی
# =========================================================

def historical_analysis(
    data,
    timestamp
):

    results = {}

    for timeframe in TIMEFRAMES:

        df = data.get(
            timeframe
        )

        if df is None:

            results[timeframe] = {
                "signal": "NO TRADE",
                "score": 0,
                "price": None,
                "atr": None,
            }

            continue

        historical = df[
            df["open_time"] <= timestamp
        ]

        if len(historical) < MIN_CANDLES:

            results[timeframe] = {
                "signal": "NO TRADE",
                "score": 0,
                "price": None,
                "atr": None,
            }

            continue

        try:

            results[timeframe] = analyze(
                historical.copy()
            )

        except Exception:

            results[timeframe] = {
                "signal": "NO TRADE",
                "score": 0,
                "price": None,
                "atr": None,
            }

    return results


# =========================================================
# ساخت سیگنال نهایی
# =========================================================

def build_final_signal(results):

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

            long_scores.append(
                score
            )

        elif signal == "SHORT":

            short_scores.append(
                score
            )

    long_count = len(
        long_scores
    )

    short_count = len(
        short_scores
    )

    # =====================================================
    # LONG
    # =====================================================

    if (
        long_count >= MIN_CONFIRMATION
        and short_count == 0
    ):

        average_score = (
            sum(long_scores)
            /
            len(long_scores)
        )

        if average_score >= MIN_AVERAGE_SCORE:

            return {
                "signal": "LONG",
                "confirmation": long_count,
                "average_score": average_score,
            }

    # =====================================================
    # SHORT
    # =====================================================

    if (
        short_count >= MIN_CONFIRMATION
        and long_count == 0
    ):

        average_score = (
            sum(short_scores)
            /
            len(short_scores)
        )

        if average_score >= MIN_AVERAGE_SCORE:

            return {
                "signal": "SHORT",
                "confirmation": short_count,
                "average_score": average_score,
            }

    return {
        "signal": "NO TRADE",
        "confirmation": 0,
        "average_score": 0,
    }


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

        high = float(
            candle["high"]
        )

        low = float(
            candle["low"]
        )

        if signal == "LONG":

            hit_sl = (
                low <= stop_loss
            )

            hit_tp1 = (
                high >= tp1
            )

            hit_tp2 = (
                high >= tp2
            )

            # حالت محافظه‌کارانه
            if hit_sl and (
                hit_tp1 or hit_tp2
            ):
                return "SL"

            if hit_tp2:
                return "TP2"

            if hit_tp1:
                return "TP1"

            if hit_sl:
                return "SL"

        elif signal == "SHORT":

            hit_sl = (
                high >= stop_loss
            )

            hit_tp1 = (
                low <= tp1
            )

            hit_tp2 = (
                low <= tp2
            )

            if hit_sl and (
                hit_tp1 or hit_tp2
            ):
                return "SL"

            if hit_tp2:
                return "TP2"

            if hit_tp1:
                return "TP1"

            if hit_sl:
                return "SL"

    return "OPEN"


# =========================================================
# بک‌تست یک ارز
# =========================================================

def backtest_symbol(symbol):

    print("\n")
    print("=" * 65)
    print(f"🚀 BACKTEST {symbol}")
    print("=" * 65)

    data = load_symbol_data(
        symbol
    )

    if "1h" not in data:

        print(
            "❌ داده 1H موجود نیست"
        )

        return None

    base_df = data["1h"]

    trades = []

    tp2_count = 0
    tp1_count = 0
    sl_count = 0
    open_count = 0

    total_r = 0.0

    i = MIN_CANDLES

    while i < len(base_df) - 5:

        timestamp = base_df.iloc[
            i
        ]["open_time"]

        results = historical_analysis(
            data,
            timestamp
        )

        final = build_final_signal(
            results
        )

        signal = final[
            "signal"
        ]

        if signal == "NO TRADE":

            i += 1
            continue

        # -------------------------------------------------
        # ورود
        # -------------------------------------------------

        entry = float(
            base_df.iloc[i]["close"]
        )

        # -------------------------------------------------
        # ATR تایم‌فریم 1H
        # -------------------------------------------------

        one_hour = results.get(
            "1h",
            {}
        )

        atr = one_hour.get(
            "atr"
        )

        if atr is None:

            i += 1
            continue

        try:

            atr = float(
                atr
            )

        except:

            i += 1
            continue

        if not np.isfinite(
            atr
        ) or atr <= 0:

            i += 1
            continue

        # -------------------------------------------------
        # SL / TP
        # -------------------------------------------------

        if signal == "LONG":

            stop_loss = (
                entry
                -
                atr * ATR_STOP
            )

            tp1 = (
                entry
                +
                atr * ATR_TP1
            )

            tp2 = (
                entry
                +
                atr * ATR_TP2
            )

        else:

            stop_loss = (
                entry
                +
                atr * ATR_STOP
            )

            tp1 = (
                entry
                -
                atr * ATR_TP1
            )

            tp2 = (
                entry
                -
                atr * ATR_TP2
            )

        # -------------------------------------------------
        # نتیجه
        # -------------------------------------------------

        result = check_trade_result(
            df=base_df,
            entry_index=i,
            signal=signal,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2
        )

        if result == "TP2":

            tp2_count += 1
            total_r += 2.0

        elif result == "TP1":

            tp1_count += 1
            total_r += 1.0

        elif result == "SL":

            sl_count += 1
            total_r -= 1.0

        else:

            open_count += 1

        trades.append({
            "time": timestamp,
            "signal": signal,
            "confirmation": final[
                "confirmation"
            ],
            "average_score": final[
                "average_score"
            ],
            "entry": entry,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "result": result
        })

        # -------------------------------------------------
        # جلوگیری از ورودهای پشت سر هم
        # -------------------------------------------------

        trade_end = i + 1

        while trade_end < len(base_df):

            candle = base_df.iloc[
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
                    or high >= tp1
                    or high >= tp2
                ):
                    break

            else:

                if (
                    high >= stop_loss
                    or low <= tp1
                    or low <= tp2
                ):
                    break

            trade_end += 1

        i = max(
            i + 1,
            trade_end + 1
        )

    # =====================================================
    # آمار ارز
    # =====================================================

    total_trades = len(
        trades
    )

    completed = (
        tp2_count
        +
        tp1_count
        +
        sl_count
    )

    if completed > 0:

        win_rate = (
            (
                tp2_count
                +
                tp1_count
            )
            /
            completed
        ) * 100

    else:

        win_rate = 0

    # =====================================================
    # گزارش ارز
    # =====================================================

    print("\n" + "-" * 50)

    print(
        f"📊 نتیجه {symbol}"
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
        f"🎯 Win Rate: "
        f"{win_rate:.2f}%"
    )

    print(
        f"💰 نتیجه: "
        f"{total_r:.2f}R"
    )

    return {
        "symbol": symbol,
        "trades": total_trades,
        "tp2": tp2_count,
        "tp1": tp1_count,
        "sl": sl_count,
        "open": open_count,
        "win_rate": win_rate,
        "profit_r": total_r,
        "trade_data": trades
    }


# =========================================================
# اجرای کل بک‌تست
# =========================================================

def main():

    print("\n")
    print("=" * 65)

    print(
        "🚀 شروع بک‌تست تفکیکی"
    )

    print(
        "⏱️ 1H → 2H → 3H → 4H → 1D"
    )

    print(
        f"📊 تعداد ارزها: {len(SYMBOLS)}"
    )

    print("=" * 65)

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

            print(
                e
            )

    # =====================================================
    # مرتب‌سازی بر اساس سود
    # =====================================================

    all_results.sort(
        key=lambda x:
            x["profit_r"],
        reverse=True
    )

    print("\n\n")
    print("=" * 65)
    print("🏆 رتبه‌بندی ارزها")
    print("=" * 65)

    for index, result in enumerate(
        all_results,
        start=1
    ):

        profit = result[
            "profit_r"
        ]

        if profit > 0:
            emoji = "🟢"
        elif profit < 0:
            emoji = "🔴"
        else:
            emoji = "⚪"

        print(
            f"\n{index}. "
            f"{emoji} "
            f"{result['symbol']}"
        )

        print(
            f"   معاملات: "
            f"{result['trades']}"
        )

        print(
            f"   TP2: "
            f"{result['tp2']}"
        )

        print(
            f"   TP1: "
            f"{result['tp1']}"
        )

        print(
            f"   SL: "
            f"{result['sl']}"
        )

        print(
            f"   Win Rate: "
            f"{result['win_rate']:.2f}%"
        )

        print(
            f"   نتیجه: "
            f"{profit:.2f}R"
        )

    # =====================================================
    # آمار کلی
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

    total_r = sum(
        x["profit_r"]
        for x in all_results
    )

    completed = (
        total_tp2
        +
        total_tp1
        +
        total_sl
    )

    if completed > 0:

        overall_win_rate = (
            (
                total_tp2
                +
                total_tp1
            )
            /
            completed
        ) * 100

    else:

        overall_win_rate = 0

    # =====================================================
    # گزارش نهایی
    # =====================================================

    print("\n\n")
    print("=" * 65)

    print(
        "🏆 گزارش نهایی"
    )

    print("=" * 65)

    print(
        f"\n📈 مجموع معاملات: "
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
        f"{total_r:.2f}R"
    )

    print("\n")
    print(
        "⚠️ این بک‌تست تضمین‌کننده سود واقعی نیست."
    )


if __name__ == "__main__":

    main()
