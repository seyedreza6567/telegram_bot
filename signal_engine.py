from multi_timeframe import analyze_timeframes


def final_signal(symbol="BTC-SWAP-USDT"):

    results = analyze_timeframes(symbol)

    long_count = 0
    short_count = 0

    for timeframe, result in results.items():

        signal = result.get("signal")

        if signal == "LONG":
            long_count += 1

        elif signal == "SHORT":
            short_count += 1

    # ورود فقط با تأیید حداقل 4 تایم‌فریم
    if long_count >= 4 and short_count == 0:
        final = "LONG"

    elif short_count >= 4 and long_count == 0:
        final = "SHORT"

    else:
        final = "NO TRADE"

    return {
        "signal": final,
        "long_count": long_count,
        "short_count": short_count,
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
