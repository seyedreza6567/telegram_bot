import pandas as pd
import numpy as np

from scanner import get_klines
from analysis_engine import analyze

# =========================================================
# SYMBOLS
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

# =========================================================
# SETTINGS
# =========================================================
TIMEFRAMES = {
    "1h": {"interval": "1h", "weight": 1.0},
    "2h": {"interval": "2h", "weight": 1.25},
    "3h": {"interval": "3h", "weight": 1.50},
    "4h": {"interval": "4h", "weight": 2.0},
    "1d": {"interval": "1d", "weight": 3.0},
}

# FIX: raised from 1000 -> 4000 candles per timeframe so the backtest
# covers a much longer historical window (roughly ~166 days on 1h,
# and up to ~11 years on 1d, though the exchange will simply return
# whatever history it actually has if that's less). scanner.py already
# paginates past the exchange's 1000-candle-per-request cap, so no
# other file needs to change. Note: this means far more API requests
# per symbol/timeframe, so a full run across all 15 symbols will take
# noticeably longer than before.
CANDLE_LIMIT = 4000
MIN_ANALYSIS_CANDLES = 250
SL_ATR = 2.0
TP1_ATR = 2.0
TP2_ATR = 4.0
MAX_HOLD_CANDLES = 100
COST_R = 0.05
MAX_SCORE = 15.0

MIN_QUALITY = 0.62
MIN_LOWER_CONFIRMATIONS = 2
MIN_DIRECTIONAL_RATIO = 0.58


# =========================================================
# SAFE FLOAT
# =========================================================
def safe_float(value):
    try:
        value = float(value)
        if np.isfinite(value):
            return value
    except Exception:
        pass
    return None


def symbol_name(symbol):
    return symbol.replace("-SWAP-USDT", "")


def prepare_dataframe(df):
    if df is None:
        return None
    if len(df) == 0:
        return None
    df = df.copy()
    df = df.reset_index(drop=True)
    return df


# =========================================================
# BUILD MULTI-TIMEFRAME ANALYSIS AT A POINT IN TIME
# =========================================================
def analyze_at_time(datasets, current_time):
    results = {}

    for timeframe, settings in TIMEFRAMES.items():
        df = datasets.get(timeframe)
        weight = settings["weight"]

        if df is None:
            results[timeframe] = {
                "signal": "NO TRADE", "score": 0, "confidence": 0,
                "long_score": 0, "short_score": 0, "quality": 0,
                "weight": weight, "timeframe": timeframe,
                "reason": "داده موجود نیست"
            }
            continue

        if "timestamp" in df.columns:
            historical = df[df["timestamp"] < current_time].copy()
        elif "time" in df.columns:
            historical = df[df["time"] < current_time].copy()
        elif "open_time" in df.columns:
            historical = df[df["open_time"] < current_time].copy()
        else:
            historical = df.copy()

        if len(historical) < MIN_ANALYSIS_CANDLES:
            results[timeframe] = {
                "signal": "NO TRADE", "score": 0, "confidence": 0,
                "long_score": 0, "short_score": 0, "quality": 0,
                "weight": weight, "timeframe": timeframe,
                "reason": "داده تاریخی کافی نیست"
            }
            continue

        try:
            result = analyze(historical)
        except Exception as e:
            results[timeframe] = {
                "signal": "NO TRADE", "score": 0, "confidence": 0,
                "long_score": 0, "short_score": 0, "quality": 0,
                "weight": weight, "timeframe": timeframe,
                "reason": f"خطای تحلیل: {e}"
            }
            continue

        result = result.copy()
        score = safe_float(result.get("score", 0))
        if score is None:
            score = 0.0
        score = max(0.0, min(score, MAX_SCORE))

        signal = result.get("signal", "NO TRADE")
        quality = (score / MAX_SCORE) if signal in ["LONG", "SHORT"] else 0.0

        result["score"] = score
        result["quality"] = quality
        result["score_ratio"] = quality
        result["weight"] = weight
        result["timeframe"] = timeframe
        results[timeframe] = result

    return results


