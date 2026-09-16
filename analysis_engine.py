import numpy as np
import pandas as pd

import ta


# =========================================================
# پارامترهای امتیازدهی
#
# NOTE: بعد از اضافه شدن ADX + OBV + Support/Resistance،
# حداکثر امتیاز نظری از 15 به 20 رسید و آستانه‌ها به همان
# نسبت (تقریباً 0.73) بازمقیاس‌بندی شدند تا سخت‌گیری اصلی
# حفظ شود:
#   ENTRY_SCORE_THRESHOLD : 8  -> 11
#   MIN_SCORE_DIFFERENCE  : 2  -> 3
#   TREND_GATE_CAP        : 7  -> 9
# =========================================================

MAX_SCORE = 20.0

ENTRY_SCORE_THRESHOLD = 11

MIN_SCORE_DIFFERENCE = 3

# اگر گیت روند سخت‌گیرانه (EMA20/50/200) عبور نشود، امتیاز
# نهایی به این سقف محدود می‌شود تا معامله بر خلاف روند غالب
# رد شود، حتی اگر امتیازهای دیگر بالا باشند.
TREND_GATE_CAP = 9

# حداقل فاصله EMA20 از EMA50 (بر حسب ATR) برای این‌که روند
# «قوی» در نظر گرفته شود.
TREND_STRENGTH_MIN = 0.22

SR_LOOKBACK = 50

NEAR_ATR_MULTIPLE = 1.5

OPPOSING_WALL_ATR_MULTIPLE = 1.0


# =========================================================
# اندیکاتورهای کمکی
# =========================================================

def calculate_adx(df, period=14):

    adx_indicator = ta.trend.ADXIndicator(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=period,
        fillna=True
    )

    return (
        adx_indicator.adx(),
        adx_indicator.adx_pos(),
        adx_indicator.adx_neg()
    )


def calculate_obv(df, ema_period=20):

    obv_indicator = ta.volume.OnBalanceVolumeIndicator(
        close=df["close"],
        volume=df["volume"],
        fillna=True
    )

    obv = obv_indicator.on_balance_volume()

    obv_ema = obv.ewm(
        span=ema_period,
        adjust=False
    ).mean()

    return obv, obv_ema


