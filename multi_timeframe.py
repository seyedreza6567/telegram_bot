from scanner import get_klines
from analysis_engine import analyze


# =========================================================
# TIMEFRAMES
# =========================================================

TIMEFRAME_WEIGHTS = {
    "1h": 1.0,
    "2h": 1.25,
    "3h": 1.50,
    "4h": 2.0,
    "1d": 3.0
}


# =========================================================
# SETTINGS
# =========================================================

CANDLE_LIMIT = 300

MIN_CANDLES = 250


# =========================================================
# MULTI TIMEFRAME
# =========================================================

def analyze_timeframes(
    symbol="BTC-SWAP-USDT"
):

    results = {}

    for timeframe, weight in TIMEFRAME_WEIGHTS.items():

        print(
            f"\nدر حال بررسی {timeframe} ..."
        )

        try:

            df = get_klines(
                symbol=symbol,
                interval=timeframe,
                limit=CANDLE_LIMIT
            )

        except Exception as e:

            results[timeframe] = {
                "signal": "NO TRADE",
                "score": 0,
                "weight": weight,
                "reason": f"خطای دریافت داده: {e}"
            }

            continue

        if (
            df is None
            or
            len(df) < MIN_CANDLES
        ):

            results[timeframe] = {
                "signal": "NO TRADE",
                "score": 0,
                "weight": weight,
                "reason": "داده کافی نیست"
            }

            continue

        try:

            result = analyze(df)

        except Exception as e:

            result = {
                "signal": "NO TRADE",
                "score": 0,
                "weight": weight,
                "reason": f"خطای تحلیل: {e}"
            }

        result["weight"] = weight
        result["timeframe"] = timeframe

        results[timeframe] = result

    return results


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    results = analyze_timeframes()

    print(
        "\n=============================="
    )

    print(
        "MULTI TIMEFRAME ANALYSIS"
    )

    print(
        "=============================="
    )

    for timeframe, result in results.items():

        print(
            f"\n⏱ {timeframe}"
        )

        print(
            "Signal:",
            result.get("signal")
        )

        print(
            "Score:",
            result.get("score")
        )

        print(
            "Weight:",
            result.get("weight")
        )

        print(
            "RSI:",
            result.get("rsi")
        )

        print(
            "Price:",
            result.get("price")
        )

        print(
            "Reason:",
            result.get("reason")
        )
