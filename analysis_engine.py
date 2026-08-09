import pandas as pd
import numpy as np


TIMEFRAMES = ["1h", "2h", "3h", "4h", "1d"]


def calculate_ema(df, period):
    return df["close"].ewm(span=period, adjust=False).mean()


def calculate_rsi(df, period=14):
    delta = df["close"].diff()

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

    rs = avg_gain / avg_loss.replace(0, np.nan)

    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(df):
    ema12 = df["close"].ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = df["close"].ewm(
        span=26,
        adjust=False
    ).mean()

    macd = ema12 - ema26

    signal = macd.ewm(
        span=9,
        adjust=False
    ).mean()

    histogram = macd - signal

    return macd, signal, histogram


def analyze(df):

    if df is None or len(df) < 100:
        return {
            "signal": "NO TRADE",
            "score": 0,
            "reason": "داده کافی نیست"
        }

    df = df.copy()

    df["EMA20"] = calculate_ema(df, 20)
    df["EMA50"] = calculate_ema(df, 50)
    df["EMA200"] = calculate_ema(df, 200)

    df["RSI"] = calculate_rsi(df)

    macd, signal, histogram = calculate_macd(df)

    df["MACD"] = macd
    df["MACD_SIGNAL"] = signal
    df["MACD_HIST"] = histogram

    last = df.iloc[-1]

    score_long = 0
    score_short = 0

    reasons_long = []
    reasons_short = []

    # EMA TREND
    if last["close"] > last["EMA200"]:
        score_long += 2
        reasons_long.append("قیمت بالای EMA200")

    if last["close"] < last["EMA200"]:
        score_short += 2
        reasons_short.append("قیمت زیر EMA200")

    # EMA MOMENTUM
    if last["EMA20"] > last["EMA50"]:
        score_long += 1
        reasons_long.append("EMA20 بالای EMA50")

    if last["EMA20"] < last["EMA50"]:
        score_short += 1
        reasons_short.append("EMA20 زیر EMA50")

    # RSI
    if 50 < last["RSI"] < 70:
        score_long += 1
        reasons_long.append("RSI مناسب خرید")

    if 30 < last["RSI"] < 50:
        score_short += 1
        reasons_short.append("RSI مناسب فروش")

    # MACD
    if last["MACD"] > last["MACD_SIGNAL"]:
        score_long += 2
        reasons_long.append("MACD صعودی")

    if last["MACD"] < last["MACD_SIGNAL"]:
        score_short += 2
        reasons_short.append("MACD نزولی")

    # تصمیم نهایی
    if score_long >= 5 and score_long > score_short + 1:

        return {
            "signal": "LONG",
            "score": score_long,
            "rsi": round(float(last["RSI"]), 2),
            "price": float(last["close"]),
            "reason": " | ".join(reasons_long)
        }

    if score_short >= 5 and score_short > score_long + 1:

        return {
            "signal": "SHORT",
            "score": score_short,
            "rsi": round(float(last["RSI"]), 2),
            "price": float(last["close"]),
            "reason": " | ".join(reasons_short)
        }

    return {
        "signal": "NO TRADE",
        "score": max(score_long, score_short),
        "rsi": round(float(last["RSI"]), 2),
        "price": float(last["close"]),
        "reason": "شرایط ورود به اندازه کافی قوی نیست"
    }


if __name__ == "__main__":
    print("Analysis Engine OK ✅")