def calculate_support_resistance(df, lookback=SR_LOOKBACK):

    support = df["low"].rolling(
        window=lookback,
        min_periods=max(5, lookback // 5)
    ).min()

    resistance = df["high"].rolling(
        window=lookback,
        min_periods=max(5, lookback // 5)
    ).max()

    return support, resistance


# =========================================================
# تحلیل یک تایم‌فریم
# =========================================================

def analyze(df):

    result = {
        "signal": "NO TRADE",
        "score": 0,
        "confidence": 0,
        "reason": "-",
        "price": None,
        "atr": None,
        "rsi": None,
    }

    if df is None or len(df) < 210:

        result["reason"] = "داده کافی برای تحلیل وجود ندارد."

        return result

    df = df.copy().reset_index(drop=True)

    close = df["close"]
    high = df["high"]
    low = df["low"]

    ema20 = ta.trend.EMAIndicator(close, window=20, fillna=True).ema_indicator()
    ema50 = ta.trend.EMAIndicator(close, window=50, fillna=True).ema_indicator()
    ema200 = ta.trend.EMAIndicator(close, window=200, fillna=True).ema_indicator()

    rsi = ta.momentum.RSIIndicator(close, window=14, fillna=True).rsi()

    atr = ta.volatility.AverageTrueRange(
        high=high,
        low=low,
        close=close,
        window=14,
        fillna=True
    ).average_true_range()

    adx, plus_di, minus_di = calculate_adx(df)

    obv, obv_ema = calculate_obv(df)

    support, resistance = calculate_support_resistance(df)

    i = len(df) - 1

    price = float(close.iloc[i])
    atr_value = float(atr.iloc[i]) if atr.iloc[i] and atr.iloc[i] > 0 else None
    rsi_value = round(float(rsi.iloc[i]), 1)

    result["price"] = price
    result["atr"] = round(atr_value, 6) if atr_value else None
    result["rsi"] = rsi_value

    if not atr_value:

        result["reason"] = "ATR نامعتبر است."

        return result

    # =====================================================
    # گیت سخت‌گیرانه روند (بدون تغییر نسبت به نسخه اصلی)
    # =====================================================

    long_trend = (
        price > ema20.iloc[i] > ema50.iloc[i] > ema200.iloc[i]
    )

    short_trend = (
        price < ema20.iloc[i] < ema50.iloc[i] < ema200.iloc[i]
    )

    trend_strength = abs(
        ema20.iloc[i] - ema50.iloc[i]
    ) / atr_value

    strong_trend = trend_strength >= TREND_STRENGTH_MIN

    trend_gate_passed_long = long_trend and strong_trend
    trend_gate_passed_short = short_trend and strong_trend

    # =====================================================
    # امتیاز جهت long / short
    # =====================================================

    long_score = 0
    short_score = 0

    reasons_long = []
    reasons_short = []

    # --- روند (وزن اصلی) ---

    if long_trend:
        long_score += 5
        reasons_long.append("روند صعودی (EMA20>50>200)")

    if short_trend:
        short_score += 5
        reasons_short.append("روند نزولی (EMA20<50<200)")

    if strong_trend and long_trend:
        long_score += 2
        reasons_long.append("قدرت روند کافی")

    if strong_trend and short_trend:
        short_score += 2
        reasons_short.append("قدرت روند کافی")

    # --- RSI ---

    if 45 <= rsi_value <= 70:
        long_score += 2
        reasons_long.append(f"RSI مناسب لانگ ({rsi_value})")

    if 30 <= rsi_value <= 55:
        short_score += 2
        reasons_short.append(f"RSI مناسب شورت ({rsi_value})")

    # --- ADX ---

    adx_value = float(adx.iloc[i])

    if adx_value >= 20:

        if plus_di.iloc[i] > minus_di.iloc[i]:
            long_score += 2
            reasons_long.append(f"ADX قوی و جهت‌دار ({round(adx_value, 1)})")
        else:
            short_score += 2
            reasons_short.append(f"ADX قوی و جهت‌دار ({round(adx_value, 1)})")

    elif adx_value < 15:

        long_score -= 2
        short_score -= 2
        reasons_long.append("بازار بدون روند (ADX پایین)")
        reasons_short.append("بازار بدون روند (ADX پایین)")

    # --- OBV ---

    if obv.iloc[i] > obv_ema.iloc[i]:
        long_score += 1
        reasons_long.append("OBV صعودی")
    elif obv.iloc[i] < obv_ema.iloc[i]:
        short_score += 1
        reasons_short.append("OBV نزولی")

    # --- Support / Resistance (فاصله بر حسب ATR) ---

    support_value = support.iloc[i]
    resistance_value = resistance.iloc[i]

    if pd.notna(support_value) and pd.notna(resistance_value):

        distance_to_support = abs(price - support_value) / atr_value
        distance_to_resistance = abs(resistance_value - price) / atr_value

        if distance_to_support <= NEAR_ATR_MULTIPLE:
            long_score += 2
            reasons_long.append("نزدیک حمایت")

        if distance_to_resistance <= OPPOSING_WALL_ATR_MULTIPLE:
            long_score -= 2
            reasons_long.append("مقاومت سنگین بالای سر")

        if distance_to_resistance <= NEAR_ATR_MULTIPLE:
            short_score += 2
            reasons_short.append("نزدیک مقاومت")

        if distance_to_support <= OPPOSING_WALL_ATR_MULTIPLE:
            short_score -= 2
            reasons_short.append("حمایت سنگین پایین")

    # =====================================================
    # اعمال سقف گیت روند
    # =====================================================

    if not trend_gate_passed_long:
        long_score = min(long_score, TREND_GATE_CAP)

    if not trend_gate_passed_short:
        short_score = min(short_score, TREND_GATE_CAP)

    long_score = max(0, min(long_score, MAX_SCORE))
    short_score = max(0, min(short_score, MAX_SCORE))

    # =====================================================
    # تصمیم نهایی
    # =====================================================

    signal = "NO TRADE"
    score = 0
    reason_list = []

    if (
        long_score >= ENTRY_SCORE_THRESHOLD
        and
        (long_score - short_score) >= MIN_SCORE_DIFFERENCE
        and
        trend_gate_passed_long
    ):
        signal = "LONG"
        score = long_score
        reason_list = reasons_long

    elif (
        short_score >= ENTRY_SCORE_THRESHOLD
        and
        (short_score - long_score) >= MIN_SCORE_DIFFERENCE
        and
        trend_gate_passed_short
    ):
        signal = "SHORT"
        score = short_score
        reason_list = reasons_short

    result["signal"] = signal
    result["score"] = round(score, 2)
    result["confidence"] = round((score / MAX_SCORE) * 100, 1)
    result["reason"] = (
        " | ".join(reason_list) if reason_list else "شرایط ورود برقرار نیست."
    )

    if signal in ("LONG", "SHORT"):

        stop_loss, take_profit = _calculate_sl_tp(
            signal=signal,
            price=price,
            atr_value=atr_value
        )

        result["stop_loss"] = stop_loss
        result["take_profit"] = take_profit

    return result


# =========================================================
# حد ضرر / حد سود بر اساس ATR
# =========================================================

def _calculate_sl_tp(signal, price, atr_value):

    sl_multiplier = 1.5
    tp_multiplier = 3.0

    if signal == "LONG":

        stop_loss = price - (atr_value * sl_multiplier)
        take_profit = price + (atr_value * tp_multiplier)

    else:

        stop_loss = price + (atr_value * sl_multiplier)
        take_profit = price - (atr_value * tp_multiplier)

    return round(stop_loss, 6), round(take_profit, 6)
