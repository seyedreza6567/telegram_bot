from multi_timeframe import analyze_timeframes


def final_signal(symbol="BTC-SWAP-USDT"):

    results = analyze_timeframes(symbol)

    long_count = 0
    short_count = 0

    long_score = 0
    short_score = 0

    for timeframe, result in results.items():

        signal = result.get("signal")
        score = result.get("score", 0)

        if signal == "LONG":
            long_count += 1
            long_score += score

        elif signal == "SHORT":
            short_count += 1
            short_score += score

    # --------------------------------
    # تصمیم محافظتی
    # --------------------------------

    if (
        long_count >= 4
        and short_count == 0
        and long_score >= 24
    ):

        final = "LONG"

    elif (
        short_count >= 4
        and long_count == 0
        and short_score >= 24
    ):

        final = "SHORT"

    else:

        final = "NO TRADE"

    return {
        "signal": final,
        "long_count": long_count,
        "short_count": short_count,
        "long_score": long_score,
        "short_score": short_score,
        "timeframes": results
    }


if __name__ == "__main__":

    result = final_signal()

    print("\n==========================")
    print("FINAL SIGNAL")
    print("==========================")

    print("Signal:", result["signal"])
    print("LONG:", result["long_count"])
    print("SHORT:", result["short_count"])

    print("LONG SCORE:", result["long_score"])
    print("SHORT SCORE:", result["short_score"])
