import pandas as pd
import numpy as np


# =========================================================
# EMA
# =========================================================

def calculate_ema(df, period):

    return df["close"].ewm(
        span=period,
        adjust=False
    ).mean()


# =========================================================
# RSI
# =========================================================

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

    rs = (
        avg_gain
        /
        avg_loss.replace(0, np.nan)
    )

    return 100 - (
        100 / (1 + rs)
    )


# =========================================================
# MACD
# =========================================================

def calculate_macd(df):

    ema12 = calculate_ema(df, 12)

    ema26 = calculate_ema(df, 26)

    macd = ema12 - ema26

    signal = macd.ewm(
        span=9,
        adjust=False
    ).mean()

    histogram = macd - signal

    return (
        macd,
        signal,
        histogram
    )


# =========================================================
# ATR
# =========================================================

def calculate_atr(
    df,
    period=14
):

    high_low = (
        df["high"]
        -
        df["low"]
    )

    high_close = (
        df["high"]
        -
        df["close"].shift()
    ).abs()

    low_close = (
        df["low"]
        -
        df["close"].shift()
    ).abs()

    true_range = pd.concat(
        [
            high_low,
            high_close,
            low_close
        ],
        axis=1
    ).max(axis=1)

    return true_range.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()


# =========================================================
# ANALYSIS
# =========================================================