# =========================================================
# FINAL DECISION
# =========================================================
def build_final_signal(results):
    long_weight = 0.0
    short_weight = 0.0
    long_quality = 0.0
    short_quality = 0.0
    total_valid_weight = 0.0
    long_count = 0
    short_count = 0

    for timeframe, result in results.items():
        signal = result.get("signal", "NO TRADE")
        weight = safe_float(result.get("weight", 0))
        quality = safe_float(result.get("quality", 0))

        if weight is None:
            weight = 0
        if quality is None:
            quality = 0
        if signal not in ["LONG", "SHORT"]:
            continue

        total_valid_weight += weight
        if signal == "LONG":
            long_count += 1
            long_weight += weight
            long_quality += quality * weight
        elif signal == "SHORT":
            short_count += 1
            short_weight += weight
            short_quality += quality * weight

    total_weight = sum(safe_float(result.get("weight", 0)) or 0 for result in results.values())
    if total_weight <= 0:
        total_weight = 1.0

    long_ratio = long_weight / total_weight
    short_ratio = short_weight / total_weight

    if total_valid_weight > 0:
        long_quality_ratio = long_quality / total_valid_weight
        short_quality_ratio = short_quality / total_valid_weight
    else:
        long_quality_ratio = 0.0
        short_quality_ratio = 0.0

    quality_margin = abs(long_quality_ratio - short_quality_ratio)

    daily = results.get("1d", {})
    four_hour = results.get("4h", {})
    daily_signal = daily.get("signal", "NO TRADE")
    four_hour_signal = four_hour.get("signal", "NO TRADE")
    daily_quality = safe_float(daily.get("quality", 0)) or 0
    four_hour_quality = safe_float(four_hour.get("quality", 0)) or 0

    higher_tf_long = (
        daily_signal == "LONG" and four_hour_signal == "LONG"
        and daily_quality >= MIN_QUALITY and four_hour_quality >= MIN_QUALITY
    )
    higher_tf_short = (
        daily_signal == "SHORT" and four_hour_signal == "SHORT"
        and daily_quality >= MIN_QUALITY and four_hour_quality >= MIN_QUALITY
    )

    lower_long_count = 0
    lower_short_count = 0

    for timeframe in ["1h", "2h", "3h"]:
        result = results.get(timeframe, {})
        signal = result.get("signal", "NO TRADE")
        quality = safe_float(result.get("quality", 0)) or 0

        if signal == "LONG" and quality >= MIN_QUALITY:
            lower_long_count += 1
        elif signal == "SHORT" and quality >= MIN_QUALITY:
            lower_short_count += 1

    final = "NO TRADE"
    reason = None

    if not higher_tf_long and not higher_tf_short:
        reason = "تایید جهت کافی نیست"
    elif higher_tf_long and lower_long_count < MIN_LOWER_CONFIRMATIONS:
        reason = f"VALID TF کم است: {lower_long_count}/3"
    elif higher_tf_short and lower_short_count < MIN_LOWER_CONFIRMATIONS:
        reason = f"VALID TF کم است: {lower_short_count}/3"
    elif daily_signal != "NO TRADE" and four_hour_signal != "NO TRADE" and daily_signal != four_hour_signal:
        reason = "1D و 4H همجهت نیستند"

    if (
        higher_tf_long
        and lower_long_count >= MIN_LOWER_CONFIRMATIONS
        and long_ratio >= MIN_DIRECTIONAL_RATIO
        and long_ratio > short_ratio
    ):
        final = "LONG"
        reason = None
    elif (
        higher_tf_short
        and lower_short_count >= MIN_LOWER_CONFIRMATIONS
        and short_ratio >= MIN_DIRECTIONAL_RATIO
        and short_ratio > long_ratio
    ):
        final = "SHORT"
        reason = None
    elif reason is None:
        reason = "شرایط ورود کامل نیست"

    return {
        "signal": final,
        "reason": reason,
        "long_weight": long_weight,
        "short_weight": short_weight,
        "long_ratio": long_ratio,
        "short_ratio": short_ratio,
        "long_quality": long_quality_ratio,
        "short_quality": short_quality_ratio,
        "quality_margin": quality_margin,
        "long_count": long_count,
        "short_count": short_count,
        "lower_long_count": lower_long_count,
        "lower_short_count": lower_short_count,
        "daily_signal": daily_signal,
        "daily_quality": daily_quality,
        "four_hour_signal": four_hour_signal,
        "four_hour_quality": four_hour_quality,
        "timeframes": results
    }


