import pandas as pd
import numpy as np

from scanner import get_klines
from analysis_engine import analyze


SYMBOL = "BTC-SWAP-USDT"
TIMEFRAME = "1h"
CANDLE_LIMIT = 1000
MIN_ANALYSIS_CANDLES = 250


def safe_float(value):

    try:
        value = float(value)

        if np.isfinite(value):
            return value

    except:
        pass

    return None


def main():

    print("\n" + "=" * 70)
    print("🔬 PURE SIGNAL TEST")
    print("=" * 70)

    df = get_klines(
        symbol=SYMBOL,
        interval=TIMEFRAME,
        limit=CANDLE_LIMIT
    )

    if df is None:
        print("DATA ERROR")
        return

    print("Candles:", len(df))
    print("Symbol:", SYMBOL)
    print("Timeframe:", TIMEFRAME)

    results = []

    for i in range(
        MIN_ANALYSIS_CANDLES,
        len(df) - 20
    ):

        historical_df = df.iloc[:i].copy()

        try:

            analysis = analyze(
                historical_df
            )

        except Exception as e:

            print("ANALYSIS ERROR:", e)
            return

        signal = analysis.get(
            "signal",
            "NO TRADE"
        )

        if signal not in [
            "LONG",
            "SHORT"
        ]:

            continue

        entry = safe_float(
            df.iloc[i]["open"]
        )

        if entry is None:
            continue

        future_5 = safe_float(
            df.iloc[i + 5]["close"]
        )

        future_10 = safe_float(
            df.iloc[i + 10]["close"]
        )

        future_20 = safe_float(
            df.iloc[i + 20]["close"]
        )

        if (
            future_5 is None
            or future_10 is None
            or future_20 is None
        ):
            continue

        if signal == "LONG":

            r5 = (
                (future_5 - entry)
                / entry
            ) * 100

            r10 = (
                (future_10 - entry)
                / entry
            ) * 100

            r20 = (
                (future_20 - entry)
                / entry
            ) * 100

        else:

            r5 = (
                (entry - future_5)
                / entry
            ) * 100

            r10 = (
                (entry - future_10)
                / entry
            ) * 100

            r20 = (
                (entry - future_20)
                / entry
            ) * 100

        results.append({
            "signal": signal,
            "r5": r5,
            "r10": r10,
            "r20": r20
        })

    if not results:

        print("\nNO SIGNALS")
        return

    data = pd.DataFrame(results)

    long_data = data[
        data["signal"] == "LONG"
    ]

    short_data = data[
        data["signal"] == "SHORT"
    ]

    print("\n" + "=" * 70)
    print("📊 RESULT")
    print("=" * 70)

    print(
        "Total Signals:",
        len(data)
    )

    print(
        "LONG:",
        len(long_data)
    )

    print(
        "SHORT:",
        len(short_data)
    )

    print("\n--- 5 CANDLES ---")

    print(
        "Average:",
        round(data["r5"].mean(), 3),
        "%"
    )

    print(
        "Positive:",
        round(
            (data["r5"] > 0).mean() * 100,
            2
        ),
        "%"
    )

    print("\n--- 10 CANDLES ---")

    print(
        "Average:",
        round(data["r10"].mean(), 3),
        "%"
    )

    print(
        "Positive:",
        round(
            (data["r10"] > 0).mean() * 100,
            2
        ),
        "%"
    )

    print("\n--- 20 CANDLES ---")

    print(
        "Average:",
        round(data["r20"].mean(), 3),
        "%"
    )

    print(
        "Positive:",
        round(
            (data["r20"] > 0).mean() * 100,
            2
        ),
        "%"
    )

    if len(long_data) > 0:

        print("\n🟢 LONG")

        print(
            "5:",
            round(long_data["r5"].mean(), 3),
            "%"
        )

        print(
            "10:",
            round(long_data["r10"].mean(), 3),
            "%"
        )

        print(
            "20:",
            round(long_data["r20"].mean(), 3),
            "%"
        )

    if len(short_data) > 0:

        print("\n🔴 SHORT")

        print(
            "5:",
            round(short_data["r5"].mean(), 3),
            "%"
        )

        print(
            "10:",
            round(short_data["r10"].mean(), 3),
            "%"
        )

        print(
            "20:",
            round(short_data["r20"].mean(), 3),
            "%"
        )

    print("\n" + "=" * 70)
    print("✅ TEST FINISHED")
    print("=" * 70)


if __name__ == "__main__":

    main()
