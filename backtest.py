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

CANDLE_LIMIT = 3000

MIN_ANALYSIS_CANDLES = 250

SL_ATR = 2.0

TP1_ATR = 2.0

TP2_ATR = 4.0

MAX_HOLD_CANDLES = 100

COST_R = 0.05

MAX_SCORE = 15.0

MIN_QUALITY = 0.67

MIN_LOWER_CONFIRMATIONS = 2

MIN_DIRECTIONAL_RATIO = 0.60

MIN_SCORE_MARGIN = 0.08


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
# BUILD MULTI-TIMEFRAME ANALYSIS
# =========================================================

def analyze_at_time(
    datasets,
    current_time
):

    results = {}

    for timeframe, settings in TIMEFRAMES.items():

        df = datasets.get(
            timeframe
        )

        weight = settings["weight"]

        if df is None:

            results[timeframe] = {
                "signal": "NO TRADE",
                "score": 0,
                "confidence": 0,
                "long_score": 0,
                "short_score": 0,
                "quality": 0,
                "weight": weight,
                "timeframe": timeframe,
                "reason": "داده موجود نیست"
            }

            continue

        # -------------------------------------------------
        # HISTORICAL CUT
        # FIX: use close_time (candle actually closed) instead
        # of open_time / timestamp, to avoid look-ahead bias
        # from candles that have opened but not yet closed.
        # -------------------------------------------------

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

            # If scanner does not expose timestamps,
            # caller must provide already aligned data.
            historical = df.copy()

        if len(historical) < MIN_ANALYSIS_CANDLES:

            results[timeframe] = {
                "signal": "NO TRADE",
                "score": 0,
                "confidence": 0,
                "long_score": 0,
                "short_score": 0,
                "quality": 0,
                "weight": weight,
                "timeframe": timeframe,
                "reason": "داده تاریخی کافی نیست"
            }

            continue

        try:

            result = analyze(
                historical
            )

        except Exception as e:

            results[timeframe] = {
                "signal": "NO TRADE",
                "score": 0,
                "confidence": 0,
                "long_score": 0,
                "short_score": 0,
                "quality": 0,
                "weight": weight,
                "timeframe": timeframe,
                "reason": f"خطای تحلیل: {e}"
            }

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
                MAX_SCORE
            )
        )

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        if signal in [
            "LONG",
            "SHORT"
        ]:

            quality = (
                score /
                MAX_SCORE
            )

        else:

            quality = 0.0

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
        )

        quality = safe_float(
            result.get(
                "quality",
                0
            )
        )

        if weight is None:
            weight = 0

        if quality is None:
            quality = 0

        if signal not in [
            "LONG",
            "SHORT"
        ]:

            continue

        total_valid_weight += weight

        if signal == "LONG":

            long_count += 1

            long_weight += weight

            long_quality += (
                quality *
                weight
            )

        elif signal == "SHORT":

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
        ) or 0
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
    ) or 0

    four_hour_quality = safe_float(
        four_hour.get(
            "quality",
            0
        )
    ) or 0

    # =====================================================
    # LOWER TIMEFRAME CONFIRMATION
    # =====================================================

    lower_long_count = 0
    lower_short_count = 0

    for timeframe in [
        "1h",
        "2h",
        "3h"
    ]:

        result = results.get(
            timeframe,
            {}
        )

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        quality = safe_float(
            result.get(
                "quality",
                0
            )
        ) or 0

        if (
            signal == "LONG"
            and
            quality >= MIN_QUALITY
        ):

            lower_long_count += 1

        elif (
            signal == "SHORT"
            and
            quality >= MIN_QUALITY
        ):

            lower_short_count += 1

    # =====================================================
    # FINAL
    # =====================================================

    final = "NO TRADE"

    # -----------------------------------------------------
    # LONG
    # -----------------------------------------------------

    if (
        daily_signal == "LONG"
        and
        four_hour_signal == "LONG"
        and
        daily_quality >= MIN_QUALITY
        and
        four_hour_quality >= MIN_QUALITY
        and
        lower_long_count >= MIN_LOWER_CONFIRMATIONS
        and
        long_ratio >= MIN_DIRECTIONAL_RATIO
        and
        long_weight > short_weight
        and
        long_quality_ratio > short_quality_ratio
        and
        quality_margin >= MIN_SCORE_MARGIN
    ):

        final = "LONG"

    # -----------------------------------------------------
    # SHORT
    # -----------------------------------------------------

    elif (
        daily_signal == "SHORT"
        and
        four_hour_signal == "SHORT"
        and
        daily_quality >= MIN_QUALITY
        and
        four_hour_quality >= MIN_QUALITY
        and
        lower_short_count >= MIN_LOWER_CONFIRMATIONS
        and
        short_ratio >= MIN_DIRECTIONAL_RATIO
        and
        short_weight > long_weight
        and
        short_quality_ratio > long_quality_ratio
        and
        quality_margin >= MIN_SCORE_MARGIN
    ):

        final = "SHORT"

    return {
        "signal": final,

        "long_weight": long_weight,

        "short_weight": short_weight,

        "long_ratio": long_ratio,

        "short_ratio": short_ratio,

        "long_quality": long_quality_ratio,

        "short_quality": short_quality_ratio,

        "quality_margin": quality_margin,

        "long_count": long_count,

        "short_count": short_count,

        "lower_long_count":
            lower_long_count,

        "lower_short_count":
            lower_short_count,

        "daily_signal":
            daily_signal,

        "daily_quality":
            daily_quality,

        "four_hour_signal":
            four_hour_signal,

        "four_hour_quality":
            four_hour_quality,

        "timeframes":
            results
    }


