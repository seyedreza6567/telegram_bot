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

    except Exception:
        pass

    return None


def main():

    print("\n" + "=" * 70)
    print("🔎 BTC BACKTEST DEBUG")
    print("=" * 70)

    df = get_klines(
        symbol=SYMBOL,
        interval=TIMEFRAME,
        limit=CANDLE_LIMIT
    )

    if df is None:

        print("DATA ERROR")
        return

    print("CANDLES:", len(df))
    print("SYMBOL:", SYMBOL)
    print("TIMEFRAME:", TIMEFRAME)

    found = 0

    for i in range(
        MIN_ANALYSIS_CANDLES,
        len(df) - 20
    ):

        historical = df.iloc[:i].copy()

        try:

            analysis = analyze(
                historical
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

        found += 1

        entry_open = safe_float(
            df.iloc[i]["open"]
        )

        entry_close = safe_float(
            df.iloc[i]["close"]
        )

        entry_high = safe_float(
            df.iloc[i]["high"]
        )

        entry_low = safe_float(
            df.iloc[i]["low"]
        )

        analysis_price = safe_float(
            analysis.get("price")
        )

        atr = safe_float(
            analysis.get("atr")
        )

        print("\n" + "-" * 70)

        print(
            "SIGNAL NUMBER:",
            found
        )

        print(
            "CANDLE INDEX:",
            i
        )

        print(
            "SIGNAL:",
            signal
        )

        print(
            "ANALYSIS PRICE:",
            analysis_price
        )

        print(
            "ATR:",
            atr
        )

        print(
            "LONG SCORE:",
            analysis.get("long_score")
        )

        print(
            "SHORT SCORE:",
            analysis.get("short_score")
        )

        print(
            "NEXT CANDLE OPEN:",
            entry_open
        )

        print(
            "NEXT CANDLE HIGH:",
            entry_high
        )

        print(
            "NEXT CANDLE LOW:",
            entry_low
        )

        print(
            "NEXT CANDLE CLOSE:",
            entry_close
        )

        if atr is not None and entry_open is not None:

            if signal == "LONG":

                sl = entry_open - (
                    atr * 2
                )

                tp1 = entry_open + (
                    atr * 2
                )

                tp2 = entry_open + (
                    atr * 4
                )

            else:

                sl = entry_open + (
                    atr * 2
                )

                tp1 = entry_open - (
                    atr * 2
                )

                tp2 = entry_open - (
                    atr * 4
                )

            print(
                "CALCULATED SL:",
                sl
            )

            print(
                "CALCULATED TP1:",
                tp1
            )

            print(
                "CALCULATED TP2:",
                tp2
            )

        print("-" * 70)

        # فقط 5 سیگنال اول
        if found >= 5:
            break

    print("\n" + "=" * 70)

    print(
        "TOTAL DEBUG SIGNALS:",
        found
    )

    print("=" * 70)


if __name__ == "__main__":

    main()
