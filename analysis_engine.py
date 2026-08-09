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

    return true_range.rolling(
        period
    ).mean()


def analyze(df):

    if df is None or len(df) < 200:
        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
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

    df["ATR"] = calculate_atr(df)

    df["VOLUME_AVG"] = df["volume"].rolling(
        20
    ).mean()

    last = df.iloc[-1]
    previous = df.iloc[-2]

    long_score = 0
    short_score = 0

    long_reasons = []
    short_reasons = []

    # TREND
    if last["close"] > last["EMA200"]:

        long_score += 2
        long_reasons.append(
            "قیمت بالای EMA200"
        )

    elif last["close"] < last["EMA200"]:

        short_score += 2
        short_reasons.append(
            "قیمت زیر EMA200"
        )

    # EMA
    if last["EMA20"] > last["EMA50"]:

        long_score += 2
        long_reasons.append(
            "EMA20 بالای EMA50"
        )

    elif last["EMA20"] < last["EMA50"]:

        short_score += 2
        short_reasons.append(
            "EMA20 زیر EMA50"
        )

    # RSI
    if 50 <= last["RSI"] <= 65:

        long_score += 2
        long_reasons.append(
            "RSI مناسب LONG"
        )

    elif 35 <= last["RSI"] < 50:

        short_score += 2
        short_reasons.append(
            "RSI مناسب SHORT"
        )

    # جلوگیری از ورود در اشباع شدید
    if last["RSI"] >= 75:
        long_score -= 2

    if last["RSI"] <= 25:
        short_score -= 2

    # MACD
    if (
        last["MACD"] > last["MACD_SIGNAL"]
        and
        last["MACD_HIST"] > previous["MACD_HIST"]
    ):

        long_score += 2
        long_reasons.append(
            "MACD صعودی"
        )

    elif (
        last["MACD"] < last["MACD_SIGNAL"]
        and
        last["MACD_HIST"] < previous["MACD_HIST"]
    ):

        short_score += 2
        short_reasons.append(
            "MACD نزولی"
        )

    # VOLUME
    if last["volume"] > last["VOLUME_AVG"]:

        if long_score > short_score:

            long_score += 1
            long_reasons.append(
                "حجم تأییدکننده"
            )

        elif short_score > long_score:

            short_score += 1
            short_reasons.append(
                "حجم تأییدکننده"
            )

    best_score = max(
        long_score,
        short_score
    )

    difference = abs(
        long_score - short_score
    )

    rsi_value = round(
        float(last["RSI"]),
        2
    )

    price = float(
        last["close"]
    )

    atr = float(
        last["ATR"]
    )

    # اگر ATR معتبر نبود
    if np.isnan(atr):

        return {
            "signal": "NO TRADE",
            "score": best_score,
            "confidence": 0,
            "rsi": rsi_value,
            "price": price,
            "atr": 0,
            "reason": "ATR معتبر نیست"
        }

    # امتیاز کافی نیست
    if best_score < 6:

        return {
            "signal": "NO TRADE",
            "score": best_score,
            "confidence": min(
                100,
                max(0, best_score * 10)
            ),
            "rsi": rsi_value,
            "price": price,
            "atr": atr,
            "reason": "قدرت سیگنال کافی نیست"
        }

    # اختلاف سیگنال‌ها کم است
    if difference < 3:

        return {
            "signal": "NO TRADE",
            "score": best_score,
            "confidence": min(
                100,
                max(0, best_score * 10)
            ),
            "rsi": rsi_value,
            "price": price,
            "atr": atr,
            "reason": "تضاد بین سیگنال‌ها"
        }

    # LONG
    if long_score > short_score:

        stop_loss = price - (atr * 2)
        take_profit = price + (atr * 4)

        return {
            "signal": "LONG",
            "score": long_score,
            "confidence": min(
                100,
                long_score * 10
            ),
            "rsi": rsi_value,
            "price": price,
            "atr": atr,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "reason": " | ".join(long_reasons)
        }

    # SHORT
    if short_score > long_score:

        stop_loss = price + (atr * 2)
        take_profit = price - (atr * 4)

        return {
            "signal": "SHORT",
            "score": short_score,
            "confidence": min(
                100,
                short_score * 10
            ),
            "rsi": rsi_value,
            "price": price,
            "atr": atr,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "reason": " | ".join(short_reasons)
        }

    return {
        "signal": "NO TRADE",
        "score": best_score,
        "confidence": 0,
        "rsi": rsi_value,
        "price": price,
        "atr": atr,
        "reason": "بازار نامشخص"
    }


if __name__ == "__main__":

    print("Advanced Analysis Engine OK")
