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

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
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

    return macd, signal, histogram


# =========================================================
# ATR
# =========================================================

def calculate_atr(df, period=14):

    previous_close = df["close"].shift(1)

    tr1 = df["high"] - df["low"]

    tr2 = (
        df["high"] -
        previous_close
    ).abs()

    tr3 = (
        df["low"] -
        previous_close
    ).abs()

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    return true_range.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()


# =========================================================
# ADX
# =========================================================

def calculate_adx(df, period=14):

    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()

    down_move = -low.diff()

    plus_dm = np.where(
        (up_move > down_move) &
        (up_move > 0),
        up_move,
        0
    )

    minus_dm = np.where(
        (down_move > up_move) &
        (down_move > 0),
        down_move,
        0
    )

    tr1 = high - low

    tr2 = (
        high -
        close.shift(1)
    ).abs()

    tr3 = (
        low -
        close.shift(1)
    ).abs()

    tr = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    atr = tr.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    plus_dm = pd.Series(
        plus_dm,
        index=df.index
    )

    minus_dm = pd.Series(
        minus_dm,
        index=df.index
    )

    plus_di = (
        100 *
        plus_dm.ewm(
            alpha=1 / period,
            adjust=False
        ).mean()
        /
        atr.replace(0, np.nan)
    )

    minus_di = (
        100 *
        minus_dm.ewm(
            alpha=1 / period,
            adjust=False
        ).mean()
        /
        atr.replace(0, np.nan)
    )

    dx = (
        100 *
        (plus_di - minus_di).abs()
        /
        (plus_di + minus_di).replace(
            0,
            np.nan
        )
    )

    return dx.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()


# =========================================================
# ANALYSIS
# =========================================================

def analyze(df):

    if df is None or len(df) < 250:

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

    df["RSI"] = calculate_rsi(
        df
    )

    (
        df["MACD"],
        df["MACD_SIGNAL"],
        df["MACD_HIST"]
    ) = calculate_macd(
        df
    )

    df["ATR"] = calculate_atr(
        df
    )

    df["ADX"] = calculate_adx(
        df
    )

    df["VOLUME_AVG"] = (
        df["volume"]
        .rolling(20)
        .mean()
    )

    # =====================================================
    # Last closed candle
    # =====================================================

    last = df.iloc[-1]
    previous = df.iloc[-2]

    price = float(
        last["close"]
    )

    atr = float(
        last["ATR"]
    )

    rsi = float(
        last["RSI"]
    )

    adx = float(
        last["ADX"]
    )

    if not np.isfinite(atr) or atr <= 0:

        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "reason": "ATR نامعتبر"
        }

    if not np.isfinite(rsi):

        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "reason": "RSI نامعتبر"
        }

    if not np.isfinite(adx):

        return {
            "signal": "NO TRADE",
            "score": 0,
            "confidence": 0,
            "reason": "ADX نامعتبر"
        }

    # =====================================================
    # Scores
    # =====================================================

    long_score = 0
    short_score = 0

    long_reasons = []
    short_reasons = []

    # =====================================================
    # 1. EMA200
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
    # 2. EMA structure
    # =====================================================

    if (
        last["EMA20"] >
        last["EMA50"] >
        last["EMA200"]
    ):

        long_score += 3

        long_reasons.append(
            "ساختار EMA صعودی"
        )

    elif (
        last["EMA20"] <
        last["EMA50"] <
        last["EMA200"]
    ):

        short_score += 3

        short_reasons.append(
            "ساختار EMA نزولی"
        )

    # =====================================================
    # 3. EMA50 slope
    # =====================================================

    ema50_slope = (
        last["EMA50"] -
        df["EMA50"].iloc[-6]
    )

    if ema50_slope > 0:

        long_score += 1

        long_reasons.append(
            "شیب EMA50 صعودی"
        )

    elif ema50_slope < 0:

        short_score += 1

        short_reasons.append(
            "شیب EMA50 نزولی"
        )

    # =====================================================
    # 4. RSI
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

    # =====================================================
    # 5. MACD
    # =====================================================

    macd = float(
        last["MACD"]
    )

    macd_signal = float(
        last["MACD_SIGNAL"]
    )

    histogram = float(
        last["MACD_HIST"]
    )

    previous_hist = float(
        previous["MACD_HIST"]
    )

    if (
        macd > macd_signal
        and
        histogram > 0
        and
        histogram > previous_hist
    ):

        long_score += 2

        long_reasons.append(
            "MACD صعودی"
        )

    elif (
        macd < macd_signal
        and
        histogram < 0
        and
        histogram < previous_hist
    ):

        short_score += 2

        short_reasons.append(
            "MACD نزولی"
        )

    # =====================================================
    # 6. ADX trend filter
    # =====================================================

    if adx < 20:

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
            "reason": "ADX پایین - بازار بدون روند"
        }

    if adx >= 25:

        if long_score > short_score:

            long_score += 1

            long_reasons.append(
                "ADX روند قوی"
            )

        elif short_score > long_score:

            short_score += 1

            short_reasons.append(
                "ADX روند قوی"
            )

    # =====================================================
    # 7. Volume
    # =====================================================

    volume_avg = float(
        last["VOLUME_AVG"]
    )

    if (
        np.isfinite(volume_avg)
        and
        volume_avg > 0
        and
        last["volume"] >
        volume_avg * 1.15
    ):

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

    # =====================================================
    # 8. Price momentum
    # =====================================================

    momentum = (
        price -
        float(df["close"].iloc[-6])
    )

    if momentum > 0:

        long_score += 1

        long_reasons.append(
            "مومنتوم صعودی"
        )

    elif momentum < 0:

        short_score += 1

        short_reasons.append(
            "مومنتوم نزولی"
        )

    # =====================================================
    # Direction
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
    # Strong confirmation
    # =====================================================

    if best_score < 8:

        return {
            "signal": "NO TRADE",
            "score": best_score,
            "confidence": min(
                100,
                best_score * 10
            ),
            "long_score": long_score,
            "short_score": short_score,
            "rsi": round(rsi, 2),
            "price": price,
            "atr": atr,
            "reason": "تأیید کافی نیست"
        }

    if difference < 3:

        return {
            "signal": "NO TRADE",
            "score": best_score,
            "confidence": min(
                100,
                best_score * 10
            ),
            "long_score": long_score,
            "short_score": short_score,
            "rsi": round(rsi, 2),
            "price": price,
            "atr": atr,
            "reason": "اختلاف جهت کافی نیست"
        }

    # =====================================================
    # LONG
    # =====================================================

    if long_score > short_score:

        stop_loss = (
            price -
            atr * 2
        )

        tp1 = (
            price +
            atr * 2
        )

        take_profit = (
            price +
            atr * 4
        )

        return {
            "signal": "LONG",
            "score": long_score,
            "confidence": min(
                100,
                long_score * 10
            ),
            "long_score": long_score,
            "short_score": short_score,
            "rsi": round(rsi, 2),
            "price": price,
            "atr": atr,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "take_profit": take_profit,
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
            atr * 2
        )

        tp1 = (
            price -
            atr * 2
        )

        take_profit = (
            price -
            atr * 4
        )

        return {
            "signal": "SHORT",
            "score": short_score,
            "confidence": min(
                100,
                short_score * 10
            ),
            "long_score": long_score,
            "short_score": short_score,
            "rsi": round(rsi, 2),
            "price": price,
            "atr": atr,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "take_profit": take_profit,
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
        "rsi": round(rsi, 2),
        "price": price,
        "atr": atr,
        "reason": "بازار نامشخص"
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print(
        "Advanced Analysis Engine v3 OK"
    )
