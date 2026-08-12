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
    print("🔬 SIGNAL DIAGNOSTIC TEST")
    print("=" * 70)

    df = get_klines(
        symbol=SYMBOL,
        interval=TIMEFRAME,
        limit=CANDLE_LIMIT
    )

    if df is None:
        print("❌ DATA ERROR")
        return

    print(f"📊 Candles: {len(df)}")
    print(f"💰 Symbol: {SYMBOL}")
    print(f"⏱️ Timeframe: {TIMEFRAME}")

    long_count = 0
    short_count = 0
    no_trade_count = 0

    scores = []

    print("\n" + "=" * 70)
    print("📋 LAST SIGNALS")
    print("=" * 70)

    for i in range(
        MIN_ANALYSIS_CANDLES,
        len(df)
    ):

        historical_df = df.iloc[:i].copy()

        try:

            result = analyze(
                historical_df
            )

        except Exception as e:

            print("❌ ANALYSIS ERROR:", e)
            return

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        score = result.get(
            "score",
            0
        )

        price = result.get(
            "price",
            0
        )

        rsi = result.get(
            "rsi",
            0
        )

        scores.append(
            safe_float(score) or 0
        )

        if signal == "LONG":

            long_count += 1

        elif signal == "SHORT":

            short_count += 1

        else:

            no_trade_count += 1

        if signal in [
            "LONG",
            "SHORT"
        ]:

            next_open = safe_float(
                df.iloc[i]["open"]
            )

            print(
                f"{i} | "
                f"{signal:<5} | "
                f"Score={score} | "
                f"RSI={rsi} | "
                f"SignalPrice={price} | "
                f"NextOpen={next_open}"
            )

    print("\n" + "=" * 70)
    print("📊 RESULT")
    print("=" * 70)

    print(
        f"🟢 LONG signals : {long_count}"
    )

    print(
        f"🔴 SHORT signals: {short_count}"
    )

    print(
        f"⚪ NO TRADE     : {no_trade_count}"
    )

    if scores:

        print(
            f"📈 Max Score    : {max(scores):.2f}"
        )

        print(
            f"📉 Min Score    : {min(scores):.2f}"
        )

        print(
            f"📊 Avg Score    : "
            f"{np.mean(scores):.2f}"
        )

    print("\n" + "=" * 70)
    print("✅ TEST FINISHED")
    print("=" * 70)


if __name__ == "__main__":

    main()
