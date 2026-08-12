import pandas as pd
import numpy as np

from scanner import get_klines


SYMBOL = "BTC-SWAP-USDT"
TIMEFRAME = "1h"
LIMIT = 1000

LOOKAHEAD = 10
MIN_CANDLES = 250


def main():

    print("\n" + "=" * 60)
    print("MARKET DIRECTION TEST")
    print("=" * 60)

    df = get_klines(
        symbol=SYMBOL,
        interval=TIMEFRAME,
        limit=LIMIT
    )

    if df is None:

        print("DATA ERROR")
        return

    if len(df) < MIN_CANDLES + LOOKAHEAD:

        print("NOT ENOUGH DATA")
        return

    df = df.copy()

    up = 0
    down = 0
    flat = 0

    moves = []

    for i in range(
        MIN_CANDLES,
        len(df) - LOOKAHEAD
    ):

        entry = float(
            df.iloc[i]["open"]
        )

        future = float(
            df.iloc[
                i + LOOKAHEAD
            ]["close"]
        )

        if entry <= 0:

            continue

        change_percent = (
            (future - entry)
            /
            entry
        ) * 100

        moves.append(
            change_percent
        )

        if change_percent > 0.20:

            up += 1

        elif change_percent < -0.20:

            down += 1

        else:

            flat += 1

    total = (
        up +
        down +
        flat
    )

    print("\nTOTAL:", total)

    print(
        "UP:",
        up
    )

    print(
        "DOWN:",
        down
    )

    print(
        "FLAT:",
        flat
    )

    if total > 0:

        print(
            "UP %:",
            round(
                up / total * 100,
                2
            )
        )

        print(
            "DOWN %:",
            round(
                down / total * 100,
                2
            )
        )

        print(
            "FLAT %:",
            round(
                flat / total * 100,
                2
            )
        )

    if moves:

        print(
            "\nAVERAGE MOVE:",
            round(
                np.mean(moves),
                4
            ),
            "%"
        )

        print(
            "MAX UP:",
            round(
                max(moves),
                4
            ),
            "%"
        )

        print(
            "MAX DOWN:",
            round(
                min(moves),
                4
            ),
            "%"
        )

    print("\n" + "=" * 60)


if __name__ == "__main__":

    main()
