import pandas as pd
import numpy as np


def calculate_ema(df, period):
    return df["close"].ewm(
        span=period,
        adjust=False
    ).mean()


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

    return 100 - (100 / (1 + rs))


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


def calculate_atr(df, period=14):

    high_low = df["high"] - df["low"]

    high_close = (
        df["high"] - df["close"].shift()
    ).abs()

    low_close = (
        df["low"] - df["close"].shift()
    ).abs()

    true_range = pd.concat(
        [high_low, high_close, low_close],
        axis=1
    ).max(axis=1)

    return true_range.rolling(period).mean()


def analyze(df):

    if df is None or len(df) < 200:
        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "reason": "داده کافی نیست"
        }

    df = df.copy()

    # EMA
    df["EMA20"] = calculate_ema(df, 20)
    df["EMA50"] = calculate_ema(df, 50)
    df["EMA200"] = calculate_ema(df, 200)

    # RSI
    df["RSI"] = calculate_rsi(df)

    # MACD
    macd, signal, histogram = calculate_macd(df)

    df["MACD"] = macd
    df["MACD_SIGNAL"] = signal
    df["MACD_HIST"] = histogram

    # ATR
    df["ATR"] = calculate_atr(df)

    # Volume average
    df["VOLUME_AVG"] = df["volume"].rolling(20).mean()

    last = df.iloc[-1]
    previous = df.iloc[-2]

    long_score = 0
    short_score = 0

    long_reasons = []
    short_reasons = []

    # -------------------------
    # TREND
    # -------------------------

    if last["close"] > last["EMA200"]:
        long_score += 2
        long_reasons.append("روند بالای EMA200")

    elif last["close"] < last["EMA200"]:
        short_score += 2
        short_reasons.append("روند زیر EMA200")

    # -------------------------
    # EMA MOMENTUM
    # -------------------------

    if last["EMA20"] > last["EMA50"]:
        long_score += 2
        long_reasons.append("EMA20 بالای EMA50")

    elif last["EMA20"] < last["EMA50"]:
        short_score += 2
        short_reasons.append("EMA20 زیر EMA50")

    # -------------------------
    # RSI
    # -------------------------

    if 50 <= last["RSI"] <= 65:
        long_score += 2
        long_reasons.append("RSI مناسب LONG")

    elif 35 <= last["RSI"] < 50:
        short_score += 2
        short_reasons.append("RSI مناسب SHORT")

    # جلوگیری از ورود در اشباع شدید
    if last["RSI"] >= 75:
        long_score -= 2

    if last["RSI"] <= 25:
        short_score -= 2

    # -------------------------
    # MACD
    # -------------------------

    if (
        last["MACD"] > last["MACD_SIGNAL"]
        and last["MACD_HIST"] > previous["MACD_HIST"]
    ):
        long_score += 2
        long_reasons.append("MACD و مومنتوم صعودی")

    elif (
        last["MACD"] < last["MACD_SIGNAL"]
        and last["MACD_HIST"] < previous["MACD_HIST"]
    ):
        short_score += 2
        short_reasons.append("MACD و مومنتوم نزولی")

    # -------------------------
    # VOLUME
    # -------------------------

    if last["volume"] > last["VOLUME_AVG"]:

        if long_score > short_score:
            long_score += 1
            long_reasons.append("حجم تأییدکننده")

        elif short_score > long_score:
            short_score += 1
            short_reasons.append("حجم تأییدکننده")

    # -------------------------
    # DECISION
    # -------------------------

    difference = abs(long_score - short_score)

    best_score = max(long_scor
