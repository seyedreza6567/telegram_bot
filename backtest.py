import time

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
    "1h": {
        "interval": "1h",
        "weight": 1.0,
    },
    "2h": {
        "interval": "2h",
        "weight": 1.25,
    },
    "3h": {
        "interval": "3h",
        "weight": 1.50,
    },
    "4h": {
        "interval": "4h",
        "weight": 2.0,
    },
    "1d": {
        "interval": "1d",
        "weight": 3.0,
    },
}


# =========================================================
# DATA
# =========================================================

CANDLE_LIMIT = 3000
MIN_ANALYSIS_CANDLES = 250


# =========================================================
# RISK
# =========================================================

SL_ATR = 2.0
TP1_ATR = 2.0
TP2_ATR = 4.0

MAX_HOLD_CANDLES = 100

COST_R = 0.05


# =========================================================
# SIGNAL FILTERS
#
# IMPORTANT:
# We do NOT require 1D + 4H + 2 lower TFs anymore.
#
# The previous rule was too restrictive:
#
#     1D same direction
#     4H same direction
#     2 of 1H/2H/3H same direction
#
# That effectively required almost the entire market
# structure to agree before entering.
#
# New rule:
#   - at least 3 valid directional timeframes
#   - higher timeframe confirmation is still required
#   - weighted direction must be >= 55%
#   - quality advantage must exist
# =========================================================

MIN_QUALITY = 0.60

MIN_DIRECTIONAL_RATIO = 0.55

MIN_SCORE_MARGIN = 0.05

MIN_VALID_TIMEFRAMES = 3

REQUIRE_HIGHER_TIMEFRAME_CONFIRMATION = True


# =========================================================
# API DELAYS
# =========================================================

TIMEFRAME_SLEEP_SECONDS = 0.7
SYMBOL_SLEEP_SECONDS = 1.5


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


# =========================================================
# SYMBOL NAME
# =========================================================

def symbol_name(symbol):

    return symbol.replace(
        "-SWAP-USDT",
        ""
    )


# =========================================================
# PREPARE DATA
# =========================================================

def prepare_dataframe(df):

    if df is None:
        return None

    if len(df) == 0:
        return None

    df = df.copy()

    df = df.reset_index(
        drop=True
    )

    return df


# =========================================================
# HISTORICAL DATA
# =========================================================

def get_historical_data(
    df,
    current_time
):

    if df is None:
        return None

    # -----------------------------------------------------
    # IMPORTANT:
    # current_time is the OPEN time of the current 1H candle.
    # Therefore only candles that CLOSED before this moment
    # are allowed for analysis.
    # -----------------------------------------------------

    if "close_time" in df.columns:

        historical = df[
            df["close_time"] <= current_time
        ].copy()

    elif "timestamp" in df.columns:

        historical = df[
            df["timestamp"] < current_time
        ].copy()

    elif "time" in df.columns:

        historical = df[
            df["time"] < current_time
        ].copy()

    elif "open_time" in df.columns:

        historical = df[
            df["open_time"] < current_time
        ].copy()

    else:

        historical = df.copy()

    return historical


# =========================================================
# EMPTY TIMEFRAME RESULT
# =========================================================

def empty_result(
    timeframe,
    weight,
    reason
):

    return {
        "signal": "NO TRADE",
        "score": 0.0,
        "confidence": 0.0,

        "long_score": 0.0,
        "short_score": 0.0,

        "quality": 0.0,
        "score_ratio": 0.0,

        "weight": weight,
        "timeframe": timeframe,

        "price": None,
        "atr": None,

        "reason": reason
    }


# =========================================================
# ANALYZE AT HISTORICAL TIME
# =========================================================

