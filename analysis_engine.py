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

    rs = avg_gain / avg_loss.replace(0, np.nan)

    return 100 - (
        100 / (1 + rs)
    )


# =========================================================
# MACD
# =========================================================

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


# =========================================================
# ATR
# =========================================================

def calculate_atr(df, period=14):

    high_low = (
        df["high"] - df["low"]
    )

    high_close = (
        df["high"] - df["close"].shift()
    ).abs()

    low_close = (
        df["low"] - df["close"].shift()
    ).abs()

    true_range = pd.concat(
        [
            high_low,
            high_close,
            low_close
        ],
        axis=1
    ).max(axis=1)

    return true_range.rolling(
        period
    ).mean()


# =========================================================
# تحلیل ساختار بازار
# =========================================================

def calculate_market_structure(df):

    recent = df.tail(20)

    recent_high = recent["high"].max()
    recent_low = recent["low"].min()

    previous_high = (
        df["high"]
        .shift(5)
        .rolling(10)
        .max()
        .iloc[-1]
    )

    previous_low = (
        df["low"]
        .shift(5)
        .rolling(10)
        .min()
        .iloc[-1]
    )

    current_close = df["close"].iloc[-1]

    bullish = False
    bearish = False

    if (
        current_close > recent_high * 0.995
        and recent_high >= previous_high
    ):
        bullish = True

    if (
        current_close < recent_low * 1.005
        and recent_low <= previous_low
    ):
        bearish = True

    return {
        "bullish": bullish,
        "bearish": bearish,
        "recent_high": float(recent_high),
        "recent_low": float(recent_low)
    }


# =========================================================
# تحلیل حجم
# =========================================================

def volume_analysis(df):

    volume_avg = df["volume"].rolling(
        20
    ).mean()

    current_volume = df["volume"].iloc[-1]
    average_volume = volume_avg.iloc[-1]

    if (
        pd.isna(average_volume)
        or average_volume == 0
    ):
        return {
            "confirmed": False,
            "ratio": 0
        }

    ratio = (
        current_volume / average_volume
    )

    return {
        "confirmed": ratio >= 1.10,
        "ratio": float(ratio)
    }


