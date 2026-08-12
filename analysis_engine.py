import pandas as pd
import numpy as np


# =========================================================
# EMA
# =========================================================

def ema(series, period):

    return series.ewm(
        span=period,
        adjust=False
    ).mean()


# =========================================================
# RSI
# =========================================================

def rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    rs = (
        avg_gain /
        avg_loss.replace(0, np.nan)
    )

    return 100 - (
        100 / (1 + rs)
    )


# =========================================================
# ATR
# =========================================================

def atr(df, period=14):

    prev_close = df["close"].shift(1)

    tr1 = df["high"] - df["low"]

    tr2 = (
        df["high"] -
        prev_close
    ).abs()

    tr3 = (
        df["low"] -
        prev_close
    ).abs()

    tr = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    return tr.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()


# =========================================================
# MACD
# =========================================================

def macd(series):

    fast = ema(
        series,
        12
    )

    slow = ema(
        series,
        26
    )

    line = fast - slow

    signal = ema(
        line,
        9
    )

    hist = line - signal

    return line, signal, hist


# =========================================================
# ANALYZE
# =========================================================

def analyze(df):

    if df is None:
        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "reason": "No data"
        }

    if len(df) < 250:

        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "reason": "Not enough data"
        }

    df = df.copy()

    close = df["close"]

    # =====================================================
    # Indicators
    # =====================================================

    df["ema20"] = ema(
        close,
        20
    )

    df["ema50"] = ema(
        close,
        50
    )

    df["ema200"] = ema(
        close,
        200
    )

    df["rsi"] = rsi(
        close,
        14
    )

    df["atr"] = atr(
        df,
        14
    )

    (
        df["macd"],
        df["macd_signal"],
        df["macd_hist"]
    ) = macd(
        close
    )

    # =====================================================
    # Last candles
    # =====================================================

    last = df.iloc[-1]
    prev = df.iloc[-2]
    prev5 = df.iloc[-6]

    price = float(
        last["close"]
    )

    current_atr = float(
        last["atr"]
    )

    current_rsi = float(
        last["rsi"]
    )

    if not np.isfinite(
        current_atr
    ) or current_atr <= 0:

        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "reason": "ATR invalid"
        }

    if not np.isfinite(
        current_rsi
    ):

        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "reason": "RSI invalid"
        }

    # =====================================================
    # Trend
    # =====================================================

    ema20 = float(
        last["ema20"]
    )

    ema50 = float(
        last["ema50"]
    )

    ema200 = float(
        last["ema200"]
    )

    ema20_prev = float(
        prev["ema20"]
    )

    ema50_prev = float(
        prev["ema50"]
    )

    # =====================================================
    # Momentum
    # =====================================================

    momentum = (
        price -
        float(prev5["close"])
    ) / float(prev5["close"])

    # =====================================================
    # MACD
    # =====================================================

    macd_value = float(
        last["macd"]
    )

    macd_signal = float(
        last["macd_signal"]
    )

    macd_hist = float(
        last["macd_hist"]
    )

    prev_hist = float(
        prev["macd_hist"]
    )

    # =====================================================
    # Scores
    # =====================================================

    long_score = 0
    short_score = 0

    long_reasons = []
    short_reasons = []

    # =====================================================
    # LONG CONDITIONS
    # =====================================================

    if price > ema200:

        long_score += 2

        long_reasons.append(
            "Price above EMA200"
        )

    if ema20 > ema50:

        long_score += 2

        long_reasons.append(
            "EMA20 above EMA50"
        )

    if ema50 > ema200:

        long_score += 2

        long_reasons.append(
            "EMA50 above EMA200"
        )

    if ema20 > ema20_prev:

        long_score += 1

        long_reasons.append(
            "EMA20 rising"
        )

    if ema50 > ema50_prev:

        long_score += 1

        long_reasons.append(
            "EMA50 rising"
        )

    if 50 <= current_rsi <= 67:

        long_score += 2

        long_reasons.append(
            "RSI bullish"
        )

    if (
        macd_value >
        macd_signal
        and
        macd_hist > 0
    ):

        long_score += 2

        long_reasons.append(
            "MACD bullish"
        )

    if (
        macd_hist >
        prev_hist
    ):

        long_score += 1

        long_reasons.append(
            "MACD momentum rising"
        )

    if momentum > 0:

        long_score += 1

        long_reasons.append(
            "Price momentum positive"
        )

    # =====================================================
    # SHORT CONDITIONS
    # =====================================================

    if price < ema200:

        short_score += 2

        short_reasons.append(
            "Price below EMA200"
        )

    if ema20 < ema50:

        short_score += 2

        short_reasons.append(
            "EMA20 below EMA50"
        )

    if ema50 < ema200:

        short_score += 2

        short_reasons.append(
            "EMA50 below EMA200"
        )

    if ema20 < ema20_prev:

        short_score += 1

        short_reasons.append(
            "EMA20 falling"
        )

    if ema50 < ema50_prev:

        short_score += 1

        short_reasons.append(
            "EMA50 falling"
        )

    if 33 <= current_rsi <= 50:

        short_score += 2

        short_reasons.append(
            "RSI bearish"
        )

    if (
        macd_value <
        macd_signal
        and
        macd_hist < 0
    ):

        short_score += 2

        short_reasons.append(
            "MACD bearish"
        )

    if (
        macd_hist <
        prev_hist
    ):

        short_score += 1

        short_reasons.append(
            "MACD momentum falling"
        )

    if momentum < 0:

        short_score += 1

        short_reasons.append(
            "Price momentum negative"
        )

    # =====================================================
    # Direction
    # =====================================================

    difference = abs(
        long_score -
        short_score
    )

    best_score = max(
        long_score,
        short_score
    )

    # =====================================================
    # Minimum quality
    # =====================================================

    if best_score < 8:

        return {
            "signal": "NO TRADE",
            "score": best_score,
            "confidence": best_score * 8,
            "long_score": long_score,
            "short_score": short_score,
            "rsi": round(
                current_rsi,
                2
            ),
            "price": price,
            "atr": current_atr,
            "reason": "Weak signal"
        }

    if difference < 3:

        return {
            "signal": "NO TRADE",
            "score": best_score,
            "confidence": best_score * 8,
            "long_score": long_score,
            "short_score": short_score,
            "rsi": round(
                current_rsi,
                2
            ),
            "price": price,
            "atr": current_atr,
            "reason": "Direction unclear"
        }

    # =====================================================
    # LONG
    # =====================================================

    if long_score > short_score:

        stop_loss = (
            price -
            current_atr * 2
        )

        tp1 = (
            price +
            current_atr * 2
        )

        tp2 = (
            price +
            current_atr * 4
        )

        return {
            "signal": "LONG",
            "score": long_score,
            "confidence": min(
                100,
                long_score * 8
            ),
            "long_score": long_score,
            "short_score": short_score,
            "rsi": round(
                current_rsi,
                2
            ),
            "price": price,
            "atr": current_atr,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "take_profit": tp2,
            "reason": " | ".join(
                long_reasons
            )
        }

    # =====================================================
    # SHORT
    # =====================================================

    if short_score > long_score:

        stop_loss = (
            price +
            current_atr * 2
        )

        tp1 = (
            price -
            current_atr * 2
        )

        tp2 = (
            price -
            current_atr * 4
        )

        return {
            "signal": "SHORT",
            "score": short_score,
            "confidence": min(
                100,
                short_score * 8
            ),
            "long_score": long_score,
            "short_score": short_score,
            "rsi": round(
                current_rsi,
                2
            ),
            "price": price,
            "atr": current_atr,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "take_profit": tp2,
            "reason": " | ".join(
                short_reasons
            )
        }

    # =====================================================
    # NO TRADE
    # =====================================================

    return {
        "signal": "NO TRADE",
        "score": best_score,
        "confidence": 0,
        "long_score": long_score,
        "short_score": short_score,
        "price": price,
        "atr": current_atr,
        "reason": "No clear direction"
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print(
        "Analysis Engine v4 OK"
    )
