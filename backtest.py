# ============================================================
# PATCH FOR backtest.py
#
# backtest.py is 1491 lines and GitHub only serves the first
# ~1000 in the page I can fetch, so I can't safely hand you a
# full replacement file without guessing at the part I can't
# see (the trade-simulation loop + "TOP BLOCK REASONS" report).
#
# Replace these two things in your existing backtest.py with
# what's below, leave everything else (imports, SYMBOLS,
# simulate_trade, load_symbol_data, get_timeline,
# backtest_symbol, and the reporting code) as-is.
# ============================================================

# ---- 1) Replace the SETTINGS block near the top ----

MAX_SCORE = 15.0
MIN_QUALITY = 0.55
MIN_LOWER_CONFIRMATIONS = 1
MIN_DIRECTIONAL_RATIO = 0.45


# ---- 2) Replace the whole build_final_signal() function ----

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
        (daily_signal == "LONG" and daily_quality >= MIN_QUALITY)
        or (four_hour_signal == "LONG" and four_hour_quality >= MIN_QUALITY)
    )
    higher_tf_short = (
        (daily_signal == "SHORT" and daily_quality >= MIN_QUALITY)
        or (four_hour_signal == "SHORT" and four_hour_quality >= MIN_QUALITY)
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

    if (
        higher_tf_long
        and lower_long_count >= MIN_LOWER_CONFIRMATIONS
        and long_ratio >= MIN_DIRECTIONAL_RATIO
        and long_ratio > short_ratio
    ):
        final = "LONG"
    elif (
        higher_tf_short
        and lower_short_count >= MIN_LOWER_CONFIRMATIONS
        and short_ratio >= MIN_DIRECTIONAL_RATIO
        and short_ratio > long_ratio
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
        "lower_long_count": lower_long_count,
        "lower_short_count": lower_short_count,
        "daily_signal": daily_signal,
        "daily_quality": daily_quality,
        "four_hour_signal": four_hour_signal,
        "four_hour_quality": four_hour_quality,
        "timeframes": results
    }
