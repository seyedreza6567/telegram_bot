import pandas as pd
import numpy as np


def calculate_ema(series, period):
    return series.ewm(
        span=period,
        adjust=False
    ).mean()


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


def calculate_macd(series):

    ema12 = calculate_ema(
        series,
        12
    )

    ema26 = calculate_ema(
        series,
        26
    )

    macd = ema12 - ema26

    signal = calculate_ema(
        macd,
        9
    )

    histogram = macd - signal

    return macd, signal, histogram


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

    last = df.iloc[-1]
    previous = df.iloc[-2]
    previous5 = df.iloc[-6]

    price = float(
        last["close"]
    )

    ema20 = float(
        last["ema20"]
    )

    ema50 = float(
        last["ema50"]
    )

    ema200 = float(
        last["ema200"]
    )

    rsi = float(
        last["rsi"]
    )

    atr = float(
        last["atr"]
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

    else:

        long_score = 0

    if (
        ema20 > ema50
        and
        ema50 > ema200
    ):

        long_score += 2

        long_reasons.append(
            "روند صعودی EMA"
        )

    if (
        ema20 >
        float(previous["ema20"])
    ):

        long_score += 1

        long_reasons.append(
            "EMA20 صعودی"
        )

    if (
        ema50 >
        float(previous["ema50"])
    ):

        long_score += 1

        long_reasons.append(
            "EMA50 صعودی"
        )

    if 52 <= rsi <= 65:

        long_score += 2

        long_reasons.append(
            "RSI مناسب LONG"
        )

    if (
        float(last["macd"])
        >
        float(last["macd_signal"])
        and
        float(last["macd_hist"]) > 0
    ):

        long_score += 2

        long_reasons.append(
            "MACD صعودی"
        )

    if (
        float(last["macd_hist"])
        >
        float(previous["macd_hist"])
    ):

        long_score += 1

        long_reasons.append(
            "قدرت MACD در حال افزایش"
        )

    momentum = (
        price -
        float(previous5["close"])
    ) / float(previous5["close"])

    if momentum > 0:

        long_score += 1

        long_reasons.append(
            "مومنتوم مثبت"
        )

    # =====================================================
    # SHORT
    # فعلاً بسیار سخت‌گیرانه
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

        short_score += 2

        short_reasons.append(
            "روند نزولی EMA"
        )

    if (
        ema20 <
        float(previous["ema20"])
    ):

        short_score += 1

    if (
        ema50 <
        float(previous["ema50"])
    ):

        short_score += 1

    if 35 <= rsi <= 48:

        short_score += 2

    if (
        float(last["macd"])
        <
        float(last["macd_signal"])
        and
        float(last["macd_hist"]) < 0
    ):

        short_score += 2

    if momentum < 0:

        short_score += 1

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
    # فقط LONG با کیفیت بالا
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
                long_score * 10
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
    # SHORT فقط در روند کاملاً نزولی
    # =====================================================

    if (
        short_score >= 9
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
                short_score * 10
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


if __name__ == "__main__":

    print(
        "Analysis Engine FINAL TEST OK"
    )