def analyze_at_time(
    datasets,
    current_time
):

    results = {}

    for timeframe, settings in TIMEFRAMES.items():

        weight = settings["weight"]

        df = datasets.get(
            timeframe
        )

        if df is None:

            results[timeframe] = empty_result(
                timeframe,
                weight,
                "داده موجود نیست"
            )

            continue

        historical = get_historical_data(
            df,
            current_time
        )

        if historical is None:

            results[timeframe] = empty_result(
                timeframe,
                weight,
                "داده تاریخی موجود نیست"
            )

            continue

        if len(historical) < MIN_ANALYSIS_CANDLES:

            results[timeframe] = empty_result(
                timeframe,
                weight,
                f"داده کافی نیست: {len(historical)}"
            )

            continue

        try:

            result = analyze(
                historical
            )

        except Exception as e:

            results[timeframe] = empty_result(
                timeframe,
                weight,
                f"خطای تحلیل: {e}"
            )

            continue

        if not isinstance(
            result,
            dict
        ):

            results[timeframe] = empty_result(
                timeframe,
                weight,
                "خروجی تحلیل نامعتبر"
            )

            continue

        result = result.copy()

        score = safe_float(
            result.get(
                "score",
                0
            )
        )

        if score is None:
            score = 0.0

        score = max(
            0.0,
            min(
                score,
                15.0
            )
        )

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        if signal not in [
            "LONG",
            "SHORT"
        ]:

            quality = 0.0

        else:

            quality = score / 15.0

        result["score"] = score

        result["quality"] = quality

        result["score_ratio"] = quality

        result["weight"] = weight

        result["timeframe"] = timeframe

        results[timeframe] = result

    return results


# =========================================================
# FINAL SIGNAL
# =========================================================

