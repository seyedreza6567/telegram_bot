from scanner import get_klines
from analysis_engine import analyze


TIMEFRAMES = ["1h", "2h", "3h", "4h", "1d"]


def analyze_timeframes(symbol="BTC-SWAP-USDT"):

    results = {}

    for timeframe in TIMEFRAMES:

        print(f"\nدر حال بررسی {timeframe} ...")

        df = get_klines(
            symbol=symbol,
            interval=timeframe,
            limit=250
        )

        if df is None or len(df) < 100:
            results[timeframe] = {
                "signal": "NO TRADE",
                "reason": "داده کافی نیست"
            }
            continue

        results[timeframe] = analyze(df)

    return results


if __name__ == "__main__":

    results = analyze_timeframes()

    print("\n==============================")
    print("MULTI TIMEFRAME ANALYSIS")
    print("==============================")

    for timeframe, result in results.items():

        print(f"\n⏱ {timeframe}")
        print(f"Signal: {result.get('signal')}")
        print(f"Score: {result.get('score')}")
        print(f"RSI: {result.get('rsi')}")
        print(f"Price: {result.get('price')}")
        print(f"Reason: {result.get('reason')}")