# =========================================================
# SIMULATE TRADE
# =========================================================
def simulate_trade(df, entry_index, signal, atr):
    entry = safe_float(df.iloc[entry_index]["open"])
    if entry is None:
        return None
    if atr is None or atr <= 0:
        return None

    if signal == "LONG":
        sl = entry - (atr * SL_ATR)
        tp1 = entry + (atr * TP1_ATR)
        tp2 = entry + (atr * TP2_ATR)
    elif signal == "SHORT":
        sl = entry + (atr * SL_ATR)
        tp1 = entry - (atr * TP1_ATR)
        tp2 = entry - (atr * TP2_ATR)
    else:
        return None

    tp1_hit = False
    last_index = min(len(df), entry_index + MAX_HOLD_CANDLES + 1)

    for j in range(entry_index, last_index):
        high = safe_float(df.iloc[j]["high"])
        low = safe_float(df.iloc[j]["low"])
        if high is None or low is None:
            continue

        if signal == "LONG":
            if not tp1_hit:
                hit_sl = low <= sl
                hit_tp1 = high >= tp1
                if hit_sl:
                    return {"result": "SL", "r": -1.0 - COST_R, "bars": j - entry_index + 1}
                if hit_tp1:
                    tp1_hit = True
                    if high >= tp2:
                        return {"result": "TP2", "r": 1.5 - COST_R, "bars": j - entry_index + 1}
                    continue
            else:
                hit_be = low <= entry
                hit_tp2 = high >= tp2
                if hit_be:
                    return {"result": "TP1", "r": 0.5 - COST_R, "bars": j - entry_index + 1}
                if hit_tp2:
                    return {"result": "TP2", "r": 1.5 - COST_R, "bars": j - entry_index + 1}

        elif signal == "SHORT":
            if not tp1_hit:
                hit_sl = high >= sl
                hit_tp1 = low <= tp1
                if hit_sl:
                    return {"result": "SL", "r": -1.0 - COST_R, "bars": j - entry_index + 1}
                if hit_tp1:
                    tp1_hit = True
                    if low <= tp2:
                        return {"result": "TP2", "r": 1.5 - COST_R, "bars": j - entry_index + 1}
                    continue
            else:
                hit_be = high >= entry
                hit_tp2 = low <= tp2
                if hit_be:
                    return {"result": "TP1", "r": 0.5 - COST_R, "bars": j - entry_index + 1}
                if hit_tp2:
                    return {"result": "TP2", "r": 1.5 - COST_R, "bars": j - entry_index + 1}

    return {"result": "TIMEOUT", "r": 0.0, "bars": max(1, last_index - entry_index)}


# =========================================================
# LOAD ALL DATA
# =========================================================
def load_symbol_data(symbol):
    datasets = {}
    for timeframe, settings in TIMEFRAMES.items():
        print(f"Loading {symbol_name(symbol)} {timeframe}...")
        try:
            df = get_klines(symbol=symbol, interval=settings["interval"], limit=CANDLE_LIMIT)
        except Exception as e:
            print("DATA ERROR:", timeframe, e)
            return None

        df = prepare_dataframe(df)
        if df is None:
            print("NO DATA:", timeframe)
            return None
        if len(df) < MIN_ANALYSIS_CANDLES:
            print("NOT ENOUGH DATA:", timeframe, len(df))
            return None

        datasets[timeframe] = df

    return datasets


def get_timeline(datasets):
    base = datasets.get("1h")
    if base is None:
        return []

    for column in ["timestamp", "time", "open_time"]:
        if column in base.columns:
            return list(base[column].iloc[MIN_ANALYSIS_CANDLES:])

    return list(range(MIN_ANALYSIS_CANDLES, len(base)))


