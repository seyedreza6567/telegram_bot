from multi_timeframe import analyze_timeframes
from risk_manager import calculate_risk


# =========================================================
# SETTINGS
# =========================================================
MIN_QUALITY = 0.55
MIN_LOWER_CONFIRMATIONS = 1
MIN_DIRECTIONAL_RATIO = 0.45


def _safe_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0


# =========================================================
# FINAL SIGNAL
# =========================================================
def final_signal(symbol="BTC-SWAP-USDT"):
    results = analyze_timeframes(symbol)

    long_weight = 0.0
    short_weight = 0.0
    long_quality = 0.0
    short_quality = 0.0
    total_valid_weight = 0.0
    long_count = 0
    short_count = 0

    for timeframe, result in results.items():
        signal = result.get("signal", "NO TRADE")
        weight = _safe_float(result.get("weight", 0))
        quality = _safe_float(result.get("quality", result.get("score_ratio", 0)))

        if weight <= 0:
            continue
        if signal not in ["LONG", "SHORT"]:
            continue

        quality = max(0.0, min(quality, 1.0))
        total_valid_weight += weight

        if signal == "LONG":
            long_count += 1
            long_weight += weight
            long_quality += quality * weight
        elif signal == "SHORT":
            short_count += 1
            short_weight += weight
            short_quality += quality * weight

    total_weight = sum(_safe_float(r.get("weight", 0)) for r in results.values())
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

    # =====================================================
    # HIGHER TIMEFRAME CONTEXT
    # FIX: previously required BOTH 1d AND 4h to already show the
    # same signal with quality >= 0.67 before anything else was even
    # checked. That's asking two independent noisy classifiers to
    # agree on the same candle, on top of everything else below -
    # the actual reason only TRX (which trended hard the whole
    # window) ever produced a trade. Now either one aligning with
    # the overall weighted direction is enough.
    # =====================================================
    daily = results.get("1d", {})
    four_hour = results.get("4h", {})
    daily_signal = daily.get("signal", "NO TRADE")
    four_hour_signal = four_hour.get("signal", "NO TRADE")
    daily_quality = _safe_float(daily.get("quality", 0))
    four_hour_quality = _safe_float(four_hour.get("quality", 0))

    higher_tf_long = (
        (daily_signal == "LONG" and daily_quality >= MIN_QUALITY)
        or (four_hour_signal == "LONG" and four_hour_quality >= MIN_QUALITY)
    )
    higher_tf_short = (
        (daily_signal == "SHORT" and daily_quality >= MIN_QUALITY)
        or (four_hour_signal == "SHORT" and four_hour_quality >= MIN_QUALITY)
    )

    # =====================================================
    # LOWER TIMEFRAME CONFIRMATION
    # FIX: needed >=2 of 1h/2h/3h before; now 1 is enough as long as
    # the overall weighted direction (long_ratio/short_ratio) agrees.
    # =====================================================
    lower_long_count = 0
    lower_short_count = 0

    for timeframe in ["1h", "2h", "3h"]:
        result = results.get(timeframe, {})
        signal = result.get("signal", "NO TRADE")
        quality = _safe_float(result.get("quality", 0))

        if signal == "LONG" and quality >= MIN_QUALITY:
            lower_long_count += 1
        elif signal == "SHORT" and quality >= MIN_QUALITY:
            lower_short_count += 1

    # =====================================================
    # FINAL DECISION
    # FIX: dropped the redundant quality_margin / long_weight>short_weight
    # / long_quality_ratio>short_quality_ratio checks - long_ratio and
    # higher_tf_long/short already encode direction; stacking near-
    # duplicate conditions on top just multiplied the odds of failure.
    # =====================================================
    final = "NO TRADE"

    long_conditions = (
        higher_tf_long
        and lower_long_count >= MIN_LOWER_CONFIRMATIONS
        and long_ratio >= MIN_DIRECTIONAL_RATIO
        and long_ratio > short_ratio
    )

    if long_conditions:
        final = "LONG"

    short_conditions = (
        higher_tf_short
        and lower_short_count >= MIN_LOWER_CONFIRMATIONS
        and short_ratio >= MIN_DIRECTIONAL_RATIO
        and short_ratio > long_ratio
    )

    if final == "NO TRADE" and short_conditions:
        final = "SHORT"

    # =====================================================
    # ENTRY
    # =====================================================
    entry_price = None
    atr = None
    entry_data = results.get("1h", {})

    try:
        if entry_data.get("price") is not None:
            entry_price = float(entry_data["price"])
    except Exception:
        entry_price = None

    try:
        if entry_data.get("atr") is not None:
            atr = float(entry_data["atr"])
    except Exception:
        atr = None

    if entry_price is None:
        for timeframe in ["2h", "3h", "4h", "1d"]:
            data = results.get(timeframe, {})
            try:
                if data.get("price") is not None:
                    entry_price = float(data["price"])
                    if data.get("atr") is not None:
                        atr = float(data["atr"])
                    break
            except Exception:
                continue

    if final in ["LONG", "SHORT"] and entry_price is not None and atr is not None and atr > 0:
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
        risk = {"valid": False, "reason": "سیگنال قابل معامله وجود ندارد"}

    return {
        "signal": final,
        "long_weight": round(long_weight, 3),
        "short_weight": round(short_weight, 3),
        "long_ratio": round(long_ratio, 3),
        "short_ratio": round(short_ratio, 3),
        "long_quality": round(long_quality_ratio, 4),
        "short_quality": round(short_quality_ratio, 4),
        "long_count": long_count,
        "short_count": short_count,
        "lower_long_count": lower_long_count,
        "lower_short_count": lower_short_count,
        "daily_signal": daily_signal,
        "daily_quality": round(daily_quality, 4),
        "four_hour_signal": four_hour_signal,
        "four_hour_quality": round(four_hour_quality, 4),
        "entry_price": entry_price,
        "atr": atr,
        "risk": risk,
        "timeframes": results
    }


if __name__ == "__main__":
    result = final_signal()
    print("\n==========================")
    print("FINAL SIGNAL")
    print("==========================")
    print("Signal:", result["signal"])
    print("LONG WEIGHT:", result["long_weight"])
    print("SHORT WEIGHT:", result["short_weight"])
    print("LONG QUALITY:", result["long_quality"])
    print("SHORT QUALITY:", result["short_quality"])
    print("DAILY:", result["daily_signal"], result["daily_quality"])
    print("4H:", result["four_hour_signal"], result["four_hour_quality"])
    print("LOWER LONG:", result["lower_long_count"])
    print("LOWER SHORT:", result["lower_short_count"])
    print("ENTRY:", result["entry_price"])
    print("ATR:", result["atr"])
    print("RISK:", result["risk"])