def build_final_signal(
    results,
    diagnostic=False
):

    long_weight = 0.0
    short_weight = 0.0

    long_quality = 0.0
    short_quality = 0.0

    total_valid_weight = 0.0

    long_count = 0
    short_count = 0

    valid_count = 0

    # =====================================================
    # COLLECT
    # =====================================================

    for timeframe, result in results.items():

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        weight = safe_float(
            result.get(
                "weight",
                0
            )
        ) or 0.0

        quality = safe_float(
            result.get(
                "quality",
                0
            )
        ) or 0.0

        if signal not in [
            "LONG",
            "SHORT"
        ]:

            continue

        valid_count += 1

        total_valid_weight += weight

        if signal == "LONG":

            long_count += 1

            long_weight += weight

            long_quality += (
                quality *
                weight
            )

        else:

            short_count += 1

            short_weight += weight

            short_quality += (
                quality *
                weight
            )

    # =====================================================
    # TOTAL WEIGHT
    # =====================================================

    total_weight = sum(
        safe_float(
            result.get(
                "weight",
                0
            )
        ) or 0.0
        for result in results.values()
    )

    if total_weight <= 0:

        total_weight = 1.0

    long_ratio = (
        long_weight /
        total_weight
    )

    short_ratio = (
        short_weight /
        total_weight
    )

    # =====================================================
    # QUALITY
    # =====================================================

    if total_valid_weight > 0:

        long_quality_ratio = (
            long_quality /
            total_valid_weight
        )

        short_quality_ratio = (
            short_quality /
            total_valid_weight
        )

    else:

        long_quality_ratio = 0.0
        short_quality_ratio = 0.0

    quality_margin = abs(
        long_quality_ratio -
        short_quality_ratio
    )

    # =====================================================
    # HIGHER TIMEFRAMES
    # =====================================================

    daily = results.get(
        "1d",
        {}
    )

    four_hour = results.get(
        "4h",
        {}
    )

    daily_signal = daily.get(
        "signal",
        "NO TRADE"
    )

    four_hour_signal = four_hour.get(
        "signal",
        "NO TRADE"
    )

    daily_quality = safe_float(
        daily.get(
            "quality",
            0
        )
    ) or 0.0

    four_hour_quality = safe_float(
        four_hour.get(
            "quality",
            0
        )
    ) or 0.0

    # =====================================================
    # LONG
    # =====================================================

    long_higher_ok = (

        daily_signal == "LONG"

        and

        four_hour_signal == "LONG"

        and

        daily_quality >= MIN_QUALITY

        and

        four_hour_quality >= MIN_QUALITY
    )

    # =====================================================
    # SHORT
    # =====================================================

    short_higher_ok = (

        daily_signal == "SHORT"

        and

        four_hour_signal == "SHORT"

        and

        daily_quality >= MIN_QUALITY

        and

        four_hour_quality >= MIN_QUALITY
    )

    # =====================================================
    # DIRECTIONAL CONFIRMATION
    # =====================================================

    long_direction_ok = (

        long_count >= 3

        and

        long_ratio >= MIN_DIRECTIONAL_RATIO

        and

        long_weight > short_weight
    )

    short_direction_ok = (

        short_count >= 3

        and

        short_ratio >= MIN_DIRECTIONAL_RATIO

        and

        short_weight > long_weight
    )

    # =====================================================
    # QUALITY
    # =====================================================

    long_quality_ok = (

        long_quality_ratio >
        short_quality_ratio

        and

        quality_margin >= MIN_SCORE_MARGIN
    )

    short_quality_ok = (

        short_quality_ratio >
        long_quality_ratio

        and

        quality_margin >= MIN_SCORE_MARGIN
    )

    # =====================================================
    # FINAL
    # =====================================================

    final = "NO TRADE"

    if (
        valid_count >= MIN_VALID_TIMEFRAMES
        and
        long_direction_ok
        and
        long_quality_ok
        and
        (
            not REQUIRE_HIGHER_TIMEFRAME_CONFIRMATION
            or
            long_higher_ok
        )
    ):

        final = "LONG"

    elif (
        valid_count >= MIN_VALID_TIMEFRAMES
        and
        short_direction_ok
        and
        short_quality_ok
        and
        (
            not REQUIRE_HIGHER_TIMEFRAME_CONFIRMATION
            or
            short_higher_ok
        )
    ):

        final = "SHORT"

    # =====================================================
    # DIAGNOSTIC REASON
    # =====================================================

    reason = "OK"

    if final == "NO TRADE":

        if valid_count < MIN_VALID_TIMEFRAMES:

            reason = (
                f"VALID TF کم است: "
                f"{valid_count}/{MIN_VALID_TIMEFRAMES}"
            )

        elif (
            not long_direction_ok
            and
            not short_direction_ok
        ):

            reason = (
                "تأیید جهت کافی نیست"
            )

        elif (
            not long_quality_ok
            and
            not short_quality_ok
        ):

            reason = (
                "برتری کیفیت کافی نیست"
            )

        elif (
            REQUIRE_HIGHER_TIMEFRAME_CONFIRMATION
            and
            not long_higher_ok
            and
            not short_higher_ok
        ):

            reason = (
                "1D و 4H هم‌جهت نیستند"
            )

        else:

            reason = (
                "شرایط ورود کامل نیست"
            )

    if diagnostic:

        print(
            "\n--- SIGNAL DIAGNOSTIC ---"
        )

        for timeframe in [
            "1h",
            "2h",
            "3h",
            "4h",
            "1d"
        ]:

            r = results.get(
                timeframe,
                {}
            )

            print(
                f"{timeframe}: "
                f"{r.get('signal', 'NO TRADE')} | "
                f"score={r.get('score', 0):.2f} | "
                f"quality={r.get('quality', 0):.2f}"
            )

        print(
            "VALID:",
            valid_count
        )

        print(
            "LONG:",
            long_count,
            "weight=",
            round(long_weight, 2),
            "ratio=",
            round(long_ratio, 2)
        )

        print(
            "SHORT:",
            short_count,
            "weight=",
            round(short_weight, 2),
            "ratio=",
            round(short_ratio, 2)
        )

        print(
            "1D:",
            daily_signal,
            round(daily_quality, 2)
        )

        print(
            "4H:",
            four_hour_signal,
            round(four_hour_quality, 2)
        )

        print(
            "MARGIN:",
            round(quality_margin, 3)
        )

        print(
            "FINAL:",
            final,
            "|",
            reason
        )

    return {
        "signal": final,

        "reason": reason,

        "valid_count": valid_count,

        "long_weight": long_weight,
        "short_weight": short_weight,

        "long_ratio": long_ratio,
        "short_ratio": short_ratio,

        "long_quality": long_quality_ratio,
        "short_quality": short_quality_ratio,

        "quality_margin": quality_margin,

        "long_count": long_count,
        "short_count": short_count,

        "daily_signal": daily_signal,
        "daily_quality": daily_quality,

        "four_hour_signal": four_hour_signal,
        "four_hour_quality": four_hour_quality,

        "timeframes": results
    }


# =========================================================
# SIMULATE TRADE
# =========================================================