# =========================================================
# BACKTEST SYMBOL
# =========================================================
def backtest_symbol(symbol):
    print("\n" + "=" * 65)
    print("BACKTEST:", symbol_name(symbol))
    print("=" * 65)

    datasets = load_symbol_data(symbol)
    if datasets is None:
        return None

    base_df = datasets["1h"]
    timeline = get_timeline(datasets)
    if not timeline:
        print("NO TIMELINE")
        return None

    trades = []
    long_signals = 0
    short_signals = 0
    no_trade_count = 0
    block_reasons = {}

    previous_signal = "NO TRADE"

    for i, current_time in enumerate(timeline):
        row_index = MIN_ANALYSIS_CANDLES + i

        results = analyze_at_time(datasets, current_time)
        final = build_final_signal(results)
        signal = final["signal"]

        if signal in ["LONG", "SHORT"]:
            if signal == "LONG":
                long_signals += 1
            else:
                short_signals += 1

            if signal != previous_signal:
                entry_data = results.get("1h", {})
                atr = safe_float(entry_data.get("atr"))
                entry_index = row_index

                if atr is not None and atr > 0 and entry_index < len(base_df):
                    trade = simulate_trade(base_df, entry_index, signal, atr)
                    if trade is not None:
                        trades.append(trade)
        else:
            no_trade_count += 1
            reason = final.get("reason") or "شرایط ورود کامل نیست"
            block_reasons[reason] = block_reasons.get(reason, 0) + 1

        previous_signal = signal

    print("\nSIGNAL SUMMARY:", symbol_name(symbol))
    print("LONG SIGNALS:", long_signals)
    print("SHORT SIGNALS:", short_signals)
    print("NO TRADE:", no_trade_count)

    if block_reasons:
        print("TOP BLOCK REASONS:")
        top_reasons = sorted(block_reasons.items(), key=lambda x: x[1], reverse=True)[:3]
        for reason, count in top_reasons:
            print(f"  {count} x {reason}")

    tp2 = sum(1 for t in trades if t["result"] == "TP2")
    tp1 = sum(1 for t in trades if t["result"] == "TP1")
    sl = sum(1 for t in trades if t["result"] == "SL")
    timeout = sum(1 for t in trades if t["result"] == "TIMEOUT")
    profit = sum(t["r"] for t in trades)
    wins = tp2 + tp1
    completed = wins + sl
    win_rate = (wins / completed * 100) if completed > 0 else 0.0

    if not trades:
        print("\nNO TRADES:", symbol_name(symbol))

    return {
        "symbol": symbol_name(symbol),
        "signals": long_signals + short_signals,
        "trades": len(trades),
        "long": long_signals,
        "short": short_signals,
        "tp2": tp2,
        "tp1": tp1,
        "sl": sl,
        "timeout": timeout,
        "win_rate": win_rate,
        "profit": profit,
    }


# =========================================================
# MAIN
# =========================================================
def main():
    all_results = []

    for symbol in SYMBOLS:
        try:
            result = backtest_symbol(symbol)
            if result is not None:
                all_results.append(result)
        except Exception as e:
            print("\nERROR:", symbol, "|", e)

    total_signals = sum(r["signals"] for r in all_results)
    total_trades = sum(r["trades"] for r in all_results)
    total_tp2 = sum(r["tp2"] for r in all_results)
    total_tp1 = sum(r["tp1"] for r in all_results)
    total_sl = sum(r["sl"] for r in all_results)
    total_timeout = sum(r["timeout"] for r in all_results)
    total_profit = sum(r["profit"] for r in all_results)
    wins = total_tp2 + total_tp1
    completed = wins + total_sl
    win_rate = (wins / completed * 100) if completed > 0 else 0.0
    symbols_with_signals = sum(1 for r in all_results if r["signals"] > 0)

    print("\n" + "=" * 65)
    print("🏆FINAL RESULT")
    print("=" * 65)
    print("SYMBOLS CHECKED:", len(all_results), "/", len(SYMBOLS))
    print("SYMBOLS WITH SIGNALS:", symbols_with_signals)
    print("TOTAL SIGNALS:", total_signals)
    print("TOTAL TRADES:", total_trades)
    print("TP2:", total_tp2)
    print("TP1:", total_tp1)
    print("SL:", total_sl)
    print("TIMEOUT:", total_timeout)
    print("WIN RATE:", round(win_rate, 2), "%")
    print("TOTAL PROFIT:", round(total_profit, 2), "R")

    print("\nRANKING")
    ranked = sorted(all_results, key=lambda r: r["profit"], reverse=True)
    for idx, r in enumerate(ranked, start=1):
        symbol_win_rate = (
            (r["tp2"] + r["tp1"]) / (r["tp2"] + r["tp1"] + r["sl"]) * 100
            if (r["tp2"] + r["tp1"] + r["sl"]) > 0 else 0.0
        )
        print(
            f"{idx:02d}. {r['symbol']} | Signals: {r['signals']} | "
            f"Trades: {r['trades']} | LONG: {r['long']} | SHORT: {r['short']} | "
            f"Win: {symbol_win_rate:.2f}% | Profit: {r['profit']:.2f}R"
        )


if __name__ == "__main__":
    main()
