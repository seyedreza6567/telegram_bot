from multi_timeframe import analyze_timeframes
from risk_manager import calculate_risk


# =========================================================
# SETTINGS
# FIX: loosened from 0.67/0.60/0.08 so altcoins (which trend
# less cleanly than BTC) can actually clear the bar sometimes.
# Previously only BTC ever produced a signal across all 15
# symbols with the stricter values. Keep these identical to
# backtest.py whenever either file changes.
# =========================================================

MIN_QUALITY = 0.60

MIN_LOWER_CONFIRMATIONS = 2

MIN_DIRECTIONAL_RATIO = 0.55

MIN_SCORE_MARGIN = 0.05


# =========================================================
# SAFE FLOAT
# =========================================================

def _safe_float(value):

    try:

        return float(value)

    except Exception:

        return 0.0


# =========================================================
# FINAL SIGNAL
# =========================================================

def final_signal(
    symbol="BTC-SWAP-USDT"
):

    results = analyze_timeframes(
        symbol
    )

    # =====================================================
    # AGGREGATION
    # =====================================================

    long_weight = 0.0
    short_weight = 0.0

    long_quality = 0.0
    short_quality = 0.0

    total_valid_weight = 0.0

    long_count = 0
    short_count = 0

    # -----------------------------------------------------
    # ONLY VALID SIGNALS
    # -----------------------------------------------------

    for timeframe, result in results.items():

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        weight = _safe_float(
            result.get(
                "weight",
                0
            )
        )

        quality = _safe_float(
            result.get(
                "quality",
                result.get(
                    "score_ratio",
                    0
                )
            )
        )

        if weight <= 0:
            continue

        if signal not in [
            "LONG",
            "SHORT"
        ]:

            # IMPORTANT:
            # NO TRADE is NOT confirmation.
            continue

        if quality < 0:
            quality = 0

        if quality > 1:
            quality = 1

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
    # RATIOS
    # =====================================================

    total_weight = sum(
        _safe_float(
            result.get(
                "weight",
                0
            )
        )
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
    # NORMALIZED QUALITY
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

    # =====================================================
    # HIGHER TIMEFRAME FILTER
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

    daily_quality = _safe_float(
        daily.get(
            "quality",
            0
        )
    )

    four_hour_quality = _safe_float(
        four_hour.get(
            "quality",
            0
        )
    )

    # =====================================================
    # LOWER TIMEFRAME CONFIRMATION
    # =====================================================

    lower_long_count = 0
    lower_short_count = 0

    lower_long_weight = 0.0
    lower_short_weight = 0.0

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

        quality = _safe_float(
            result.get(
                "quality",
                0
            )
        )

        weight = _safe_float(
            result.get(
                "weight",
                0
            )
        )

        if (
            signal == "LONG"
            and
            quality >= MIN_QUALITY
        ):

            lower_long_count += 1
            lower_long_weight += weight

        elif (
            signal == "SHORT"
            and
            quality >= MIN_QUALITY
        ):

            lower_short_count += 1
            lower_short_weight += weight

    # =====================================================
    # SCORE MARGIN
    # =====================================================

    quality_margin = abs(
        long_quality_ratio -
        short_quality_ratio
    )

    # =====================================================
    # FINAL DECISION
    # =====================================================

    final = "NO TRADE"

    # =====================================================
    # LONG
    # =====================================================

    long_conditions = (

        # Higher timeframe direction
        daily_signal == "LONG"

        and

        four_hour_signal == "LONG"

        # Higher timeframe quality
        and

        daily_quality >= MIN_QUALITY

        and

        four_hour_quality >= MIN_QUALITY

        # At least two lower TF confirmations
        and

        lower_long_count >= MIN_LOWER_CONFIRMATIONS

        # Overall directional weight
        and

        long_ratio >= MIN_DIRECTIONAL_RATIO

        and

        long_weight > short_weight

        # Quality advantage
        and

        long_quality_ratio >
        short_quality_ratio

        and

        quality_margin >= MIN_SCORE_MARGIN
    )

    if long_conditions:

        final = "LONG"

    # =====================================================
    # SHORT
    # =====================================================

    short_conditions = (

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

        short_quality_ratio >
        long_quality_ratio

        and

        quality_margin >= MIN_SCORE_MARGIN
    )

    if (
        final == "NO TRADE"
        and
        short_conditions
    ):

        final = "SHORT"

    # =====================================================
    # ENTRY
    # =====================================================

    entry_price = None
    atr = None

    # 1H is execution timeframe
    entry_data = results.get(
        "1h",
        {}
    )

    try:

        if entry_data.get(
            "price"
        ) is not None:

            entry_price = float(
                entry_data["price"]
            )

    except Exception:

        entry_price = None

    try:

        if entry_data.get(
            "atr"
        ) is not None:

            atr = float(
                entry_data["atr"]
            )

    except Exception:

        atr = None

    # -----------------------------------------------------
    # FALLBACK
    # -----------------------------------------------------

    if entry_price is None:

        for timeframe in [
            "2h",
            "3h",
            "4h",
            "1d"
        ]:

            data = results.get(
                timeframe,
                {}
            )

            try:

                if data.get(
                    "price"
                ) is not None:

                    entry_price = float(
                        data["price"]
                    )

                    if data.get(
                        "atr"
                    ) is not None:

                        atr = float(
                            data["atr"]
                        )

                    break

            except Exception:

                continue

    # =====================================================
    # RISK
    # =====================================================

    if (
        final in [
            "LONG",
            "SHORT"
        ]
        and
        entry_price is not None
        and
        atr is not None
        and
        atr > 0
    ):

        risk = calculate_risk(
            entry_price=entry_price,
            signal=final,
            atr=atr,
            risk_percent=1.0,
            stop_atr=2.0,
            tp1_atr=2.0,
            tp2_atr=4.0
        )

    else:

        risk = {
            "valid": False,
            "reason": "سیگنال قابل معامله وجود ندارد"
        }

    # =====================================================
    # RETURN
    # =====================================================

    return {

        "signal": final,

        "long_weight": round(
            long_weight,
            3
        ),

        "short_weight": round(
            short_weight,
            3
        ),

        "long_ratio": round(
            long_ratio,
            3
        ),

        "short_ratio": round(
            short_ratio,
            3
        ),

        "long_quality": round(
            long_quality_ratio,
            4
        ),

        "short_quality": round(
            short_quality_ratio,
            4
        ),

        "quality_margin": round(
            quality_margin,
            4
        ),

        "long_count": long_count,

        "short_count": short_count,

        "lower_long_count":
            lower_long_count,

        "lower_short_count":
            lower_short_count,

        "daily_signal":
            daily_signal,

        "daily_quality":
            round(
                daily_quality,
                4
            ),

        "four_hour_signal":
            four_hour_signal,

        "four_hour_quality":
            round(
                four_hour_quality,
                4
            ),

        "entry_price":
            entry_price,

        "atr":
            atr,

        "risk":
            risk,

        "timeframes":
            results
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    result = final_signal()

    print(
        "\n=========================="
    )

    print(
        "FINAL SIGNAL"
    )

    print(
        "=========================="
    )

    print(
        "Signal:",
        result["signal"]
    )

    print(
        "LONG WEIGHT:",
        result["long_weight"]
    )

    print(
        "SHORT WEIGHT:",
        result["short_weight"]
    )

    print(
        "LONG QUALITY:",
        result["long_quality"]
    )

    print(
        "SHORT QUALITY:",
        result["short_quality"]
    )

    print(
        "QUALITY MARGIN:",
        result["quality_margin"]
    )

    print(
        "DAILY:",
        result["daily_signal"],
        result["daily_quality"]
    )

    print(
        "4H:",
        result["four_hour_signal"],
        result["four_hour_quality"]
    )

    print(
        "LOWER LONG:",
        result["lower_long_count"]
    )

    print(
        "LOWER SHORT:",
        result["lower_short_count"]
    )

    print(
        "ENTRY:",
        result["entry_price"]
    )

    print(
        "ATR:",
        result["atr"]
    )

    print(
        "RISK:",
        result["risk"]
    )