# =========================================================
# SIMULATE TRADE
# FIX: previously, if TP1 was hit but neither break-even
# nor TP2 was reached before MAX_HOLD_CANDLES, the trade
# was scored as a flat "TIMEOUT" with r = 0.0. This erased
# the partial profit that was already locked in at TP1 and
# systematically understated results. Now TIMEOUT trades are
# marked-to-market against the last available close price,
# respecting whichever stage (pre-TP1 or post-TP1/BE) the
# trade was in when time ran out.
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

    # =====================================================
    # LEVELS
    # =====================================================

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

    last_index = min(
        len(df),
        entry_index + MAX_HOLD_CANDLES + 1
    )

    last_close = entry

    for j in range(entry_index, last_index):

        high = safe_float(df.iloc[j]["high"])
        low = safe_float(df.iloc[j]["low"])
        close = safe_float(df.iloc[j]["close"])

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

        elif signal == "SHORT":

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
    # TIME RAN OUT -> MARK TO MARKET
    # =====================================================

    bars = max(1, last_index - entry_index)

    if not tp1_hit:

        # No partial profit was locked in yet.
        # Mark the open trade to the last known close,
        # clipped between the SL and TP1 distance.
        if signal == "LONG":
            r = (last_close - entry) / atr
        else:
            r = (entry - last_close) / atr

        r = max(-1.0, min(r, TP1_ATR))

        return {
            "result": "TIMEOUT",
            "r": r - COST_R,
            "bars": bars
        }

    else:

        # TP1 already locked in 0.5R. The remaining runner
        # is stopped at break-even, so it can only add value
        # between 0 and 1.0 extra R (from entry to tp2).
        if signal == "LONG":
            progress = (last_close - entry) / (tp2 - entry)
        else:
            progress = (entry - last_close) / (entry - tp2)

        progress = max(0.0, min(progress, 1.0))

        return {
            "result": "TIMEOUT",
            "r": 0.5 + progress - COST_R,
            "bars": bars
        }


# =========================================================
# LOAD ALL DATA
# =========================================================

