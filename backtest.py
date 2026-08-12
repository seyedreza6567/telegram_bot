import pandas as pd
import numpy as np

from scanner import get_klines
from analysis_engine import analyze


# =========================================================
# SYMBOLS
# =========================================================

SYMBOLS = [
    "BTC-SWAP-USDT",
    "ETH-SWAP-USDT",
    "BNB-SWAP-USDT",
    "SOL-SWAP-USDT",
    "XRP-SWAP-USDT",
    "DOGE-SWAP-USDT",
    "ADA-SWAP-USDT",
    "TRX-SWAP-USDT",
    "AVAX-SWAP-USDT",
    "LINK-SWAP-USDT",
    "DOT-SWAP-USDT",
    "LTC-SWAP-USDT",
    "BCH-SWAP-USDT",
    "UNI-SWAP-USDT",
    "SUI-SWAP-USDT",
]


# =========================================================
# SETTINGS
# =========================================================

TIMEFRAME = "1h"

CANDLE_LIMIT = 1000

MIN_ANALYSIS_CANDLES = 250

SL_ATR = 2.0

TP1_ATR = 2.0

TP2_ATR = 4.0

MAX_HOLD_CANDLES = 100

# هزینه رفت و برگشت معامله
COST_R = 0.05


# =========================================================
# SAFE FLOAT
# =========================================================

def safe_float(value):

    try:

        value = float(value)

        if np.isfinite(value):

            return value

    except Exception:

        pass

    return None


# =========================================================
# SYMBOL NAME
# =========================================================

def symbol_name(symbol):

    return symbol.replace(
        "-SWAP-USDT",
        ""
    )


# =========================================================
# SIMULATE TRADE
# =========================================================

