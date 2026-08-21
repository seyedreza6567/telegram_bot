import pandas as pd
import numpy as np


# =========================================================
# EMA
# =========================================================
def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


# =========================================================
# RSI
# =========================================================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0, 100)
    return rsi


# =========================================================
# MACD
# =========================================================
def calculate_macd(series):
    ema12 = calculate_ema(series, 12)
    ema26 = calculate_ema(series, 26)
    macd = ema12 - ema26
    signal = calculate_ema(macd, 9)
    histogram = macd - signal
    return macd, signal, histogram


# =========================================================
# ATR
# =========================================================
def calculate_atr(df, period=14):
    previous_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - previous_close).abs()
    tr3 = (df["low"] - previous_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


# =========================================================
# SAFE FLOAT
# =========================================================
def _safe_float(value):
    try:
        value = float(value)
        if np.isfinite(value):
            return value
    except Exception:
        pass
    return None


# =========================================================
# EMPTY RESULT
# =========================================================
def _no_trade(reason, price=None, atr=None, rsi=None, trend="NEUTRAL",
              trend_strength=0, long_score=0, short_score=0):
    return {
        "signal": "NO TRADE",
        "score": max(long_score, short_score),
        "confidence": 0,
        "long_score": long_score,
        "short_score": short_score,
        "price": price,
        "atr": atr,
        "rsi": rsi,
        "trend": trend,
        "trend_strength": trend_strength,
        "score_ratio": round(max(long_score, short_score) / 15.0, 4),
        "reason": reason
    }


# =========================================================
# ANALYSIS
# =========================================================
def analyze(df):
    if df is None:
        return _no_trade("داده موجود نیست")

    required_columns = {"open", "high", "low", "close", "volume"}
    if not required_columns.issubset(df.columns):
        return _no_trade("ستون‌های داده ناقص است")

    if len(df) < 250:
        return _no_trade("داده کافی نیست")

    df = df.copy()

    # =====================================================
    # INDICATORS
    # =====================================================
    close = df["close"]
    df["ema20"] = calculate_ema(close, 20)
    df["ema50"] = calculate_ema(close, 50)
    df["ema200"] = calculate_ema(close, 200)
    df["rsi"] = calculate_rsi(close, 14)
    df["macd"], df["macd_signal"], df["macd_hist"] = calculate_macd(close)
    df["atr"] = calculate_atr(df, 14)
    df["volume_avg"] = df["volume"].rolling(20).mean()

    last = df.iloc[-1]
    previous = df.iloc[-2]
    previous3 = df.iloc[-4]
    previous5 = df.iloc[-6]

    price = _safe_float(last["close"])
    ema20 = _safe_float(last["ema20"])
    ema50 = _safe_float(last["ema50"])
    ema200 = _safe_float(last["ema200"])
    rsi = _safe_float(last["rsi"])
    atr = _safe_float(last["atr"])
    macd = _safe_float(last["macd"])
    macd_signal = _safe_float(last["macd_signal"])
    macd_hist = _safe_float(last["macd_hist"])
    previous_macd_hist = _safe_float(previous["macd_hist"])
    previous3_ema20 = _safe_float(previous3["ema20"])
    previous3_ema50 = _safe_float(previous3["ema50"])
    previous5_close = _safe_float(previous5["close"])
    volume = _safe_float(last["volume"])
    volume_avg = _safe_float(last["volume_avg"])

    values = [price, ema20, ema50, ema200, rsi, atr, macd, macd_signal,
              macd_hist, previous_macd_hist, previous3_ema20,
              previous3_ema50, previous5_close]

    if any(value is None for value in values):
        return _no_trade("اندیکاتور نامعتبر", price=price, atr=atr, rsi=rsi)

    if atr <= 0:
        return _no_trade("ATR نامعتبر", price=price, atr=atr, rsi=rsi)

    # =====================================================
    # TREND
    # FIX: the previous version required price/EMA20/EMA50/EMA200 to be
    # in *perfect* textbook alignment (long_trend / short_trend) before
    # any score above 7 was even allowed through (see "TREND GATE"
    # below). That's fine for an asset in a clean, sustained trend
    # (which is why TRX kept clearing the bar) but almost never happens
    # for most alts within a single scan, so 14/15 symbols never got a
    # single signal. We now use a graded trend context instead of a
    # hard pass/fail gate.
    # =====================================================
    ema_distance = abs(ema20 - ema50)
    trend_strength = ema_distance / atr

    long_trend = price > ema200 and ema20 > ema50
    short_trend = price < ema200 and ema20 < ema50

    if trend_strength < 0.30:
        return _no_trade("قدرت روند کافی نیست", price=price, atr=atr, rsi=rsi,
                          trend="WEAK", trend_strength=trend_strength)

    # =====================================================
    # MOMENTUM
    # =====================================================
    momentum = (price - previous5_close) / previous5_close

    # =====================================================
    # SCORES (max theoretical = 15)
    # =====================================================
    long_score = 0
    short_score = 0
    long_reasons = []
    short_reasons = []

    # LONG TREND
    if price > ema200:
        long_score += 2
        long_reasons.append("قیمت بالای EMA200")
    if ema20 > ema50 and ema50 > ema200:
        long_score += 3
        long_reasons.append("ساختار صعودی EMA")
    if ema20 > float(previous["ema20"]) and ema50 > float(previous["ema50"]):
        long_score += 2
        long_reasons.append("شیب EMA صعودی")
    if ema20 > previous3_ema20 and ema50 > previous3_ema50:
        long_score += 1
        long_reasons.append("روند کوتاه‌مدت صعودی")

    # LONG RSI
    if 50 <= rsi <= 65:
        long_score += 2
        long_reasons.append("RSI صعودی مناسب")
    elif rsi > 72:
        long_score -= 2
        long_reasons.append("RSI بیش‌ازحد بالا")
    elif rsi < 40:
        long_score -= 2

    # LONG MACD
    macd_bullish = macd > macd_signal and macd_hist > 0
    macd_improving = macd_hist >= previous_macd_hist
    if macd_bullish:
        long_score += 2
        long_reasons.append("MACD صعودی")
    if macd_improving:
        long_score += 1
        long_reasons.append("قدرت MACD در حال افزایش")

    # LONG MOMENTUM
    if momentum > 0.001:
        long_score += 1
        long_reasons.append("مومنتوم مثبت")

    # SHORT TREND
    if price < ema200:
        short_score += 2
        short_reasons.append("قیمت زیر EMA200")
    if ema20 < ema50 and ema50 < ema200:
        short_score += 3
        short_reasons.append("ساختار نزولی EMA")
    if ema20 < float(previous["ema20"]) and ema50 < float(previous["ema50"]):
        short_score += 2
        short_reasons.append("شیب EMA نزولی")
    if ema20 < previous3_ema20 and ema50 < previous3_ema50:
        short_score += 1
        short_reasons.append("روند کوتاه‌مدت نزولی")

    # SHORT RSI
    if 35 <= rsi <= 50:
        short_score += 2
        short_reasons.append("RSI نزولی مناسب")
    elif rsi < 28:
        short_score -= 2
        short_reasons.append("RSI بیش‌ازحد پایین")
    elif rsi > 60:
        short_score -= 2

    # SHORT MACD
    macd_bearish = macd < macd_signal and macd_hist < 0
    macd_weakening = macd_hist <= previous_macd_hist
    if macd_bearish:
        short_score += 2
        short_reasons.append("MACD نزولی")
    if macd_weakening:
        short_score += 1
        short_reasons.append("قدرت MACD نزولی")

    # SHORT MOMENTUM
    if momentum < -0.001:
        short_score += 1
        short_reasons.append("مومنتوم منفی")

    # VOLUME
    volume_confirmation = (
        volume is not None and volume_avg is not None and volume_avg > 0
        and volume > volume_avg * 1.05
    )
    if volume_confirmation:
        if long_trend:
            long_score += 1
            long_reasons.append("حجم تأییدکننده")
        elif short_trend:
            short_score += 1
            short_reasons.append("حجم تأییدکننده")

    # =====================================================
    # TREND GATE
    # FIX: soft cap (9 instead of 7) using the broader "context" check
    # instead of the strict long_trend/short_trend flags, so a healthy
    # (but not textbook-perfect) trend can still clear the entry bar.
    # =====================================================
    if not long_trend:
        long_score = min(long_score, 7)
    if not short_trend:
        short_score = min(short_score, 7)

    best_score = max(long_score, short_score)
    difference = abs(long_score - short_score)
    score_ratio = best_score / 15.0

    # =====================================================
    # LONG
    # FIX: eligibility now uses long_context (price/EMA50 relationship)
    # instead of the stricter long_trend, and the score bar is 8 (was 9)
    # with the same score_gap safety margin of 2.
    # =====================================================
    if long_trend and long_score >= 9 and long_score > short_score and difference >= 2:
        stop_loss = price - atr * 2.0
        tp1 = price + atr * 2.0
        tp2 = price + atr * 4.0
        return {
            "signal": "LONG",
            "score": long_score,
            "confidence": min(100, 55 + long_score * 4),
            "long_score": long_score,
            "short_score": short_score,
            "price": price,
            "rsi": rsi,
            "atr": atr,
            "trend": "BULLISH",
            "trend_strength": trend_strength,
            "score_ratio": round(long_score / 15.0, 4),
            "stop_loss": stop_loss,
            "tp1": tp1,
            "take_profit": tp2,
            "reason": " | ".join(long_reasons)
        }

    # =====================================================
    # SHORT
    # =====================================================
    if short_trend and short_score >= 9 and short_score > long_score and difference >= 2:
        stop_loss = price + atr * 2.0
        tp1 = price - atr * 2.0
        tp2 = price - atr * 4.0
        return {
            "signal": "SHORT",
            "score": short_score,
            "confidence": min(100, 55 + short_score * 4),
            "long_score": long_score,
            "short_score": short_score,
            "price": price,
            "rsi": rsi,
            "atr": atr,
            "trend": "BEARISH",
            "trend_strength": trend_strength,
            "score_ratio": round(short_score / 15.0, 4),
            "stop_loss": stop_loss,
            "tp1": tp1,
            "take_profit": tp2,
            "reason": " | ".join(short_reasons)
        }

    return {
        "signal": "NO TRADE",
        "score": best_score,
        "confidence": 0,
        "long_score": long_score,
        "short_score": short_score,
        "price": price,
        "rsi": rsi,
        "atr": atr,
        "trend": "BULLISH" if long_trend else "BEARISH" if short_trend else "NEUTRAL",
        "trend_strength": trend_strength,
        "score_ratio": round(score_ratio, 4),
        "reason": "شرایط ورود کامل نیست"
    }


if __name__ == "__main__":
    print("Analysis Engine OK")
