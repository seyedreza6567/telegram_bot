import pandas as pd

from scanner import get_klines

# FIX: همان مشکل multi_timeframe.py اینجا هم وجود داشت - backtest.py
# یک کپی کاملاً مستقل از منطق تصمیم‌گیری دارد (به multi_timeframe.py
# یا signal_engine.py وابسته نیست) و MAX_SCORE را جداگانه 15.0 هاردکد
# کرده بود. بعد از بازمقیاس‌بندی analysis_engine.py به MAX_SCORE=20،
# همه‌ی نتایج قبلی بک‌تست (+37.2R و غیره) زیر یک quality واقعاً
# سست‌تر از چیزی که فکر می‌کردیم گرفته شده بودند. حالا مستقیماً
# از analysis_engine.py ایمپورت می‌شود.
from analysis_engine import analyze, MAX_SCORE as ANALYSIS_MAX_SCORE

from signal_engine import (
    MIN_QUALITY,
    MIN_DIRECTIONAL_RATIO,
    MIN_LOWER_CONFIRMATIONS,
    LOWER_TIMEFRAMES,
    HIGH_TIMEFRAMES,
)


CANDLE_LIMIT = 4000

WARMUP_BARS = 210

TIMEFRAMES = LOWER_TIMEFRAMES + HIGH_TIMEFRAMES

PRIORITY_SYMBOLS = [
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
    "LTC-SWAP-USDT",
    "BCH-SWAP-USDT",
    "UNI-SWAP-USDT",
    "SUI-SWAP-USDT",
]


def _fetch_all_timeframes(symbol):

    data = {}

    for tf in TIMEFRAMES:

        df = get_klines(symbol=symbol, interval=tf, limit=CANDLE_LIMIT)

        if df is None or len(df) < WARMUP_BARS + 5:
            return None

        data[tf] = df.reset_index(drop=True)

    return data


def _aligned_index(target_time, df):
    """
    آخرین ایندکس df که open_time آن <= target_time است. (align
    به عقب - یعنی آخرین کندل بسته‌شده‌ی آن تایم‌فریم تا آن لحظه)
    """

    idx = df["open_time"].searchsorted(target_time, side="right") - 1

    return idx if idx >= 0 else None


def _simulate_trade(entry_tf_df, start_index, signal, entry, stop_loss, take_profit):

    for i in range(start_index + 1, len(entry_tf_df)):

        high = entry_tf_df["high"].iloc[i]
        low = entry_tf_df["low"].iloc[i]

        if signal == "LONG":

            hit_stop = low <= stop_loss
            hit_target = high >= take_profit

        else:

            hit_stop = high >= stop_loss
            hit_target = low <= take_profit

        if hit_stop and hit_target:
            # هر دو در یک کندل - محافظه‌کارانه، حد ضرر را می‌پذیریم.
            return "LOSS"

        if hit_stop:
            return "LOSS"

        if hit_target:
            return "WIN"

    return None  # تا پایان داده معامله بسته نشده


