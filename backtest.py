import time
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
    "AVAX-SWAP-USDT",
    "LINK-SWAP-USDT",
    "DOT-SWAP-USDT",
    "LTC-SWAP-USDT",
    "UNI-SWAP-USDT",
    "SUI-SWAP-USDT",
]
TIMEFRAME = "1h"
# تعداد کندل تاریخی
CANDLE_LIMIT = 1000
# حداقل داده برای شروع تحلیل
MIN_TRAIN_CANDLES = 250
# ATR
ATR_SL = 2.0
ATR_TP1 = 2.0
ATR_TP2 = 4.0
# حداقل امتیاز برای ورود
MIN_SCORE = 6
# فاصله بین درخواست‌ها
REQUEST_DELAY = 0.8
# =========================================================
# بررسی معامله
# =========================================================
def check_trade_result(
    df,
    entry_index,
    signal,
    stop_loss,
    tp1,
    tp2
):
    for i in range(entry_index + 1, len(df)):
        candle = df.iloc[i]
        high = float(candle["high"])
        low = float(candle["low"])
        if signal == "LONG":
            hit_sl = low <= stop_loss
            hit_tp2 = high >= tp2
            hit_tp1 = high >= tp1
            # محافظه‌کارانه:
            # اگر SL و TP در یک کندل باشند → SL
            if hit_sl and (hit_tp1 or hit_tp2):
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
            if hit_sl and (hit_tp1 or hit_tp2):
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
    print(f"🔎 BACKTEST: {symbol}")
    print("=" * 60)
    try:
        df = get_klines(
            symbol=symbol,
            interval=TIMEFRAME,
            limit=CANDLE_LIMIT
        )
    except Exception as e:
        print(f"❌ خطای دریافت {symbol}: {e}")
        return None
    if df is None:
        print("❌ داده دریافت نشد")
        return None
    if len(df) < MIN_TRAIN_CANDLES + 20:
        print(
            f"❌ داده کافی نیست: {len(df)} کندل"
        )
        return None
    df = df.copy()
    # اطمینان از عددی بودن داده‌ها
    for column in [
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )
    df = df.dropna(
        subset=[
            "high",
            "low",
            "close"
        ]
    ).reset_index(
        drop=True
    )
    trades = []
    tp2_count = 0
    tp1_count = 0
    sl_count = 0
    open_count = 0
    total_profit_r = 0.0
    i = MIN_TRAIN_CANDLES
    # =====================================================
    # حرکت در تاریخ
    # =====================================================
    while i < len(df) - 10:
        historical_df = df.iloc[:i].copy()
        try:
            result = analyze(
                historical_df
            )
        except Exception:
            i += 1
            continue
        signal = result.get(
            "signal",
            "NO TRADE"
        )
        score = result.get(
            "score",
            0
        )
        # فقط سیگنال‌های قابل توجه
        if signal not in [
            "LONG",
            "SHORT"
        ]:
            i += 1
            continue
        if score < MIN_SCORE:
            i += 1
            continue
        entry = result.get("price")
        atr = result.get("atr")
        if entry is None or atr is None:
            i += 1
            continue
        try:
            entry = float(entry)
            atr = float(atr)
        except Exception:
            i += 1
            continue
        if not np.isfinite(atr) or atr <= 0:
            i += 1
            continue
        # =================================================
        # محاسبه SL / TP
        # =================================================
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
        # =================================================
        # ثبت نتیجه
        # =================================================
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
            "entry": entry,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "result": trade_result
        })
        # =================================================
        # جلوگیری از معاملات پشت سرهم
        # =================================================
        trade_end = i + 1
        while trade_end < len(df):
            candle = df.iloc[trade_end]
            high = float(candle["high"])
            low = float(candle["low"])
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
    wins = (
        tp2_count
        + tp1_count
    )
    if completed > 0:
        win_rate = (
            wins / completed
        ) * 100
    else:
        win_rate = 0.0
    print("\n📊 نتیجه")
    print(
        f"معاملات: {total_trades}"
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
        f"⚪ OPEN: {open_count}"
    )
    print(
        f"🎯 Win Rate: {win_rate:.2f}%"
    )
    print(
        f"💰 Profit: {total_profit_r:.2f}R"
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
        "trade_data": trades
    }