def analyze(df):

    if df is None or len(df) < 200:

        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "reason": "داده کافی نیست"
        }

    df = df.copy()

    # =====================================================
    # Indicators
    # =====================================================

    df["EMA20"] = calculate_ema(
        df,
        20
    )

    df["EMA50"] = calculate_ema(
        df,
        50
    )

    df["EMA200"] = calculate_ema(
        df,
        200
    )

    df["RSI"] = calculate_rsi(df)

    (
        df["MACD"],
        df["MACD_SIGNAL"],
        df["MACD_HIST"]
    ) = calculate_macd(df)

    df["ATR"] = calculate_atr(df)

    df["VOLUME_AVG"] = (
        df["volume"]
        .rolling(20)
        .mean()
    )

    # =====================================================
    # آخرین کندل بسته شده
    # =====================================================

    last = df.iloc[-1]

    previous = df.iloc[-2]

    price = float(last["close"])

    rsi = float(last["RSI"])

    atr = float(last["ATR"])

    # =====================================================
    # اعتبار
    # =====================================================

    if not np.isfinite(rsi):

        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "price": price,
            "atr": atr if np.isfinite(atr) else 0,
            "reason": "RSI معتبر نیست"
        }

    if not np.isfinite(atr) or atr <= 0:

        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "price": price,
            "atr": 0,
            "reason": "ATR معتبر نیست"
        }

    # =====================================================
    # امتیاز
    # =====================================================

    long_score = 0

    short_score = 0

    long_reasons = []

    short_reasons = []

    # =====================================================
    # 1 EMA200
    # =====================================================

    if price > last["EMA200"]:

        long_score += 2

        long_reasons.append(
            "بالای EMA200"
        )

    elif price < last["EMA200"]:

        short_score += 2

        short_reasons.append(
            "زیر EMA200"
        )

    # =====================================================
    # 2 EMA20 / EMA50
    # =====================================================

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

    # =====================================================
    # 3 شیب EMA50
    # =====================================================

    if last["EMA50"] > previous["EMA50"]:

        long_score += 1

        long_reasons.append(
            "شیب EMA50 صعودی"
        )

    elif last["EMA50"] < previous["EMA50"]:

        short_score += 1

        short_reasons.append(
            "شیب EMA50 نزولی"
        )

    # =====================================================
    # 4 RSI
    # =====================================================

    if 52 <= rsi <= 68:

        long_score += 2

        long_reasons.append(
            "RSI صعودی"
        )

    elif 32 <= rsi <= 48:

        short_score += 2

        short_reasons.append(
            "RSI نزولی"
        )

    elif rsi > 70:

        short_score += 1

        short_reasons.append(
            "RSI اشباع خرید"
        )

    elif rsi < 30:

        long_score += 1

        long_reasons.append(
            "RSI اشباع فروش"
        )

    # =====================================================
    # 5 MACD
    # =====================================================

    macd = float(
        last["MACD"]
    )

    macd_signal = float(
        last["MACD_SIGNAL"]
    )

    hist = float(
        last["MACD_HIST"]
    )

    previous_hist = float(
        previous["MACD_HIST"]
    )

    if (
        macd > macd_signal
        and
        hist > 0
        and
        hist >= previous_hist
    ):

        long_score += 2

        long_reasons.append(
            "MACD صعودی"
        )

    elif (
        macd < macd_signal
        and
        hist < 0
        and
        hist <= previous_hist
    ):

        short_score += 2

        short_reasons.append(
            "MACD نزولی"
        )

    # =====================================================
    # 6 Volume
    # =====================================================

    volume_avg = float(
        last["VOLUME_AVG"]
    )

    if (
        np.isfinite(volume_avg)
        and
        volume_avg > 0
        and
        last["volume"]
        >
        volume_avg * 1.10
    ):

        if long_score > short_score:

            long_score += 1

            long_reasons.append(
                "حجم قوی"
            )

        elif short_score > long_score:

            short_score += 1

            short_reasons.append(
                "حجم قوی"
            )

    # =====================================================
    # قدرت روند
    # =====================================================

    ema_distance = abs(
        last["EMA20"]
        -
        last["EMA50"]
    )

    trend_strength = (
        ema_distance / atr
    )

    if trend_strength < 0.20:

        return {
            "signal": "NO TRADE",
            "score": max(
                long_score,
                short_score
            ),
            "confidence": 0,
            "rsi": round(rsi, 2),
            "price": price,
            "atr": atr,
            "long_score": long_score,
            "short_score": short_score,
            "reason": "روند ضعیف"
        }

    # =====================================================
    # تعیین جهت
    # =====================================================

    best_score = max(
        long_score,
        short_score
    )

    difference = abs(
        long_score
        -
        short_score
    )

    # =====================================================
    # حداقل امتیاز
    # =====================================================

    if best_score < 7:

        return {
            "signal": "NO TRADE",
            "score": best_score,
            "confidence": best_score * 10,
            "rsi": round(rsi, 2),
            "price": price,
            "atr": atr,
            "long_score": long_score,
            "short_score": short_score,
            "reason": "امتیاز کافی نیست"
        }

    # =====================================================
    # اختلاف جهت
    # =====================================================

    if difference < 3:

        return {
            "signal": "NO TRADE",
            "score": best_score,
            "confidence": best_score * 10,
            "rsi": round(rsi, 2),
            "price": price,
            "atr": atr,
            "long_score": long_score,
            "short_score": short_score,
            "reason": "جهت مشخص نیست"
        }

    # =====================================================
    # LONG
    # =====================================================

    if long_score > short_score:

        stop_loss = (
            price
            -
            atr * 2
        )

        tp1 = (
            price
            +
            atr * 2
        )

        take_profit = (
            price
            +
            atr * 4
        )

        return {
            "signal": "LONG",
            "score": long_score,
            "confidence": min(
                100,
                long_score * 10
            ),
            "rsi": round(rsi, 2),
            "price": price,
            "atr": atr,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "take_profit": take_profit,
            "long_score": long_score,
            "short_score": short_score,
            "reason": " | ".join(
                long_reasons
            )
        }

    # =====================================================
    # SHORT
    # =====================================================

    if short_score > long_score:

        stop_loss = (
            price
            +
            atr * 2
        )

        tp1 = (
            price
            -
            atr * 2
        )

        take_profit = (
            price
            -
            atr * 4
        )

        return {
            "signal": "SHORT",
            "score": short_score,
            "confidence": min(
                100,
                short_score * 10
            ),
            "rsi": round(rsi, 2),
            "price": price,
            "atr": atr,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "take_profit": take_profit,
            "long_score": long_score,
            "short_score": short_score,
            "reason": " | ".join(
                short_reasons
            )
        }

    return {
        "signal": "NO TRADE",
        "score": best_score,
        "confidence": 0,
        "rsi": round(rsi, 2),
        "price": price,
        "atr": atr,
        "long_score": long_score,
        "short_score": short_score,
        "reason": "بازار نامشخص"
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print(
        "Advanced Analysis Engine v3 OK"
    )