def simulate_trade(
    df,
    entry_index,
    signal,
    atr
):

    entry = safe_float(
        df.iloc[entry_index]["open"]
    )

    if entry is None:

        return None

    if atr is None or atr <= 0:

        return None

    # =====================================================
    # LONG
    # =====================================================

    if signal == "LONG":

        sl = entry - (
            atr * SL_ATR
        )

        tp1 = entry + (
            atr * TP1_ATR
        )

        tp2 = entry + (
            atr * TP2_ATR
        )

    # =====================================================
    # SHORT
    # =====================================================

    elif signal == "SHORT":

        sl = entry + (
            atr * SL_ATR
        )

        tp1 = entry - (
            atr * TP1_ATR
        )

        tp2 = entry - (
            atr * TP2_ATR
        )

    else:

        return None

    # =====================================================
    # نصف پوزیشن در TP1
    # =====================================================

    tp1_hit = False

    # =====================================================
    # حداکثر زمان معامله
    # =====================================================

    last_index = min(
        len(df),
        entry_index + MAX_HOLD_CANDLES + 1
    )

    # =====================================================
    # بررسی کندل‌ها
    # =====================================================

    for j in range(
        entry_index,
        last_index
    ):

        high = safe_float(
            df.iloc[j]["high"]
        )

        low = safe_float(
            df.iloc[j]["low"]
        )

        if high is None or low is None:

            continue

        # =================================================
        # LONG
        # =================================================

        if signal == "LONG":

            # -------------------------------------------------
            # قبل از TP1
            # -------------------------------------------------

            if not tp1_hit:

                hit_sl = low <= sl

                hit_tp1 = high >= tp1

                # اگر SL و TP1 در یک کندل باشند
                # حالت محافظه‌کارانه:
                # SL را اول حساب می‌کنیم.

                if hit_sl and hit_tp1:

                    return {
                        "result": "SL",
                        "r": -1.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_sl:

                    return {
                        "result": "SL",
                        "r": -1.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp1:

                    tp1_hit = True

                    # اگر در همان کندل TP2 هم رسیده باشد
                    # نصف پوزیشن TP1
                    # نصف دیگر TP2

                    if high >= tp2:

                        return {
                            "result": "TP2",
                            "r": 1.5 - COST_R,
                            "bars": j - entry_index + 1
                        }

                    continue

            # -------------------------------------------------
            # بعد از TP1
            # -------------------------------------------------

            else:

                hit_sl_be = low <= entry

                hit_tp2 = high >= tp2

                # اگر بعد از TP1 هم Entry و TP2
                # در یک کندل باشند،
                # محافظه‌کارانه Entry را اول می‌گیریم.

                if hit_sl_be and hit_tp2:

                    return {
                        "result": "TP1",
                        "r": 0.5 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_sl_be:

                    return {
                        "result": "TP1",
                        "r": 0.5 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp2:

                    return {
                        "result": "TP2",
                        "r": 1.5 - COST_R,
                        "bars": j - entry_index + 1
                    }

        # =================================================
        # SHORT
        # =================================================

        elif signal == "SHORT":

            # -------------------------------------------------
            # قبل از TP1
            # -------------------------------------------------

            if not tp1_hit:

                hit_sl = high >= sl

                hit_tp1 = low <= tp1

                if hit_sl and hit_tp1:

                    return {
                        "result": "SL",
                        "r": -1.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_sl:

                    return {
                        "result": "SL",
                        "r": -1.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp1:

                    tp1_hit = True

                    if low <= tp2:

                        return {
                            "result": "TP2",
                            "r": 1.5 - COST_R,
                            "bars": j - entry_index + 1
                        }

                    continue

            # -------------------------------------------------
            # بعد از TP1
            # -------------------------------------------------

            else:

                hit_sl_be = high >= entry

                hit_tp2 = low <= tp2

                if hit_sl_be and hit_tp2:

                    return {
                        "result": "TP1",
                        "r": 0.5 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_sl_be:

                    return {
                        "result": "TP1",
                        "r": 0.5 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp2:

                    return {
                        "result": "TP2",
                        "r": 1.5 - COST_R,
                        "bars": j - entry_index + 1
                    }

    # =====================================================
    # TIMEOUT
    # =====================================================

    return {
        "result": "TIMEOUT",
        "r": 0.0,
        "bars": max(
            1,
            last_index - entry_index
        )
    }


# =========================================================
# BACKTEST SYMBOL
# =========================================================

def backtest_symbol(symbol):

    print("\n" + "=" * 65)

    print(
        "BACKTEST:",
        symbol_name(symbol)
    )

    print("=" * 65)

    df = get_klines(
        symbol=symbol,
        interval=TIMEFRAME,
        limit=CANDLE_LIMIT
    )

    if df is None:

        print("DATA ERROR")

        return None

    if len(df) < MIN_ANALYSIS_CANDLES + 25:

        print(
            "NOT ENOUGH DATA:",
            len(df)
        )

        return None

    df = df.copy()

    df = df.reset_index(
        drop=True
    )

    trades = []

    i = MIN_ANALYSIS_CANDLES

    # =====================================================
    # BACKTEST LOOP
    # =====================================================

    while i < len(df) - 1:

        # =================================================
        # فقط اطلاعات قبل از ورود
        # =================================================

        historical = df.iloc[:i].copy()

        try:

            analysis = analyze(
                historical
            )

        except Exception as e:

            print(
                "ANALYSIS ERROR:",
                e
            )

            i += 1

            continue

        signal = analysis.get(
            "signal",
            "NO TRADE"
        )

        if signal not in [
            "LONG",
            "SHORT"
        ]:

            i += 1

            continue

        atr = safe_float(
            analysis.get("atr")
        )

        if atr is None or atr <= 0:

            i += 1

            continue

        # =================================================
        # ورود روی OPEN کندل بعدی
        # =================================================

        trade = simulate_trade(
            df=df,
            entry_index=i,
            signal=signal,
            atr=atr
        )

        if trade is None:

            i += 1

            continue

        trades.append({

            "signal": signal,

            "result": trade["result"],

            "r": trade["r"],

            "bars": trade["bars"],

            "entry_index": i

        })

        # =================================================
        # نکته مهم:
        #
        # اگر معامله در کندل j تمام شده،
        # معامله بعدی باید از کندل بعدی شروع شود.
        # =================================================

        i = i + max(
            1,
            trade["bars"]
        )

    # =====================================================
    # NO TRADES
    # =====================================================

    if not trades:

        print("NO TRADES")

        return None

    data = pd.DataFrame(
        trades
    )

    # =====================================================
    # RESULTS
    # =====================================================

    tp2 = len(
        data[
            data["result"] == "TP2"
        ]
    )

    tp1 = len(
        data[
            data["result"] == "TP1"
        ]
    )

    sl = len(
        data[
            data["result"] == "SL"
        ]
    )

    timeout = len(
        data[
            data["result"] == "TIMEOUT"
        ]
    )

    long_count = len(
        data[
            data["signal"] == "LONG"
        ]
    )

    short_count = len(
        data[
            data["signal"] == "SHORT"
        ]
    )

    completed = (
        tp1
        + tp2
        + sl
    )

    wins = (
        tp1
        + tp2
    )

    if completed > 0:

        win_rate = (
            wins / completed
        ) * 100

    else:

        win_rate = 0

    total_r = float(
        data["r"].sum()
    )

    # =====================================================
    # PRINT
    # =====================================================

    print(
        "Trades:",
        len(data)
    )

    print(
        "LONG:",
        long_count
    )

    print(
        "SHORT:",
        short_count
    )

    print(
        "TP2:",
        tp2
    )

    print(
        "TP1:",
        tp1
    )

    print(
        "SL:",
        sl
    )

    print(
        "TIMEOUT:",
        timeout
    )

    print(
        "WIN RATE:",
        round(
            win_rate,
            2
        ),
        "%"
    )

    print(
        "PROFIT:",
        round(
            total_r,
            2
        ),
        "R"
    )

    return {

        "symbol": symbol,

        "trades": len(data),

        "long": long_count,

        "short": short_count,

        "tp2": tp2,

        "tp1": tp1,

        "sl": sl,

        "timeout": timeout,

        "win_rate": win_rate,

        "profit": total_r
    }


# =========================================================
# MAIN
# =========================================================

def main():

    print("\n" + "=" * 65)

    print(
        "🚀 FINAL SL/TP BACKTEST"
    )

    print("=" * 65)

    results = []

    for symbol in SYMBOLS:

        try:

            result = backtest_symbol(
                symbol
            )

            if result is not None:

                results.append(
                    result
                )

        except Exception as e:

            print(
                "ERROR:",
                symbol,
                e
            )

    # =====================================================
    # NO RESULTS
    # =====================================================

    if not results:

        print(
            "\nNO RESULTS"
        )

        return

    # =====================================================
    # SORT
    # =====================================================

    results = sorted(
        results,
        key=lambda x: x["profit"],
        reverse=True
    )

    # =====================================================
    # TOTALS
    # =====================================================

    total_trades = sum(
        x["trades"]
        for x in results
    )

    total_tp2 = sum(
        x["tp2"]
        for x in results
    )

    total_tp1 = sum(
        x["tp1"]
        for x in results
    )

    total_sl = sum(
        x["sl"]
        for x in results
    )

    total_timeout = sum(
        x["timeout"]
        for x in results
    )

    total_profit = sum(
        x["profit"]
        for x in results
    )

    completed = (
        total_tp2
        + total_tp1
        + total_sl
    )

    wins = (
        total_tp2
        + total_tp1
    )

    if completed > 0:

        win_rate = (
            wins / completed
        ) * 100

    else:

        win_rate = 0

    # =====================================================
    # FINAL
    # =====================================================

    print("\n" + "=" * 65)

    print(
        "🏆 FINAL RESULT"
    )

    print("=" * 65)

    print(
        "TOTAL TRADES:",
        total_trades
    )

    print(
        "TP2:",
        total_tp2
    )

    print(
        "TP1:",
        total_tp1
    )

    print(
        "SL:",
        total_sl
    )

    print(
        "TIMEOUT:",
        total_timeout
    )

    print(
        "WIN RATE:",
        round(
            win_rate,
            2
        ),
        "%"
    )

    print(
        "TOTAL PROFIT:",
        round(
            total_profit,
            2
        ),
        "R"
    )

    print("\nRANKING")

    for n, result in enumerate(
        results,
        1
    ):

        print(
            n,
            symbol_name(
                result["symbol"]
            ),
            "| Trades:",
            result["trades"],
            "| Win:",
            round(
                result["win_rate"],
                2
            ),
            "%",
            "| Profit:",
            round(
                result["profit"],
                2
            ),
            "R"
        )

    print("\n" + "=" * 65)

    print(
        "✅ BACKTEST FINISHED"
    )

    print("=" * 65)


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
