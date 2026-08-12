from scanner import get_klines
from analysis_engine import analyze


# =========================================================
# TIMEFRAME WEIGHTS
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

MAX_SCORE = 15.0


# =========================================================
# EMPTY RESULT
# =========================================================

def _empty_result(
    timeframe,
    weight,
    reason
):

    return {
        "signal": "NO TRADE",
        "score": 0,
        "confidence": 0,

        "long_score": 0,
        "short_score": 0,

        "score_ratio": 0.0,
        "quality": 0.0,

        "weight": weight,
        "timeframe": timeframe,

        "price": None,
        "atr": None,
        "rsi": None,

        "reason": reason
    }


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

        # -------------------------------------------------
        # FETCH DATA
        # -------------------------------------------------

        try:

            df = get_klines(
                symbol=symbol,
                interval=timeframe,
                limit=CANDLE_LIMIT
            )

        except Exception as e:

            results[timeframe] = _empty_result(
                timeframe,
                weight,
                f"خطای دریافت داده: {e}"
            )

            continue

        # -------------------------------------------------
        # VALIDATE DATA
        # -------------------------------------------------

        if (
            df is None
            or
            len(df) < MIN_CANDLES
        ):

            results[timeframe] = _empty_result(
                timeframe,
                weight,
                "داده کافی نیست"
            )

            continue

        # -------------------------------------------------
        # ANALYZE
        # -------------------------------------------------

        try:

            result = analyze(df)

        except Exception as e:

            results[timeframe] = _empty_result(
                timeframe,
                weight,
                f"خطای تحلیل: {e}"
            )

            continue

        if not isinstance(
            result,
            dict
        ):

            results[timeframe] = _empty_result(
                timeframe,
                weight,
                "خروجی تحلیل نامعتبر است"
            )

            continue

        # -------------------------------------------------
        # STANDARDIZE
        # -------------------------------------------------

        result = result.copy()

        result["weight"] = float(
            weight
        )

        result["timeframe"] = timeframe

        try:

            score = float(
                result.get(
                    "score",
                    0
                )
            )

        except Exception:

            score = 0.0

        score = max(
            0.0,
            min(
                score,
                MAX_SCORE
            )
        )

        result["score"] = score

        # -------------------------------------------------
        # QUALITY
        # -------------------------------------------------

        quality = (
            score /
            MAX_SCORE
        )

        if result.get(
            "signal"
        ) not in [
            "LONG",
            "SHORT"
        ]:

            quality = 0.0

        result["score_ratio"] = round(
            quality,
            4
        )

        result["quality"] = round(
            quality,
            4
        )

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
            "Quality:",
            result.get("quality")
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