# =========================================================
# تحلیل اصلی
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

    # -----------------------------------------------------
    # اندیکاتورها
    # -----------------------------------------------------

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

    macd, macd_signal, histogram = calculate_macd(
        df
    )

    df["MACD"] = macd
    df["MACD_SIGNAL"] = macd_signal
    df["MACD_HIST"] = histogram

    df["ATR"] = calculate_atr(df)

    df["VOLUME_AVG"] = df["volume"].rolling(
        20
    ).mean()

    # -----------------------------------------------------
    # آخرین اطلاعات
    # -----------------------------------------------------

    last = df.iloc[-1]
    previous = df.iloc[-2]

    price = float(last["close"])

    rsi = float(last["RSI"])

    atr = float(last["ATR"])

    if np.isnan(atr):

        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "rsi": round(rsi, 2),
            "price": price,
            "atr": 0,
            "reason": "ATR معتبر نیست"
        }

    # -----------------------------------------------------
    # امتیازها
    # -----------------------------------------------------

    long_score = 0
    short_score = 0

    long_reasons = []
    short_reasons = []

    # =====================================================
    # 1. روند EMA200
    # =====================================================

    if price > last["EMA200"]:

        long_score += 2

        long_reasons.append(
            "قیمت بالای EMA200"
        )

    elif price < last["EMA200"]:

        short_score += 2

        short_reasons.append(
            "قیمت زیر EMA200"
        )

    # =====================================================
    # 2. EMA20 / EMA50
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
    # 3. شیب EMA20
    # =====================================================

    if last["EMA20"] > previous["EMA20"]:

        long_score += 1

        long_reasons.append(
            "شیب EMA20 صعودی"
        )

    elif last["EMA20"] < previous["EMA20"]:

        short_score += 1

        short_reasons.append(
            "شیب EMA20 نزولی"
        )

    # =====================================================
    # 4. RSI
    # =====================================================

    if 52 <= rsi <= 68:

        long_score += 2

        long_reasons.append(
            f"RSI مناسب LONG ({rsi:.2f})"
        )

    elif 32 <= rsi <= 48:

        short_score += 2

        short_reasons.append(
            f"RSI مناسب SHORT ({rsi:.2f})"
        )

    elif rsi > 70:

        short_score += 1

        short_reasons.append(
            f"RSI در محدوده اشباع خرید ({rsi:.2f})"
        )

    elif rsi < 30:

        long_score += 1

        long_reasons.append(
            f"RSI در محدوده اشباع فروش ({rsi:.2f})"
        )

    # =====================================================
    # 5. MACD
    # =====================================================

    if (
        last["MACD"] > last["MACD_SIGNAL"]
        and
        last["MACD_HIST"] >
        previous["MACD_HIST"]
    ):

        long_score += 2

        long_reasons.append(
            "MACD صعودی و تقویت‌شونده"
        )

    elif (
        last["MACD"] < last["MACD_SIGNAL"]
        and
        last["MACD_HIST"] <
        previous["MACD_HIST"]
    ):

        short_score += 2

        short_reasons.append(
            "MACD نزولی و تقویت‌شونده"
        )

    # =====================================================
    # 6. حجم
    # =====================================================

    volume_info = volume_analysis(df)

    volume_ratio = volume_info["ratio"]

    if volume_info["confirmed"]:

        if long_score > short_score:

            long_score += 1

            long_reasons.append(
                f"حجم تأییدکننده ({volume_ratio:.2f}x)"
            )

        elif short_score > long_score:

            short_score += 1

            short_reasons.append(
                f"حجم تأییدکننده ({volume_ratio:.2f}x)"
            )

    # =====================================================
    # 7. ساختار بازار
    # =====================================================

    structure = calculate_market_structure(df)

    if structure["bullish"]:

        long_score += 2

        long_reasons.append(
            "ساختار بازار صعودی"
        )

    elif structure["bearish"]:

        short_score += 2

        short_reasons.append(
            "ساختار بازار نزولی"
        )

    # =====================================================
    # 8. جلوگیری از ورود در اشباع شدید
    # =====================================================

    if rsi >= 80:

        long_score -= 2

    if rsi <= 20:

        short_score -= 2

    # =====================================================
    # نتیجه اولیه
    # =====================================================

    best_score = max(
        long_score,
        short_score
    )

    difference = abs(
        long_score - short_score
    )

    # =====================================================
    # اطلاعات پایه
    # =====================================================

    result_base = {
        "rsi": round(rsi, 2),
        "price": price,
        "atr": atr,
        "volume_ratio": round(
            volume_ratio,
            2
        ),
        "ema20": float(last["EMA20"]),
        "ema50": float(last["EMA50"]),
        "ema200": float(last["EMA200"]),
        "macd": float(last["MACD"]),
        "macd_signal": float(
            last["MACD_SIGNAL"]
        ),
        "market_high": structure[
            "recent_high"
        ],
        "market_low": structure[
            "recent_low"
        ]
    }

    # =====================================================
    # امتیاز ناکافی
    # =====================================================

    if best_score < 7:

        return {
            **result_base,
            "signal": "NO TRADE",
            "score": best_score,
            "confidence": min(
                100,
                max(
                    0,
                    best_score * 10
                )
            ),
            "reason":
                "امتیاز تحلیل به حد لازم نرسیده"
        }

    # =====================================================
    # تضاد زیاد
    # =====================================================

    if difference < 3:

        return {
            **result_base,
            "signal": "NO TRADE",
            "score": best_score,
            "confidence": min(
                100,
                best_score * 10
            ),
            "reason":
                "تضاد بین شرایط LONG و SHORT"
        }

    # =====================================================
    # LONG
    # =====================================================

    if long_score > short_score:

        stop_loss = price - (
            atr * 2
        )

        tp1 = price + (
            atr * 2
        )

        tp2 = price + (
            atr * 4
        )

        return {
            **result_base,

            "signal": "LONG",

            "score": long_score,

            "confidence": min(
                100,
                long_score * 10
            ),

            "stop_loss":
                stop_loss,

            "take_profit":
                tp2,

            "tp1":
                tp1,

            "tp2":
                tp2,

            "risk_reward":
                2.0,

            "reason":
                " | ".join(
                    long_reasons
                ),

            "analysis": {
                "trend": "BULLISH",
                "momentum": "BULLISH",
                "volume": volume_info[
                    "confirmed"
                ],
                "structure": "BULLISH"
                if structure["bullish"]
                else "NEUTRAL"
            }
        }

    # =====================================================
    # SHORT
    # =====================================================

    if short_score > long_score:

        stop_loss = price + (
            atr * 2
        )

        tp1 = price - (
            atr * 2
        )

        tp2 = price - (
            atr * 4
        )

        return {
            **result_base,

            "signal": "SHORT",

            "score": short_score,

            "confidence": min(
                100,
                short_score * 10
            ),

            "stop_loss":
                stop_loss,

            "take_profit":
                tp2,

            "tp1":
                tp1,

            "tp2":
                tp2,

            "risk_reward":
                2.0,

            "reason":
                " | ".join(
                    short_reasons
                ),

            "analysis": {
                "trend": "BEARISH",
                "momentum": "BEARISH",
                "volume": volume_info[
                    "confirmed"
                ],
                "structure": "BEARISH"
                if structure["bearish"]
                else "NEUTRAL"
            }
        }

    # =====================================================
    # حالت نامشخص
    # =====================================================

    return {
        **result_base,
        "signal": "NO TRADE",
        "score": best_score,
        "confidence": 0,
        "reason": "بازار جهت مشخصی ندارد"
    }


# =========================================================
# تست مستقیم
# =========================================================

if __name__ == "__main__":

    print(
        "Advanced Analysis Engine v2.0 OK"
    )
