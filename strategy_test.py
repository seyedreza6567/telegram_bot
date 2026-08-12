import pandas as pd
import numpy as np

from scanner import get_klines
from analysis_engine import analyze


# =========================================================
# SETTINGS
# =========================================================

SYMBOL = "BTC-SWAP-USDT"
TIMEFRAME = "1h"
LIMIT = 1000

MIN_CANDLES = 250

HORIZONS = [5, 10, 20]

MIN_MOVE = 0.20


# =========================================================
# SAFE FLOAT
# =========================================================

def safe_float(value):

    try:

        value = float(value)

        if np.isfinite(value):
            return value

    except Exception:
        pass

    return None


# =========================================================
# TEST
# =========================================================

def main():

    print("\n" + "=" * 70)
    print("SIGNAL DIRECTION TEST")
    print("=" * 70)

    df = get_klines(
        symbol=SYMBOL,
        interval=TIMEFRAME,
        limit=LIMIT
    )

    if df is None:

        print("DATA ERROR")
        return

    if len(df) < MIN_CANDLES + 20:

        print("NOT ENOUGH DATA")
        return

    df = df.copy()

    results = {}

    for horizon in HORIZONS:

        results[horizon] = {
            "all": [],
            "long": [],
            "short": []
        }

    total_long = 0
    total_short = 0
    total_no_trade = 0

    # =====================================================
    # WALK FORWARD
    # =====================================================

    for i in range(
        MIN_CANDLES,
        len(df) - max(HORIZONS)
    ):

        historical = df.iloc[
            :i
        ].copy()

        try:

            analysis = analyze(
                historical
            )

        except Exception:

            continue

        signal = analysis.get(
            "signal",
            "NO TRADE"
        )

        if signal == "LONG":

            total_long += 1

        elif signal == "SHORT":

            total_short += 1

        else:

            total_no_trade += 1

            continue

        entry = safe_float(
            df.iloc[i]["open"]
        )

        if entry is None or entry <= 0:
            continue

        # =================================================
        # FUTURE MOVEMENTS
        # =================================================

        for horizon in HORIZONS:

            future_close = safe_float(
                df.iloc[
                    i + horizon
                ]["close"]
            )

            if future_close is None:
                continue

            move = (
                (
                    future_close -
                    entry
                )
                /
                entry
            ) * 100

            results[horizon][
                "all"
            ].append(move)

            if signal == "LONG":

                results[horizon][
                    "long"
                ].append(move)

            elif signal == "SHORT":

                results[horizon][
                    "short"
                ].append(move)

    # =====================================================
    # BASIC RESULT
    # =====================================================

    total_signals = (
        total_long +
        total_short
    )

    print(
        f"\nTOTAL SIGNALS: {total_signals}"
    )

    print(
        f"LONG: {total_long}"
    )

    print(
        f"SHORT: {total_short}"
    )

    print(
        f"NO TRADE: {total_no_trade}"
    )

    # =====================================================
    # HORIZON REPORT
    # =====================================================

    for horizon in HORIZONS:

        all_moves = results[horizon]["all"]

        long_moves = results[horizon]["long"]

        short_moves = results[horizon]["short"]

        print(
            "\n" + "-" * 70
        )

        print(
            f"HORIZON: {horizon} CANDLES"
        )

        print(
            "-" * 70
        )

        # -------------------------------------------------
        # ALL
        # -------------------------------------------------

        if all_moves:

            average = np.mean(
                all_moves
            )

            positive = (
                np.sum(
                    np.array(all_moves) > 0
                )
                /
                len(all_moves)
            ) * 100

            print(
                f"Average: {average:.4f}%"
            )

            print(
                f"Positive: {positive:.2f}%"
            )

        # -------------------------------------------------
        # LONG
        # -------------------------------------------------

        if long_moves:

            long_avg = np.mean(
                long_moves
            )

            long_positive = (
                np.sum(
                    np.array(long_moves) > 0
                )
                /
                len(long_moves)
            ) * 100

            print(
                f"LONG Average: "
                f"{long_avg:.4f}%"
            )

            print(
                f"LONG Positive: "
                f"{long_positive:.2f}%"
            )

        # -------------------------------------------------
        # SHORT
        #
        # برای SHORT حرکت مثبت بازار
        # به ضرر SHORT است.
        #
        # بنابراین معیار درست:
        # -move
        # -------------------------------------------------

        if short_moves:

            short_avg_market = np.mean(
                short_moves
            )

            short_avg = -short_avg_market

            short_positive = (
                np.sum(
                    np.array(short_moves) < 0
                )
                /
                len(short_moves)
            ) * 100

            print(
                f"SHORT Average: "
                f"{short_avg:.4f}%"
            )

            print(
                f"SHORT Positive: "
                f"{short_positive:.2f}%"
            )

    # =====================================================
    # FINAL
    # =====================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "TEST FINISHED"
    )

    print(
        "=" * 70
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