def load_symbol_data(symbol):

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
                timeframe
            )

            return None

        if len(df) < MIN_ANALYSIS_CANDLES:

            print(
                "NOT ENOUGH DATA:",
                timeframe,
                len(df)
            )

            return None

        datasets[timeframe] = df

    return datasets


# =========================================================
# GET COMMON TIMELINE
# =========================================================

def get_timeline(
    datasets
):

    base = datasets.get(
        "1h"
    )

    if base is None:
        return []

    # If timestamps exist, use them.
    for column in [
        "timestamp",
        "time",
        "open_time"
    ]:

        if column in base.columns:

            return list(
                base[column]
                .iloc[
                    MIN_ANALYSIS_CANDLES:
                ]
            )

    # Fallback:
    # index-based timeline.
    return list(
        range(
            MIN_ANALYSIS_CANDLES,
            len(base)
        )
    )


# =========================================================
# BACKTEST SYMBOL
# =========================================================

def backtest_symbol(symbol):

    print(
        "\n" + "=" * 65
    )

    print(
        "BACKTEST:",
        symbol_name(symbol)
    )

    print(
        "=" * 65
    )

    datasets = load_symbol_data(
        symbol
    )

    if datasets is None:

        return None

    base_df = datasets["1h"]

    timeline = get_timeline(
        datasets
    )

    if not timeline:

        print(
            "NO TIMELINE"
        )

        return None

    trades = []

    # =====================================================
    # BACKTEST LOOP
    # =====================================================

    position_until = MIN_ANALYSIS_CANDLES

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

        # -------------------------------------------------
        # ANALYZE ONLY PAST DATA
        # -------------------------------------------------

        results = analyze_at_time(
            datasets,
            current_time
        )

        final = build_final_signal(
            results
        )

        signal = final["signal"]

        if signal not in [
            "LONG",
            "SHORT"
        ]:

            continue

        # -------------------------------------------------
        # ENTRY ATR
        # -------------------------------------------------

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
            continue

        # -------------------------------------------------
        # ENTRY
        # -------------------------------------------------

        trade = simulate_trade(
            df=base_df,
            entry_index=i,
            signal=signal,
            atr=atr
        )

        if trade is None:
            continue

        trades.append({

            "signal":
                signal,

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
    # NO TRADES
    # =====================================================

    if not trades:

        print(
            "NO TRADES"
        )

        return None

    data = pd.DataFrame(
        trades
    )

    # =====================================================
    # RESULTS
    # =====================================================

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
        tp1 +
        tp2 +
        sl
    )

    wins = (
        tp1 +
        tp2
    )

    win_rate = (
        wins / completed * 100
        if completed > 0
        else 0
    )

    total_r = float(
        data["r"].sum()
    )

    # =====================================================
    # PRINT
    # =====================================================

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

        "symbol":
            symbol,

        "trades":
            len(data),

        "long":
            long_count,

        "short":
            short_count,

        "tp2":
            tp2,

        "tp1":
            tp1,

        "sl":
            sl,

        "timeout":
            timeout,

        "win_rate":
            win_rate,

        "profit":
            total_r
    }


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "\n" + "=" * 65
    )

    print(
        "🚀 MULTI-TIMEFRAME BACKTEST"
    )

    print(
        "=" * 65
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
                "ERROR:",
                symbol,
                e
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
        "\n" + "=" * 65
    )

    print(
        "🏆 FINAL RESULT"
    )

    print(
        "=" * 65
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

    print(
        "\nRANKING"
    )

    for n, result in enumerate(
        results,
        1
    ):

        print(
            n,
            symbol_name(
                result["symbol"]
            ),
            "| Trades:",
            result["trades"],
            "| Win:",
            round(
                result["win_rate"],
                2
            ),
            "%",
            "| Profit:",
            round(
                result["profit"],
                2
            ),
            "R"
        )

    print(
        "\n" + "=" * 65
    )

    print(
        "✅ BACKTEST FINISHED"
    )

    print(
        "=" * 65
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
