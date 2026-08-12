from multi_timeframe import analyze_timeframes
from risk_manager import calculate_risk


def final_signal(symbol="BTC-SWAP-USDT"):

    results = analyze_timeframes(
        symbol
    )

    long_count = 0
    short_count = 0

    long_score = 0
    short_score = 0

    for timeframe, result in results.items():

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        score = result.get(
            "score",
            0
        )

        if signal == "LONG":

            long_count += 1
            long_score += score

        elif signal == "SHORT":

            short_count += 1
            short_score += score

    # =====================================================
    # تصمیم نهایی
    # =====================================================

    if (
        long_count >= 4
        and
        short_count == 0
        and
        long_score >= 24
    ):

        final = "LONG"

    elif (
        short_count >= 4
        and
        long_count == 0
        and
        short_score >= 24
    ):

        final = "SHORT"

    else:

        final = "NO TRADE"

    # =====================================================
    # قیمت ورود
    # =====================================================

    entry_price = None

    for timeframe in [
        "1h",
        "2h",
        "3h",
        "4h",
        "1d"
    ]:

        data = results.get(
            timeframe,
            {}
        )

        price = data.get(
            "price"
        )

        if price is not None:

            try:

                entry_price = float(
                    price
                )

                break

            except Exception:

                continue

    # =====================================================
    # مدیریت ریسک
    # =====================================================

    if final in [
        "LONG",
        "SHORT"
    ] and entry_price is not None:

        risk = calculate_risk(
            entry_price=entry_price,
            signal=final,
            risk_percent=1.0,
            stop_loss_percent=2.0,
            take_profit_percent=4.0
        )

    else:

        risk = {
            "valid": False,
            "reason": "سیگنال قابل معامله وجود ندارد"
        }

    return {
        "signal": final,
        "long_count": long_count,
        "short_count": short_count,
        "long_score": long_score,
        "short_score": short_score,
        "entry_price": entry_price,
        "risk": risk,
        "timeframes": results
    }


if __name__ == "__main__":

    result = final_signal()

    print("\n==========================")
    print("FINAL SIGNAL")
    print("==========================")

    print(
        "Signal:",
        result["signal"]
    )

    print(
        "LONG:",
        result["long_count"]
    )

    print(
        "SHORT:",
        result["short_count"]
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
        "RISK:",
        result["risk"]
    )