def backtest_symbol(symbol):

    data = _fetch_all_timeframes(symbol)

    if data is None:
        return None

    entry_tf = "4h"
    entry_df = data[entry_tf]

    trades = []

    in_position_until = -1

    for i in range(WARMUP_BARS, len(entry_df) - 1):

        if i <= in_position_until:
            continue

        current_time = entry_df["open_time"].iloc[i]

        tf_results = {}

        for tf, df in data.items():

            idx = _aligned_index(current_time, df)

            if idx is None or idx < WARMUP_BARS:
                tf_results = None
                break

            window = df.iloc[max(0, idx - WARMUP_BARS - 20): idx + 1]

            tf_results[tf] = analyze(window)

        if tf_results is None:
            continue

        daily_signal = tf_results.get("1d", {}).get("signal", "NO TRADE")
        h4_signal = tf_results.get("4h", {}).get("signal", "NO TRADE")

        long_count = sum(1 for r in tf_results.values() if r["signal"] == "LONG")
        short_count = sum(1 for r in tf_results.values() if r["signal"] == "SHORT")

        lower_long = sum(
            1 for tf in LOWER_TIMEFRAMES if tf_results.get(tf, {}).get("signal") == "LONG"
        )
        lower_short = sum(
            1 for tf in LOWER_TIMEFRAMES if tf_results.get(tf, {}).get("signal") == "SHORT"
        )

        long_quality_values = [
            r["score"] / ANALYSIS_MAX_SCORE
            for r in tf_results.values() if r["signal"] == "LONG"
        ]
        short_quality_values = [
            r["score"] / ANALYSIS_MAX_SCORE
            for r in tf_results.values() if r["signal"] == "SHORT"
        ]

        long_quality = (
            sum(long_quality_values) / len(long_quality_values)
            if long_quality_values else 0
        )
        short_quality = (
            sum(short_quality_values) / len(short_quality_values)
            if short_quality_values else 0
        )

        total = long_count + short_count
        ratio_long = long_count / total if total else 0
        ratio_short = short_count / total if total else 0

        signal = None

        if (
            daily_signal == "LONG" and h4_signal == "LONG"
            and lower_long >= MIN_LOWER_CONFIRMATIONS
            and long_quality >= MIN_QUALITY
            and ratio_long >= MIN_DIRECTIONAL_RATIO
        ):
            signal = "LONG"

        elif (
            daily_signal == "SHORT" and h4_signal == "SHORT"
            and lower_short >= MIN_LOWER_CONFIRMATIONS
            and short_quality >= MIN_QUALITY
            and ratio_short >= MIN_DIRECTIONAL_RATIO
        ):
            signal = "SHORT"

        if not signal:
            continue

        entry_data = tf_results["4h"]

        entry_price = entry_data.get("price")
        stop_loss = entry_data.get("stop_loss")
        take_profit = entry_data.get("take_profit")

        if entry_price is None or stop_loss is None or take_profit is None:
            continue

        risk_distance = abs(entry_price - stop_loss)
        reward_distance = abs(take_profit - entry_price)

        if risk_distance <= 0:
            continue

        result = _simulate_trade(
            entry_df, i, signal, entry_price, stop_loss, take_profit
        )

        if result is None:
            continue

        r_multiple = (
            reward_distance / risk_distance if result == "WIN"
            else -1.0
        )

        trades.append({
            "symbol": symbol,
            "signal": signal,
            "result": result,
            "r_multiple": r_multiple,
        })

        # تا اولین کندلی که نتیجه مشخص شد صبر کن (بدون هم‌پوشانی معاملات)
        in_position_until = i + 1

    return trades


def run_backtest(symbols=None):

    symbols = symbols or PRIORITY_SYMBOLS

    all_trades = []

    per_symbol = {}

    for symbol in symbols:

        print(f"\n===== Backtesting {symbol} =====")

        try:
            trades = backtest_symbol(symbol)
        except Exception as e:
            print(f"BACKTEST ERROR {symbol}: {e}")
            continue

        if not trades:
            print("  no trades")
            continue

        wins = sum(1 for t in trades if t["result"] == "WIN")
        total_r = sum(t["r_multiple"] for t in trades)

        per_symbol[symbol] = {
            "trades": len(trades),
            "win_rate": round(wins / len(trades) * 100, 2),
            "total_r": round(total_r, 2),
        }

        print(
            f"  trades={len(trades)} "
            f"win_rate={per_symbol[symbol]['win_rate']}% "
            f"total_R={per_symbol[symbol]['total_r']}"
        )

        all_trades.extend(trades)

    if all_trades:

        wins = sum(1 for t in all_trades if t["result"] == "WIN")
        total_r = sum(t["r_multiple"] for t in all_trades)

        print("\n===== TOTAL =====")
        print(f"trades={len(all_trades)}")
        print(f"win_rate={round(wins / len(all_trades) * 100, 2)}%")
        print(f"total_R={round(total_r, 2)}")

    return per_symbol


if __name__ == "__main__":

    run_backtest()