# =========================================================
# رتبه‌بندی
# =========================================================
def calculate_rank_score(result):
    if result is None:
        return -999
    profit = result["profit_r"]
    win_rate = result["win_rate"]
    trades = result["trades"]
    # امتیاز اصلی بر اساس سود
    rank_score = profit * 10
    # پاداش Win Rate
    rank_score += win_rate * 0.10
    # جلوگیری از رتبه گرفتن با تعداد بسیار کم معامله
    if trades < 10:
        rank_score -= 20
    return rank_score
# =========================================================
# اجرای اصلی
# =========================================================
def main():
    print("\n")
    print("=" * 60)
    print("🚀 BACKTEST ENGINE")
    print("=" * 60)
    print(
        f"⏱️ Timeframe: {TIMEFRAME}"
    )
    print(
        f"📊 Candles: {CANDLE_LIMIT}"
    )
    print(
        f"⭐ Minimum Score: {MIN_SCORE}"
    )
    print(
        "\n⚠️ بک‌تست صرفاً تاریخی و تحلیلی است."
    )
    all_results = []
    # =====================================================
    # بررسی ارزها
    # =====================================================
    for number, symbol in enumerate(
        SYMBOLS,
        start=1
    ):
        print(
            f"\n🔵 {number}/{len(SYMBOLS)}"
        )
        result = backtest_symbol(
            symbol
        )
        if result is not None:
            result["rank_score"] = (
                calculate_rank_score(
                    result
                )
            )
            all_results.append(
                result
            )
        # جلوگیری از فشار به API
        time.sleep(
            REQUEST_DELAY
        )
    # =====================================================
    # اگر نتیجه‌ای نبود
    # =====================================================
    if not all_results:
        print(
            "\n❌ هیچ نتیجه‌ای برای بک‌تست پیدا نشد."
        )
        return
    # =====================================================
    # رتبه‌بندی
    # =====================================================
    ranking = sorted(
        all_results,
        key=lambda x: (
            x["rank_score"],
            x["profit_r"],
            x["win_rate"]
        ),
        reverse=True
    )
    print("\n\n")
    print("=" * 60)
    print("🏆 رتبه‌بندی ارزها")
    print("=" * 60)
    for position, result in enumerate(
        ranking,
        start=1
    ):
        profit = result["profit_r"]
        if profit > 0:
            emoji = "🟢"
        elif profit < 0:
            emoji = "🔴"
        else:
            emoji = "⚪"
        print(
            f"\n{position}. "
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
            f"   Profit: "
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
    total_profit = sum(
        x["profit_r"]
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
    print("\n")
    print("=" * 60)
    print("📈 گزارش نهایی")
    print("=" * 60)
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
    if total_profit > 0:
        result_emoji = "🟢"
    elif total_profit < 0:
        result_emoji = "🔴"
    else:
        result_emoji = "⚪"
    print(
        f"{result_emoji} نتیجه فرضی کلی: "
        f"{total_profit:.2f}R"
    )
    # =====================================================
    # بهترین ارز
    # =====================================================
    best = ranking[0]
    print("\n")
    print("=" * 60)
    print("🥇 بهترین ارز")
    print("=" * 60)
    print(
        f"🪙 {best['symbol']}"
    )
    print(
        f"💰 Profit: "
        f"{best['profit_r']:.2f}R"
    )
    print(
        f"🎯 Win Rate: "
        f"{best['win_rate']:.2f}%"
    )
    print(
        "\n⚠️ این بک‌تست تضمین‌کننده سود آینده نیست."
    )
if __name__ == "__main__":
    main()
