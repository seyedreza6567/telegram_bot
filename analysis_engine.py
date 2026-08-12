import pandas as pd
import numpy as np


# =========================================================
# EMA
# =========================================================

def calculate_ema(series, period):
    return series.ewm(
        span=period,
        adjust=False
    ).mean()


# =========================================================
# RSI
# =========================================================

def calculate_rsi(series, period=14):

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
# MACD
# =========================================================

def calculate_macd(series):

    ema12 = calculate_ema(series, 12)
    ema26 = calculate_ema(series, 26)

    macd = ema12 - ema26

    signal = calculate_ema(
        macd,
        9
    )

    histogram = macd - signal

    return macd, signal, histogram


# =========================================================
# ATR
# =========================================================

def calculate_atr(df, period=14):

    previous_close = df["close"].shift(1)

    tr1 = (
        df["high"] -
        df["low"]
    )

    tr2 = (
        df["high"] -
        previous_close
    ).abs()

    tr3 = (
        df["low"] -
        previous_close
    ).abs()

    true_range = pd.concat(
        [
            tr1,
            tr2,
            tr3
        ],
        axis=1
    ).max(axis=1)

    return true_range.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()


# =========================================================
# ANALYSIS ENGINE
# =========================================================

def analyze(df):

    if df is None or len(df) < 250:

        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "long_score": 0,
            "short_score": 0,
            "reason": "داده کافی نیست"
        }

    df = df.copy()

    close = df["close"]

    df["ema20"] = calculate_ema(
        close,
        20
    )

    df["ema50"] = calculate_ema(
        close,
        50
    )

    df["ema200"] = calculate_ema(
        close,
        200
    )

    df["rsi"] = calculate_rsi(
        close,
        14
    )

    (
        df["macd"],
        df["macd_signal"],
        df["macd_hist"]
    ) = calculate_macd(
        close
    )

    df["atr"] = calculate_atr(
        df,
        14
    )

    df["volume_avg"] = (
        df["volume"]
        .rolling(20)
        .mean()
    )

    last = df.iloc[-1]
    previous = df.iloc[-2]
    previous3 = df.iloc[-4]
    previous5 = df.iloc[-6]

    price = float(last["close"])
    ema20 = float(last["ema20"])
    ema50 = float(last["ema50"])
    ema200 = float(last["ema200"])
    rsi = float(last["rsi"])
    atr = float(last["atr"])

    macd = float(last["macd"])
    macd_signal = float(last["macd_signal"])
    macd_hist = float(last["macd_hist"])

    previous_macd_hist = float(
        previous["macd_hist"]
    )

    previous3_ema20 = float(
        previous3["ema20"]
    )

    previous3_ema50 = float(
        previous3["ema50"]
    )

    previous5_close = float(
        previous5["close"]
    )

    volume = float(
        last["volume"]
    )

    volume_avg = float(
        last["volume_avg"]
    )

    if not np.isfinite(rsi):

        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "long_score": 0,
            "short_score": 0,
            "reason": "RSI نامعتبر"
        }

    if not np.isfinite(atr) or atr <= 0:

        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "long_score": 0,
            "short_score": 0,
            "reason": "ATR نامعتبر"
        }

    # =====================================================
    # TREND STRENGTH
    # =====================================================

    ema_distance = abs(
        ema20 - ema50
    )

    trend_strength = (
        ema_distance / atr
    )

    # =====================================================
    # MOMENTUM
    # =====================================================

    momentum = (
        price -
        previous5_close
    ) / previous5_close

    # =====================================================
    # SCORES
    # =====================================================

    long_score = 0
    short_score = 0

    long_reasons = []
    short_reasons = []

    # =====================================================
    # LONG
    # =====================================================

    if price > ema200:

        long_score += 2

        long_reasons.append(
            "قیمت بالای EMA200"
        )

    if (
        ema20 > ema50
        and
        ema50 > ema200
    ):

        long_score += 3

        long_reasons.append(
            "ساختار صعودی EMA"
        )

    if (
        ema20 > float(previous["ema20"])
        and
        ema50 > float(previous["ema50"])
    ):

        long_score += 2

        long_reasons.append(
            "شیب EMA صعودی"
        )

    if (
        ema20 > previous3_ema20
        and
        ema50 > previous3_ema50
    ):

        long_score += 1

        long_reasons.append(
            "روند کوتاه‌مدت صعودی"
        )

    if 53 <= rsi <= 63:

        long_score += 2

        long_reasons.append(
            "RSI مناسب"
        )

    elif rsi > 68:

        long_score -= 2

    elif rsi < 45:

        long_score -= 1

    if (
        macd > macd_signal
        and
        macd_hist > 0
        and
        macd_hist >= previous_macd_hist
    ):

        long_score += 2

        long_reasons.append(
            "MACD صعودی"
        )

    if momentum > 0.001:

        long_score += 1

        long_reasons.append(
            "مومنتوم مثبت"
        )

    if (
        np.isfinite(volume_avg)
        and
        volume_avg > 0
        and
        volume > volume_avg * 1.05
    ):

        long_score += 1

        long_reasons.append(
            "حجم تأییدکننده"
        )

    # =====================================================
    # SHORT
    # =====================================================

    if price < ema200:

        short_score += 2

        short_reasons.append(
            "قیمت زیر EMA200"
        )

    if (
        ema20 < ema50
        and
        ema50 < ema200
    ):

        short_score += 3

        short_reasons.append(
            "ساختار نزولی EMA"
        )

    if (
        ema20 < float(previous["ema20"])
        and
        ema50 < float(previous["ema50"])
    ):

        short_score += 2

        short_reasons.append(
            "شیب EMA نزولی"
        )

    if (
        ema20 < previous3_ema20
        and
        ema50 < previous3_ema50
    ):

        short_score += 1

        short_reasons.append(
            "روند کوتاه‌مدت نزولی"
        )

    if 37 <= rsi <= 47:

        short_score += 2

        short_reasons.append(
            "RSI مناسب SHORT"
        )

    elif rsi < 32:

        short_score -= 2

    elif rsi > 55:

        short_score -= 1

    if (
        macd < macd_signal
        and
        macd_hist < 0
        and
        macd_hist <= previous_macd_hist
    ):

        short_score += 2

        short_reasons.append(
            "MACD نزولی"
        )

    if momentum < -0.001:

        short_score += 1

        short_reasons.append(
            "مومنتوم منفی"
        )

    if (
        np.isfinite(volume_avg)
        and
        volume_avg > 0
        and
        volume > volume_avg * 1.05
    ):

        short_score += 1

        short_reasons.append(
            "حجم تأییدکننده"
        )

    # =====================================================
    # بازار ضعیف
    # =====================================================

    if trend_strength < 0.30:

        return {
            "signal": "NO TRADE",
            "score": max(
                long_score,
                short_score
            ),
            "confidence": 0,
            "long_score": long_score,
            "short_score": short_score,
            "price": price,
            "atr": atr,
            "reason": "قدرت روند کافی نیست"
        }

    # =====================================================
    # تصمیم
    # =====================================================

    best_score = max(
        long_score,
        short_score
    )

    difference = abs(
        long_score -
        short_score
    )

    # =====================================================
    # LONG
    # =====================================================

    if (
        long_score >= 9
        and
        long_score > short_score
        and
        difference >= 3
    ):

        stop_loss = (
            price -
            atr * 2
        )

        tp1 = (
            price +
            atr * 2
        )

        tp2 = (
            price +
            atr * 4
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
            "price": price,
            "atr": atr,
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

    if (
        short_score >= 10
        and
        short_score > long_score
        and
        difference >= 4
    ):

        stop_loss = (
            price +
            atr * 2
        )

        tp1 = (
            price -
            atr * 2
        )

        tp2 = (
            price -
            atr * 4
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
            "price": price,
            "atr": atr,
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
        "atr": atr,
        "reason": "شرایط ورود کامل نیست"
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print(
        "Analysis Engine v4 OK"
    )
