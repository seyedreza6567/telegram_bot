from multi_timeframe import analyze_timeframes
from risk_manager import calculate_risk


# =========================================================
# FINAL SIGNAL
# =========================================================

def final_signal(
    symbol="BTC-SWAP-USDT"
):

    results = analyze_timeframes(
        symbol
    )

    long_weight = 0.0
    short_weight = 0.0

    long_score = 0.0
    short_score = 0.0

    valid_weight = 0.0

    # =====================================================
    # COLLECT RESULTS
    # =====================================================

    for timeframe, result in results.items():

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        score = result.get(
            "score",
            0
        )

        weight = result.get(
            "weight",
            1.0
        )

        try:

            score = float(score)
            weight = float(weight)

        except Exception:

            continue

        if weight <= 0:
            continue

        if signal in [
            "LONG",
            "SHORT"
        ]:

            valid_weight += weight

        if signal == "LONG":

            long_weight += weight

            long_score += (
                score * weight
            )

        elif signal == "SHORT":

            short_weight += weight

            short_score += (
                score * weight
            )

    # =====================================================
    # TOTAL WEIGHT
    # =====================================================

    total_weight = sum(
        result.get(
            "weight",
            1.0
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
    # HIGHER TIMEFRAME TREND
    # =====================================================

    daily_signal = results.get(
        "1d",
        {}
    ).get(
        "signal",
        "NO TRADE"
    )

    four_hour_signal = results.get(
        "4h",
        {}
    ).get(
        "signal",
        "NO TRADE"
    )

    # =====================================================
    # FINAL DECISION
    # =====================================================

    final = "NO TRADE"

    # LONG
    if (
        long_ratio >= 0.60
        and
        long_weight > short_weight
        and
        daily_signal != "SHORT"
        and
        four_hour_signal != "SHORT"
        and
        long_score >= 35
    ):

        final = "LONG"

    # SHORT
    elif (
        short_ratio >= 0.60
        and
        short_weight > long_weight
        and
        daily_signal != "LONG"
        and
        four_hour_signal != "LONG"
        and
        short_score >= 35
    ):

        final = "SHORT"

    # =====================================================
    # ENTRY
    # =====================================================

    entry_price = None
    atr = None

    # برای ورود از تایم‌فریم 1H استفاده می‌کنیم
    # چون معامله در نزدیک‌ترین تایم‌فریم اجرا می‌شود.

    entry_data = results.get(
        "1h",
        {}
    )

    try:

        if entry_data.get("price") is not None:

            entry_price = float(
                entry_data["price"]
            )

    except Exception:

        entry_price = None

    try:

        if entry_data.get("atr") is not None:

            atr = float(
                entry_data["atr"]
            )

    except Exception:

        atr = None

    # اگر 1H موجود نبود، 2H
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

                if data.get("price") is not None:

                    entry_price = float(
                        data["price"]
                    )

                    atr = float(
                        data.get("atr")
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

        "long_score": round(
            long_score,
            3
        ),

        "short_score": round(
            short_score,
            3
        ),

        "entry_price": entry_price,

        "atr": atr,

        "risk": risk,

        "timeframes": results
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
        "LONG SCORE:",
        result["long_score"]
    )

    print(
        "SHORT SCORE:",
        result["short_score"]
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
