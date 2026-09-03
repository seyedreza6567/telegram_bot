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
# ADX (Wilder's smoothing)
# =========================================================
def calculate_adx(df, period=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    previous_high = high.shift(1)
    previous_low = low.shift(1)
    previous_close = close.shift(1)

    up_move = high - previous_high
    down_move = previous_low - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr1 = high - low
    tr2 = (high - previous_close).abs()
    tr3 = (low - previous_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr_wilder = true_range.ewm(alpha=1 / period, adjust=False).mean()

    plus_dm_series = pd.Series(plus_dm, index=df.index)
    minus_dm_series = pd.Series(minus_dm, index=df.index)

    plus_dm_smooth = plus_dm_series.ewm(alpha=1 / period, adjust=False).mean()
    minus_dm_smooth = minus_dm_series.ewm(alpha=1 / period, adjust=False).mean()

    plus_di = 100 * (plus_dm_smooth / atr_wilder.replace(0, np.nan))
    minus_di = 100 * (minus_dm_smooth / atr_wilder.replace(0, np.nan))

    di_sum = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()

    return adx, plus_di, minus_di


# =========================================================
# OBV (On-Balance Volume)
# =========================================================
def calculate_obv(df):
    close = df["close"]
    volume = df["volume"]

    direction = np.sign(close.diff()).fillna(0)
    obv = (direction * volume).cumsum()
    obv_ema = obv.ewm(span=20, adjust=False).mean()

    return obv, obv_ema


# =========================================================
# SUPPORT / RESISTANCE (rolling swing high/low zone)
# =========================================================
def calculate_support_resistance(df, lookback=50):
    resistance = df["high"].rolling(lookback).max()
    support = df["low"].rolling(lookback).min()
    return support, resistance


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
        "score_ratio": round(max(long_score, short_score) / MAX_SCORE, 4),
        "reason": reason
    }


# =========================================================
# SETTINGS
# =========================================================
# Previous max theoretical score was 15 (trend/RSI/MACD/momentum/volume-spike).
# Added: Support/Resistance (+2), OBV (+1), ADX (+2) => new max = 20.
# Entry threshold rescaled to keep the same strictness ratio (~53%):
# old: 8/15 = 0.533  ->  new: round(0.533 * 20) = 11
MAX_SCORE = 20.0
ENTRY_SCORE_THRESHOLD = 11
MIN_SCORE_DIFFERENCE = 3
TREND_GATE_CAP = 9  # was 7/15 -> rescaled to ~9/20


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
    df["adx"], df["plus_di"], df["minus_di"] = calculate_adx(df, 14)
    df["obv"], df["obv_ema"] = calculate_obv(df)
    df["support"], df["resistance"] = calculate_support_resistance(df, 50)

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
    adx = _safe_float(last["adx"])
    obv = _safe_float(last["obv"])
    obv_ema = _safe_float(last["obv_ema"])
    support = _safe_float(last["support"])
    resistance = _safe_float(last["resistance"])

    values = [price, ema20, ema50, ema200, rsi, atr, macd, macd_signal,
              macd_hist, previous_macd_hist, previous3_ema20,
              previous3_ema50, previous5_close]

    if any(value is None for value in values):
        return _no_trade("اندیکاتور نامعتبر", price=price, atr=atr, rsi=rsi)

    if atr <= 0:
        return _no_trade("ATR نامعتبر", price=price, atr=atr, rsi=rsi)

    # ADX/OBV/S-R are treated as optional enhancers: if not yet available
    # (e.g. early in the series) they simply contribute zero, they never
    # block a signal on their own.
    adx_valid = adx is not None
    obv_valid = obv is not None and obv_ema is not None
    sr_valid = support is not None and resistance is not None

    # =====================================================
    # TREND
    # =====================================================
    ema_distance = abs(ema20 - ema50)
    trend_strength = ema_distance / atr

    long_trend = price > ema200 and ema20 > ema50
    short_trend = price < ema200 and ema20 < ema50

    if trend_strength < 0.26:
        return _no_trade("قدرت روند کافی نیست", price=price, atr=atr, rsi=rsi,
                          trend="WEAK", trend_strength=trend_strength)

    # =====================================================
    # MOMENTUM
    # =====================================================
    momentum = (price - previous5_close) / previous5_close

    # =====================================================
    # SCORES (max theoretical = 20)
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

    # VOLUME SPIKE (existing simple check)
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
    # OBV (money-flow direction, independent of price-only momentum)
    # =====================================================
    if obv_valid:
        if obv > obv_ema:
            long_score += 1
            long_reasons.append("OBV صعودی (جریان پول مثبت)")
        elif obv < obv_ema:
            short_score += 1
            short_reasons.append("OBV نزولی (جریان پول منفی)")

    # =====================================================
    # ADX (trend-strength confirmation, direction-agnostic)
    # =====================================================
    if adx_valid:
        if adx >= 20:
            if long_trend:
                long_score += 2
                long_reasons.append(f"ADX قوی ({round(adx,1)})")
            if short_trend:
                short_score += 2
                short_reasons.append(f"ADX قوی ({round(adx,1)})")
        elif adx < 15:
            # choppy / rangebound market - penalize both directions
            long_score -= 2
            short_score -= 2

    # =====================================================
    # SUPPORT / RESISTANCE (proximity in ATR units)
    # =====================================================
    if sr_valid and atr > 0:
        distance_to_resistance = (resistance - price) / atr
        distance_to_support = (price - support) / atr

        # LONG: reward being near support (room to run up),
        # penalize being right under a resistance wall.
        if distance_to_support <= 1.5:
            long_score += 2
            long_reasons.append("نزدیک ناحیه حمایت")
        if distance_to_resistance <= 1.0:
            long_score -= 2
            long_reasons.append("نزدیک ناحیه مقاومت (ریسک برخورد)")

        # SHORT: reward being near resistance, penalize being
        # right above a support floor.
        if distance_to_resistance <= 1.5:
            short_score += 2
            short_reasons.append("نزدیک ناحیه مقاومت")
        if distance_to_support <= 1.0:
            short_score -= 2
            short_reasons.append("نزدیک ناحیه حمایت (ریسک برخورد)")

    # =====================================================
    # TREND GATE
    # =====================================================
    if not long_trend:
        long_score = min(long_score, TREND_GATE_CAP)
    if not short_trend:
        short_score = min(short_score, TREND_GATE_CAP)

    best_score = max(long_score, short_score)
    difference = abs(long_score - short_score)
    score_ratio = best_score / MAX_SCORE

    # =====================================================
    # LONG
    # =====================================================
    if (long_trend and long_score >= ENTRY_SCORE_THRESHOLD
            and long_score > short_score and difference >= MIN_SCORE_DIFFERENCE):
        stop_loss = price - atr * 2.0
        tp1 = price + atr * 2.0
        tp2 = price + atr * 4.0
        return {
            "signal": "LONG",
            "score": long_score,
            "confidence": min(100, 55 + long_score * 3),
            "long_score": long_score,
            "short_score": short_score,
            "price": price,
            "rsi": rsi,
            "atr": atr,
            "adx": adx,
            "obv": obv,
            "support": support,
            "resistance": resistance,
            "trend": "BULLISH",
            "trend_strength": trend_strength,
            "score_ratio": round(long_score / MAX_SCORE, 4),
            "stop_loss": stop_loss,
            "tp1": tp1,
            "take_profit": tp2,
            "reason": " | ".join(long_reasons)
        }

    # =====================================================
    # SHORT
    # =====================================================
    if (short_trend and short_score >= ENTRY_SCORE_THRESHOLD
            and short_score > long_score and difference >= MIN_SCORE_DIFFERENCE):
        stop_loss = price + atr * 2.0
        tp1 = price - atr * 2.0
        tp2 = price - atr * 4.0
        return {
            "signal": "SHORT",
            "score": short_score,
            "confidence": min(100, 55 + short_score * 3),
            "long_score": long_score,
            "short_score": short_score,
            "price": price,
            "rsi": rsi,
            "atr": atr,
            "adx": adx,
            "obv": obv,
            "support": support,
            "resistance": resistance,
            "trend": "BEARISH",
            "trend_strength": trend_strength,
            "score_ratio": round(short_score / MAX_SCORE, 4),
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
        "adx": adx,
        "obv": obv,
        "support": support,
        "resistance": resistance,
        "trend": "BULLISH" if long_trend else "BEARISH" if short_trend else "NEUTRAL",
        "trend_strength": trend_strength,
        "score_ratio": round(score_ratio, 4),
        "reason": "شرایط ورود کامل نیست"
    }


if __name__ == "__main__":
    print("Analysis Engine OK")
