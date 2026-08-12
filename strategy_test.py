import pandas as pd
import numpy as np

from scanner import get_klines
from analysis_engine import analyze


SYMBOL = "BTC-SWAP-USDT"
TIMEFRAME = "1h"
LIMIT = 1000
MIN_CANDLES = 250


def main():

    print("\n" + "=" * 60)
    print("STRATEGY DIAGNOSTIC TEST")
    print("=" * 60)

    df = get_klines(
        symbol=SYMBOL,
        interval=TIMEFRAME,
        limit=LIMIT
    )

    if df is None or len(df) < MIN_CANDLES + 20:

        print("DATA ERROR")
        return

    df = df.copy()

    long_count = 0
    short_count = 0
    no_trade_count = 0

    long_correct = 0
    short_correct = 0

    long_wrong = 0
    short_wrong = 0

    results = []

    for i in range(
        MIN_CANDLES,
        len(df) - 20
    ):

        historical = df.iloc[:i].copy()

        try:

            result = analyze(
                historical
            )

        except Exception:

            continue

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        entry = float(
            df.iloc[i]["open"]
        )

        future_close = float(
            df.iloc[i + 10]["close"]
        )

        if signal == "LONG":

            long_count += 1

            if future_close > entry:

                long_correct += 1

            else:

                long_wrong += 1

            results.append({
                "signal": "LONG",
                "entry": entry,
                "future": future_close
            })

        elif signal == "SHORT":

            short_count += 1

            if future_close < entry:

                short_correct += 1

            else:

                short_wrong += 1

            results.append({
                "signal": "SHORT",
                "entry": entry,
                "future": future_close
            })

        else:

            no_trade_count += 1

    print("\n")
    print("TOTAL SIGNALS:", long_count + short_count)
    print("LONG:", long_count)
    print("SHORT:", short_count)
    print("NO TRADE:", no_trade_count)

    print("\n" + "-" * 60)

    if long_count > 0:

        long_accuracy = (
            long_correct /
            long_count
        ) * 100

    else:

        long_accuracy = 0

    if short_count > 0:

        short_accuracy = (
            short_correct /
            short_count
        ) * 100

    else:

        short_accuracy = 0

    print(
        "LONG CORRECT:",
        long_correct
    )

    print(
        "LONG WRONG:",
        long_wrong
    )

    print(
        "LONG ACCURACY:",
        round(long_accuracy, 2),
        "%"
    )

    print("\n")

    print(
        "SHORT CORRECT:",
        short_correct
    )

    print(
        "SHORT WRONG:",
        short_wrong
    )

    print(
        "SHORT ACCURACY:",
        round(short_accuracy, 2),
        "%"
    )

    print("\n" + "=" * 60)

    if (
        long_accuracy > 50
        and
        short_accuracy > 50
    ):

        print(
            "SIGNAL ENGINE LOOKS OK"
        )

    elif (
        long_accuracy < 50
        and
        short_accuracy < 50
    ):

        print(
            "SIGNAL DIRECTION IS PROBABLY WRONG"
        )

    else:

        print(
            "ONE DIRECTION IS STRONGER"
        )

    print("=" * 60)


if __name__ == "__main__":

    main()
