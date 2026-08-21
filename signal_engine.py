from multi_timeframe import analyze_timeframes
from risk_manager import calculate_risk


# =========================================================
# SETTINGS
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
        value = float(value)

        if value != value:  # NaN
            return 0.0

        return value

    except Exception:
        return 0.0


# =========================================================
# CLAMP
# =========================================================

def _clamp(value, minimum=0.0, maximum=1.0):

    value = _safe_float(value)

    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value


# =========================================================
# FINAL SIGNAL
# =========================================================

def final_signal(
    symbol="BTC-SWAP-USDT"
):

    results = analyze_timeframes(symbol)

    # =====================================================
    # AGGREGATION
    # =====================================================

    long_weight = 0.0
    short_weight = 0.0

    long_quality_weighted = 0.0
    short_quality_weighted = 0.0

    total_weight = 0.0

    long_count = 0
    short_count = 0

    # =====================================================
    # PROCESS TIMEFRAMES
    # =====================================================

    for timeframe, result in results.items():

        if not isinstance(result, dict):
            continue

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        weight = _safe_float(
            result.get(
                "weight",
                0.0
            )
        )

        if weight <= 0:
            continue

        total_weight += weight

        # -------------------------------------------------
        # QUALITY
        # -------------------------------------------------
        #
        # Prefer score_ratio from analysis_engine.
        # Fallback to quality for compatibility.
        #

        quality = _safe_float(
            result.get(
                "score_ratio",
                result.get(
                    "quality",
                    0.0
                )
            )
        )

        quality = _clamp(quality)

        # -------------------------------------------------
        # LONG
        # -------------------------------------------------

        if signal == "LONG":

            long_count += 1

            long_weight += weight

            long_quality_weighted += (
                quality * weight
            )

        # -------------------------------------------------
        # SHORT
        # -------------------------------------------------

        elif signal == "SHORT":

            short_count += 1

            short_weight += weight

            short_quality_weighted += (
                quality * weight
            )

        # -------------------------------------------------
        # NO TRADE
        # -------------------------------------------------

        else:

            continue

    # =====================================================
    # WEIGHT RATIOS
    # =====================================================

    if total_weight > 0:

        long_ratio = (
            long_weight /
            total_weight
        )

        short_ratio = (
            short_weight /
            total_weight
        )

    else:

        long_ratio = 0.0
        short_ratio = 0.0

    # =====================================================
    # QUALITY
    # =====================================================
    #
    # IMPORTANT:
    # Normalize each direction by ITS OWN weight.
    #
    # This prevents a direction with fewer signals from
    # artificially getting a quality advantage.
    #

    if long_weight > 0:

        long_quality_ratio = (
            long_quality_weighted /
            long_weight
        )

    else:

        long_quality_ratio = 0.0

    if short_weight > 0:

        short_quality_ratio = (
            short_quality_weighted /
            short_weight
        )

    else:

        short_quality_ratio = 0.0

    # =====================================================
    # QUALITY MARGIN
    # =====================================================

    quality_margin = abs(
        long_quality_ratio -
        short_quality_ratio
    )

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

    if not isinstance(daily, dict):
        daily = {}

    if not isinstance(four_hour, dict):
        four_hour = {}

    daily_signal = daily.get(
        "signal",
        "NO TRADE"
    )

    four_hour_signal = four_hour.get(
        "signal",
        "NO TRADE"
    )

    daily_quality = _clamp(
        daily.get(
            "score_ratio",
            daily.get(
                "quality",
                0.0
            )
        )
    )

    four_hour_quality = _clamp(
        four_hour.get(
            "score_ratio",
            four_hour.get(
                "quality",
                0.0
            )
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

        if not isinstance(result, dict):
            continue

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        quality = _clamp(
            result.get(
                "score_ratio",
                result.get(
                    "quality",
                    0.0
                )
            )
        )

        weight = _safe_float(
            result.get(
                "weight",
                0.0
            )
        )

        # -------------------------------------------------
        # LONG CONFIRMATION
        # -------------------------------------------------

        if (
            signal == "LONG"
            and
            quality >= MIN_QUALITY
        ):

            lower_long_count += 1

            lower_long_weight += weight

        # -------------------------------------------------
        # SHORT CONFIRMATION
        # -------------------------------------------------

        elif (
            signal == "SHORT"
            and
            quality >= MIN_QUALITY
        ):

            lower_short_count += 1

            lower_short_weight += weight

    # =====================================================
    # DIRECTIONAL SCORE MARGIN
    # =====================================================

    # Compare actual weighted directional quality.
    #
    # Example:
    #
    # LONG quality = 0.75
    # SHORT quality = 0.60
    #
    # margin = 0.15
    #

    quality_margin = abs(
        long_quality_ratio -
        short_quality_ratio
    )

    # =====================================================
    # FINAL DECISION
    # =====================================================

    final = "NO TRADE"

    # =====================================================
    # LONG CONDITIONS
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

        # Lower timeframe confirmation
        and

        lower_long_count >= MIN_LOWER_CONFIRMATIONS

        # Overall directional weight
        and

        long_ratio >= MIN_DIRECTIONAL_RATIO

        # LONG must dominate SHORT
        and

        long_weight > short_weight

        # LONG quality must dominate SHORT
        and

        long_quality_ratio >
        short_quality_ratio

        # Minimum quality advantage
        and

        quality_margin >= MIN_SCORE_MARGIN
    )

    if long_conditions:

        final = "LONG"

    # =====================================================
    # SHORT CONDITIONS
    # =====================================================

    short_conditions = (

        # Higher timeframe direction
        daily_signal == "SHORT"

        and

        four_hour_signal == "SHORT"

        # Higher timeframe quality
        and

        daily_quality >= MIN_QUALITY

        and

        four_hour_quality >= MIN_QUALITY

        # Lower timeframe confirmation
        and

        lower_short_count >= MIN_LOWER_CONFIRMATIONS

        # Overall directional weight
        and

        short_ratio >= MIN_DIRECTIONAL_RATIO

        # SHORT must dominate LONG
        and

        short_weight > long_weight

        # SHORT quality must dominate LONG
        and

        short_quality_ratio >
        long_quality_ratio

        # Minimum quality advantage
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
    # ENTRY DATA
    # =====================================================

    entry_price = None
    atr = None

    # 1H = execution timeframe
    entry_data = results.get(
        "1h",
        {}
    )

    if not isinstance(entry_data, dict):
        entry_data = {}

    # =====================================================
    # ENTRY PRICE
    # =====================================================

    try:

        if entry_data.get(
            "price"
        ) is not None:

            entry_price = float(
                entry_data["price"]
            )

    except Exception:

        entry_price = None

    # =====================================================
    # ATR
    # =====================================================

    try:

        if entry_data.get(
            "atr"
        ) is not None:

            atr = float(
                entry_data["atr"]
            )

    except Exception:

        atr = None

    # =====================================================
    # FALLBACK ENTRY DATA
    # =====================================================

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

            if not isinstance(data, dict):
                continue

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
    # RISK MANAGEMENT
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

        "lower_long_weight":
            round(
                lower_long_weight,
                3
            ),

        "lower_short_weight":
            round(
                lower_short_weight,
                3
            ),

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
        "LONG RATIO:",
        result["long_ratio"]
    )

    print(
        "SHORT RATIO:",
        result["short_ratio"]
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