def simulate_trade(
    df,
    entry_index,
    signal,
    atr
):

    entry = safe_float(
        df.iloc[entry_index]["open"]
    )

    if entry is None:
        return None

    if atr is None or atr <= 0:
        return None

    if signal == "LONG":

        sl = entry - (
            atr * SL_ATR
        )

        tp1 = entry + (
            atr * TP1_ATR
        )

        tp2 = entry + (
            atr * TP2_ATR
        )

    elif signal == "SHORT":

        sl = entry + (
            atr * SL_ATR
        )

        tp1 = entry - (
            atr * TP1_ATR
        )

        tp2 = entry - (
            atr * TP2_ATR
        )

    else:

        return None

    tp1_hit = False

    last_index = min(
        len(df),
        entry_index +
        MAX_HOLD_CANDLES +
        1
    )

    last_close = entry

    for j in range(
        entry_index,
        last_index
    ):

        high = safe_float(
            df.iloc[j]["high"]
        )

        low = safe_float(
            df.iloc[j]["low"]
        )

        close = safe_float(
            df.iloc[j]["close"]
        )

        if high is None or low is None:
            continue

        if close is not None:
            last_close = close

        # =================================================
        # LONG
        # =================================================

        if signal == "LONG":

            if not tp1_hit:

                hit_sl = low <= sl
                hit_tp1 = high >= tp1

                if hit_sl:

                    return {
                        "result": "SL",
                        "r": -1.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp1:

                    tp1_hit = True

                    if high >= tp2:

                        return {
                            "result": "TP2",
                            "r": 1.5 - COST_R,
                            "bars": j - entry_index + 1
                        }

                    continue

            else:

                hit_be = low <= entry
                hit_tp2 = high >= tp2

                if hit_be:

                    return {
                        "result": "TP1",
                        "r": 0.5 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp2:

                    return {
                        "result": "TP2",
                        "r": 1.5 - COST_R,
                        "bars": j - entry_index + 1
                    }

        # =================================================
        # SHORT
        # =================================================

        else:

            if not tp1_hit:

                hit_sl = high >= sl
                hit_tp1 = low <= tp1

                if hit_sl:

                    return {
                        "result": "SL",
                        "r": -1.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp1:

                    tp1_hit = True

                    if low <= tp2:

                        return {
                            "result": "TP2",
                            "r": 1.5 - COST_R,
                            "bars": j - entry_index + 1
                        }

                    continue

            else:

                hit_be = high >= entry
                hit_tp2 = low <= tp2

                if hit_be:

                    return {
                        "result": "TP1",
                        "r": 0.5 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp2:

                    return {
                        "result": "TP2",
                        "r": 1.5 - COST_R,
                        "bars": j - entry_index + 1
                    }

    # =====================================================
    # TIMEOUT
    # =====================================================

    bars = max(
        1,
        last_index - entry_index
    )

    if not tp1_hit:

        if signal == "LONG":

            r = (
                last_close - entry
            ) / atr

        else:

            r = (
                entry - last_close
            ) / atr

        r = max(
            -1.0,
            min(
                r,
                TP1_ATR
            )
        )

        return {
            "result": "TIMEOUT",
            "r": r - COST_R,
            "bars": bars
        }

    # TP1 already hit
    if signal == "LONG":

        progress = (
            last_close - entry
        ) / (
            tp2 - entry
        )

    else:

        progress = (
            entry - last_close
        ) / (
            entry - tp2
        )

    progress = max(
        0.0,
        min(
            progress,
            1.0
        )
    )

    return {
        "result": "TIMEOUT",
        "r": 0.5 + progress - COST_R,
        "bars": bars
    }


# =========================================================
# LOAD SYMBOL DATA
# =========================================================

def load_symbol_data(
    symbol
):

    datasets = {}

    for timeframe, settings in TIMEFRAMES.items():

        print(
            f"Loading {symbol_name(symbol)} "
            f"{timeframe}..."
        )

        try:

            df = get_klines(
                symbol=symbol,
                interval=settings["interval"],
                limit=CANDLE_LIMIT
            )

        except Exception as e:

            print(
                "DATA ERROR:",
                symbol_name(symbol),
                timeframe,
                e
            )

            return None

        df = prepare_dataframe(
            df
        )

        if df is None:

            print(
                "NO DATA:",
                symbol_name(symbol),
                timeframe
            )

            return None

        if len(df) < MIN_ANALYSIS_CANDLES:

            print(
                "NOT ENOUGH DATA:",
                symbol_name(symbol),
                timeframe,
                len(df)
            )

            return None

        datasets[timeframe] = df

        time.sleep(
            TIMEFRAME_SLEEP_SECONDS
        )

    return datasets


# =========================================================
# TIMELINE
# =========================================================

def get_timeline(
    datasets
):

    base = datasets.get(
        "1h"
    )

    if base is None:
        return []

    if "open_time" in base.columns:

        return list(
            base["open_time"]
            .iloc[
                MIN_ANALYSIS_CANDLES:
            ]
        )

    if "timestamp" in base.columns:

        return list(
            base["timestamp"]
            .iloc[
                MIN_ANALYSIS_CANDLES:
            ]
        )

    if "time" in base.columns:

        return list(
            base["time"]
            .iloc[
                MIN_ANALYSIS_CANDLES:
            ]
        )

    return list(
        range(
            MIN_ANALYSIS_CANDLES,
            len(base)
        )
    )


# =========================================================
# BACKTEST ONE SYMBOL
# =========================================================

def backtest_symbol(
    symbol
):

    print(
        "\n" + "=" * 70
    )

    print(
        "BACKTEST:",
        symbol_name(symbol)
    )

    print(
        "=" * 70
    )

    datasets = load_symbol_data(
        symbol
    )

    if datasets is None:

        print(
            "SKIPPED:",
            symbol_name(symbol),
            "DATA FAILURE"
        )

        return None

    base_df = datasets["1h"]

    timeline = get_timeline(
        datasets
    )

    if not timeline:

        print(
            "SKIPPED:",
            symbol_name(symbol),
            "NO TIMELINE"
        )

        return None

    trades = []

    position_until = MIN_ANALYSIS_CANDLES

    signal_counts = {
        "LONG": 0,
        "SHORT": 0,
        "NO TRADE": 0
    }

    blocked_reasons = {}

    # =====================================================
    # LOOP
    # =====================================================

    for position, current_time in enumerate(
        timeline
    ):

        i = (
            MIN_ANALYSIS_CANDLES +
            position
        )

        if i >= len(base_df) - 1:
            break

        if i < position_until:
            continue

        results = analyze_at_time(
            datasets,
            current_time
        )

        final = build_final_signal(
            results,
            diagnostic=False
        )

        signal = final["signal"]

        signal_counts[
            signal
        ] = signal_counts.get(
            signal,
            0
        ) + 1

        if signal == "NO TRADE":

            reason = final["reason"]

            blocked_reasons[
                reason
            ] = blocked_reasons.get(
                reason,
                0
            ) + 1

            continue

        entry_data = results.get(
            "1h",
            {}
        )

        atr = safe_float(
            entry_data.get(
                "atr"
            )
        )

        if atr is None or atr <= 0:

            blocked_reasons[
                "ATR نامعتبر"
            ] = blocked_reasons.get(
                "ATR نامعتبر",
                0
            ) + 1

            continue

        trade = simulate_trade(
            df=base_df,
            entry_index=i,
            signal=signal,
            atr=atr
        )

        if trade is None:
            continue

        trades.append({

            "signal": signal,

            "result":
                trade["result"],

            "r":
                trade["r"],

            "bars":
                trade["bars"],

            "entry_index":
                i,

            "atr":
                atr,

            "daily":
                final["daily_signal"],

            "four_hour":
                final["four_hour_signal"]
        })

        position_until = (
            i +
            max(
                1,
                trade["bars"]
            )
        )

    # =====================================================
    # PRINT DIAGNOSTIC
    # =====================================================

    print(
        "\nSIGNAL SUMMARY:",
        symbol_name(symbol)
    )

    print(
        "LONG SIGNALS:",
        signal_counts["LONG"]
    )

    print(
        "SHORT SIGNALS:",
        signal_counts["SHORT"]
    )

    print(
        "NO TRADE:",
        signal_counts["NO TRADE"]
    )

    print(
        "TOP BLOCK REASONS:"
    )

    for reason, count in sorted(
        blocked_reasons.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]:

        print(
            " ",
            count,
            "x",
            reason
        )

    # =====================================================
    # NO TRADES
    # =====================================================

    if not trades:

        print(
            "\nNO TRADES:",
            symbol_name(symbol)
        )

        return {
            "symbol": symbol,
            "trades": 0,
            "long": 0,
            "short": 0,
            "tp2": 0,
            "tp1": 0,
            "sl": 0,
            "timeout": 0,
            "win_rate": 0.0,
            "profit": 0.0,
            "signals": (
                signal_counts["LONG"] +
                signal_counts["SHORT"]
            )
        }

    data = pd.DataFrame(
        trades
    )

    tp2 = len(
        data[
            data["result"] == "TP2"
        ]
    )

    tp1 = len(
        data[
            data["result"] == "TP1"
        ]
    )

    sl = len(
        data[
            data["result"] == "SL"
        ]
    )

    timeout = len(
        data[
            data["result"] == "TIMEOUT"
        ]
    )

    long_count = len(
        data[
            data["signal"] == "LONG"
        ]
    )

    short_count = len(
        data[
            data["signal"] == "SHORT"
        ]
    )

    completed = (
        tp2 +
        tp1 +
        sl
    )

    wins = (
        tp2 +
        tp1
    )

    win_rate = (
        wins / completed * 100
        if completed > 0
        else 0
    )

    total_r = float(
        data["r"].sum()
    )

    print(
        "\nRESULT:",
        symbol_name(symbol)
    )

    print(
        "Trades:",
        len(data)
    )

    print(
        "LONG:",
        long_count
    )

    print(
        "SHORT:",
        short_count
    )

    print(
        "TP2:",
        tp2
    )

    print(
        "TP1:",
        tp1
    )

    print(
        "SL:",
        sl
    )

    print(
        "TIMEOUT:",
        timeout
    )

    print(
        "WIN RATE:",
        round(
            win_rate,
            2
        ),
        "%"
    )

    print(
        "PROFIT:",
        round(
            total_r,
            2
        ),
        "R"
    )

    return {
        "symbol": symbol,
        "trades": len(data),
        "long": long_count,
        "short": short_count,
        "tp2": tp2,
        "tp1": tp1,
        "sl": sl,
        "timeout": timeout,
        "win_rate": win_rate,
        "profit": total_r,
        "signals": (
            signal_counts["LONG"] +
            signal_counts["SHORT"]
        )
    }


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "\n" + "=" * 70
    )

    print(
        "🚀 MULTI-TIMEFRAME BACKTEST"
    )

    print(
        "=" * 70
    )

    print(
        "SYMBOLS:",
        len(SYMBOLS)
    )

    print(
        "NEW FILTER:"
    )

    print(
        "  Minimum valid TF:",
        MIN_VALID_TIMEFRAMES
    )

    print(
        "  Minimum quality:",
        MIN_QUALITY
    )

    print(
        "  Direction ratio:",
        MIN_DIRECTIONAL_RATIO
    )

    print(
        "  Higher TF confirmation:",
        REQUIRE_HIGHER_TIMEFRAME_CONFIRMATION
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
                "\nFATAL SYMBOL ERROR:",
                symbol_name(symbol),
                e
            )

        time.sleep(
            SYMBOL_SLEEP_SECONDS
        )

    if not results:

        print(
            "\nNO RESULTS"
        )

        return

    results = sorted(
        results,
        key=lambda x: x["profit"],
        reverse=True
    )

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

    total_timeout = sum(
        x["timeout"]
        for x in results
    )

    total_profit = sum(
        x["profit"]
        for x in results
    )

    total_signals = sum(
        x["signals"]
        for x in results
    )

    completed = (
        total_tp2 +
        total_tp1 +
        total_sl
    )

    wins = (
        total_tp2 +
        total_tp1
    )

    win_rate = (
        wins / completed * 100
        if completed > 0
        else 0
    )

    # =====================================================
    # FINAL
    # =====================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "🏆 FINAL RESULT"
    )

    print(
        "=" * 70
    )

    print(
        "SYMBOLS CHECKED:",
        len(results),
        "/",
        len(SYMBOLS)
    )

    print(
        "SYMBOLS WITH SIGNALS:",
        sum(
            1
            for x in results
            if x["signals"] > 0
        )
    )

    print(
        "TOTAL SIGNALS:",
        total_signals
    )

    print(
        "TOTAL TRADES:",
        total_trades
    )

    print(
        "TP2:",
        total_tp2
    )

    print(
        "TP1:",
        total_tp1
    )

    print(
        "SL:",
        total_sl
    )

    print(
        "TIMEOUT:",
        total_timeout
    )

    print(
        "WIN RATE:",
        round(
            win_rate,
            2
        ),
        "%"
    )

    print(
        "TOTAL PROFIT:",
        round(
            total_profit,
            2
        ),
        "R"
    )

    # =====================================================
    # RANKING
    # =====================================================

    print(
        "\nRANKING"
    )

    for n, result in enumerate(
        results,
        1
    ):

        print(
            f"{n:02d}. "
            f"{symbol_name(result['symbol'])} | "
            f"Signals: {result['signals']} | "
            f"Trades: {result['trades']} | "
            f"LONG: {result['long']} | "
            f"SHORT: {result['short']} | "
            f"Win: {result['win_rate']:.2f}% | "
            f"Profit: {result['profit']:.2f}R"
        )

    print(
        "\n" + "=" * 70
    )

    print(
        "✅ BACKTEST FINISHED"
    )

    print(
        "=" * 70
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
