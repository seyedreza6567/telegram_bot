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

MAX_HOLD_CANDLES = 100

# هزینه رفت و برگشت معامله بر حسب R
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
# MODEL A
#
# SL = 2 ATR
# TP1 = 2 ATR
# TP2 = 4 ATR
#
# بعد TP1:
# نصف پوزیشن بسته می‌شود
# نصف باقی‌مانده BE
#
# SL  = -1R
# TP1 = +0.5R
# TP2 = +1.5R
# =========================================================

def simulate_model_a(
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

    if signal == "LONG":

        sl = entry - atr * 2.0
        tp1 = entry + atr * 2.0
        tp2 = entry + atr * 4.0

    elif signal == "SHORT":

        sl = entry + atr * 2.0
        tp1 = entry - atr * 2.0
        tp2 = entry - atr * 4.0

    else:

        return None

    tp1_hit = False

    last_index = min(
        len(df),
        entry_index + MAX_HOLD_CANDLES + 1
    )

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

            if not tp1_hit:

                hit_sl = low <= sl
                hit_tp1 = high >= tp1

                # اگر SL و TP1 در یک کندل باشند
                # SL اول در نظر گرفته می‌شود.

                if hit_sl:

                    return {
                        "result": "SL",
                        "r": -1.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp1:

                    tp1_hit = True

                    # اگر TP2 هم در همان کندل لمس شود
                    if high >= tp2:

                        return {
                            "result": "TP2",
                            "r": 1.5 - COST_R,
                            "bars": j - entry_index + 1
                        }

                    continue

            else:

                hit_be = low <= entry
                hit_tp2 = high >= tp2

                # اگر BE و TP2 در یک کندل باشند
                # BE اول در نظر گرفته می‌شود.

                if hit_be:

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

            if not tp1_hit:

                hit_sl = high >= sl
                hit_tp1 = low <= tp1

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

            else:

                hit_be = high >= entry
                hit_tp2 = low <= tp2

                if hit_be:

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

    return {
        "result": "TIMEOUT",
        "r": 0.0,
        "bars": max(
            1,
            last_index - entry_index
        )
    }


# =========================================================
# MODEL B
#
# SL = 2 ATR
# TP1 = 2 ATR
# TP2 = 4 ATR
#
# بعد TP1:
# نصف پوزیشن بسته می‌شود
# نصف باقی‌مانده SL اولیه را حفظ می‌کند
#
# TP1 = +0.5R
# سپس SL = -0.5R مجموع
# TP2 = +1.5R
# =========================================================

def simulate_model_b(
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

    if signal == "LONG":

        sl = entry - atr * 2.0
        tp1 = entry + atr * 2.0
        tp2 = entry + atr * 4.0

    elif signal == "SHORT":

        sl = entry + atr * 2.0
        tp1 = entry - atr * 2.0
        tp2 = entry - atr * 4.0

    else:

        return None

    tp1_hit = False

    last_index = min(
        len(df),
        entry_index + MAX_HOLD_CANDLES + 1
    )

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

            if not tp1_hit:

                hit_sl = low <= sl
                hit_tp1 = high >= tp1

                if hit_sl:

                    return {
                        "result": "SL",
                        "r": -1.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp1:

                    tp1_hit = True

                    if high >= tp2:

                        return {
                            "result": "TP2",
                            "r": 1.5 - COST_R,
                            "bars": j - entry_index + 1
                        }

                    continue

            else:

                hit_sl = low <= sl
                hit_tp2 = high >= tp2

                if hit_sl:

                    return {
                        "result": "TP1",
                        "r": -0.5 - COST_R,
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

            if not tp1_hit:

                hit_sl = high >= sl
                hit_tp1 = low <= tp1

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

            else:

                hit_sl = high >= sl
                hit_tp2 = low <= tp2

                if hit_sl:

                    return {
                        "result": "TP1",
                        "r": -0.5 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp2:

                    return {
                        "result": "TP2",
                        "r": 1.5 - COST_R,
                        "bars": j - entry_index + 1
                    }

    return {
        "result": "TIMEOUT",
        "r": 0.0,
        "bars": max(
            1,
            last_index - entry_index
        )
    }


# =========================================================
# MODEL C
#
# SL = 2 ATR
# TP = 4 ATR
#
# بدون TP1
#
# SL = -1R
# TP = +2R
# =========================================================

def simulate_model_c(
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

    if signal == "LONG":

        sl = entry - atr * 2.0
        tp = entry + atr * 4.0

    elif signal == "SHORT":

        sl = entry + atr * 2.0
        tp = entry - atr * 4.0

    else:

        return None

    last_index = min(
        len(df),
        entry_index + MAX_HOLD_CANDLES + 1
    )

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

            hit_sl = low <= sl
            hit_tp = high >= tp

            if hit_sl:

                return {
                    "result": "SL",
                    "r": -1.0 - COST_R,
                    "bars": j - entry_index + 1
                }

            if hit_tp:

                return {
                    "result": "TP",
                    "r": 2.0 - COST_R,
                    "bars": j - entry_index + 1
                }

        # =================================================
        # SHORT
        # =================================================

        elif signal == "SHORT":

            hit_sl = high >= sl
            hit_tp = low <= tp

            if hit_sl:

                return {
                    "result": "SL",
                    "r": -1.0 - COST_R,
                    "bars": j - entry_index + 1
                }

            if hit_tp:

                return {
                    "result": "TP",
                    "r": 2.0 - COST_R,
                    "bars": j - entry_index + 1
                }

    return {
        "result": "TIMEOUT",
        "r": 0.0,
        "bars": max(
            1,
            last_index - entry_index
        )
    }


# =========================================================
# CALCULATE STATS
# =========================================================

def calculate_stats(trades):

    if not trades:

        return {
            "trades": 0,
            "tp2": 0,
            "tp1": 0,
            "tp": 0,
            "sl": 0,
            "timeout": 0,
            "win_rate": 0.0,
            "profit": 0.0
        }

    total_profit = 0.0

    tp2 = 0
    tp1 = 0
    tp = 0
    sl = 0
    timeout = 0

    for trade in trades:

        result = trade.get(
            "result",
            "TIMEOUT"
        )

        r = safe_float(
            trade.get(
                "r",
                0.0
            )
        )

        if r is None:
            r = 0.0

        total_profit += r

        if result == "TP2":

            tp2 += 1

        elif result == "TP1":

            tp1 += 1

        elif result == "TP":

            tp += 1

        elif result == "SL":

            sl += 1

        elif result == "TIMEOUT":

            timeout += 1

    total_trades = len(trades)

    wins = (
        tp2 +
        tp1 +
        tp
    )

    completed = (
        wins +
        sl
    )

    win_rate = (
        wins / completed * 100
        if completed > 0
        else 0.0
    )

    return {
        "trades": total_trades,
        "tp2": tp2,
        "tp1": tp1,
        "tp": tp,
        "sl": sl,
        "timeout": timeout,
        "win_rate": win_rate,
        "profit": total_profit
    }


# =========================================================
# GENERATE COMMON ENTRIES
#
# مهم:
# این تابع فقط Entry ها را پیدا می‌کند.
#
# هیچ مدل خروجی در این مرحله دخالت ندارد.
# =========================================================

def generate_entries(df):

    entries = []

    i = MIN_ANALYSIS_CANDLES

    while i < len(df) - 1:

        historical = df.iloc[:i].copy()

        try:

            analysis = analyze(
                historical
            )

        except Exception as e:

            print(
                "ANALYSIS ERROR AT:",
                i,
                "|",
                e
            )

            i += 1
            continue

        if not isinstance(
            analysis,
            dict
        ):

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

        entries.append({
            "index": i,
            "signal": signal,
            "atr": atr
        })

        # هر کندل فقط یک بار بررسی می‌شود.
        i += 1

    return entries


# =========================================================
# BACKTEST SYMBOL
# =========================================================

def backtest_symbol(symbol):

    print(
        "\n" + "=" * 65
    )

    print(
        "BACKTEST COMPARE:",
        symbol_name(symbol)
    )

    print(
        "=" * 65
    )

    df = get_klines(
        symbol=symbol,
        interval=TIMEFRAME,
        limit=CANDLE_LIMIT
    )

    if df is None:

        print(
            "DATA ERROR"
        )

        return None

    if len(df) < (
        MIN_ANALYSIS_CANDLES + 25
    ):

        print(
            "NOT ENOUGH DATA:",
            len(df)
        )

        return None

    df = df.copy()

    df = df.reset_index(
        drop=True
    )

    # =====================================================
    # COMMON ENTRIES
    # =====================================================

    entries = generate_entries(
        df
    )

    print(
        "COMMON ENTRIES:",
        len(entries)
    )

    if not entries:

        return {
            "A": calculate_stats([]),
            "B": calculate_stats([]),
            "C": calculate_stats([])
        }

    model_trades = {
        "A": [],
        "B": [],
        "C": []
    }

    # =====================================================
    # SAME ENTRIES FOR ALL MODELS
    # =====================================================

    for entry in entries:

        entry_index = entry["index"]
        signal = entry["signal"]
        atr = entry["atr"]

        # =================================================
        # MODEL A
        # =================================================

        trade_a = simulate_model_a(
            df,
            entry_index,
            signal,
            atr
        )

        if trade_a is not None:

            model_trades["A"].append(
                trade_a
            )

        # =================================================
        # MODEL B
        # =================================================

        trade_b = simulate_model_b(
            df,
            entry_index,
            signal,
            atr
        )

        if trade_b is not None:

            model_trades["B"].append(
                trade_b
            )

        # =================================================
        # MODEL C
        # =================================================

        trade_c = simulate_model_c(
            df,
            entry_index,
            signal,
            atr
        )

        if trade_c is not None:

            model_trades["C"].append(
                trade_c
            )

    # =====================================================
    # STATS
    # =====================================================

    return {
        "A": calculate_stats(
            model_trades["A"]
        ),

        "B": calculate_stats(
            model_trades["B"]
        ),

        "C": calculate_stats(
            model_trades["C"]
        )
    }


# =========================================================
# MAIN
# =========================================================

def main():

    totals = {

        "A": {
            "trades": 0,
            "tp2": 0,
            "tp1": 0,
            "tp": 0,
            "sl": 0,
            "timeout": 0,
            "profit": 0.0
        },

        "B": {
            "trades": 0,
            "tp2": 0,
            "tp1": 0,
            "tp": 0,
            "sl": 0,
            "timeout": 0,
            "profit": 0.0
        },

        "C": {
            "trades": 0,
            "tp2": 0,
            "tp1": 0,
            "tp": 0,
            "sl": 0,
            "timeout": 0,
            "profit": 0.0
        }
    }

    # =====================================================
    # SYMBOL LOOP
    # =====================================================

    for symbol in SYMBOLS:

        try:

            result = backtest_symbol(
                symbol
            )

            if result is None:
                continue

            for model in [
                "A",
                "B",
                "C"
            ]:

                for key in [
                    "trades",
                    "tp2",
                    "tp1",
                    "tp",
                    "sl",
                    "timeout"
                ]:

                    totals[model][key] += (
                        result[model][key]
                    )

                totals[model]["profit"] += (
                    result[model]["profit"]
                )

        except Exception as e:

            print(
                "\nERROR:",
                symbol,
                "|",
                e
            )

    # =====================================================
    # FINAL RESULT
    # =====================================================

    print(
        "\n" + "=" * 65
    )

    print(
        "🏆 FINAL EXIT COMPARISON"
    )

    print(
        "=" * 65
    )

    for model in [
        "A",
        "B",
        "C"
    ]:

        d = totals[model]

        wins = (
            d["tp2"] +
            d["tp1"] +
            d["tp"]
        )

        completed = (
            wins +
            d["sl"]
        )

        win_rate = (
            wins / completed * 100
            if completed > 0
            else 0.0
        )

        # =================================================
        # EXPECTED PROFIT
        # =================================================

        if model == "A":

            expected_profit = (
                d["tp2"] * (1.5 - COST_R)
                +
                d["tp1"] * (0.5 - COST_R)
                +
                d["sl"] * (-1.0 - COST_R)
            )

        elif model == "B":

            expected_profit = (
                d["tp2"] * (1.5 - COST_R)
                +
                d["tp1"] * (-0.5 - COST_R)
                +
                d["sl"] * (-1.0 - COST_R)
            )

        else:

            expected_profit = (
                d["tp"] * (2.0 - COST_R)
                +
                d["sl"] * (-1.0 - COST_R)
            )

        difference = (
            d["profit"] -
            expected_profit
        )

        print(
            "\nMODEL",
            model
        )

        print(
            "Trades:",
            d["trades"]
        )

        print(
            "TP2:",
            d["tp2"]
        )

        print(
            "TP1:",
            d["tp1"]
        )

        print(
            "TP:",
            d["tp"]
        )

        print(
            "SL:",
            d["sl"]
        )

        print(
            "TIMEOUT:",
            d["timeout"]
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
                d["profit"],
                2
            ),
            "R"
        )

        print(
            "EXPECTED:",
            round(
                expected_profit,
                2
            ),
            "R"
        )

        print(
            "CHECK DIFFERENCE:",
            round(
                difference,
                4
            ),
            "R"
        )

    # =====================================================
    # FINAL CONSISTENCY CHECK
    # =====================================================

    print(
        "\n" + "=" * 65
    )

    print(
        "FINAL CONSISTENCY CHECK"
    )

    print(
        "=" * 65
    )

    a_trades = totals["A"]["trades"]
    b_trades = totals["B"]["trades"]
    c_trades = totals["C"]["trades"]

    if (
        a_trades
        ==
        b_trades
        ==
        c_trades
    ):

        print(
            "ENTRY COUNT: OK"
        )

        print(
            "COMMON TRADES:",
            a_trades
        )

    else:

        print(
            "ENTRY COUNT: ERROR"
        )

        print(
            "A:",
            a_trades
        )

        print(
            "B:",
            b_trades
        )

        print(
            "C:",
            c_trades
        )

    # =====================================================
    # FINAL SUMMARY
    # =====================================================

    print(
        "\n" + "=" * 65
    )

    print(
        "FINAL PROFIT SUMMARY"
    )

    print(
        "=" * 65
    )

    for model in [
        "A",
        "B",
        "C"
    ]:

        print(
            "MODEL",
            model,
            "=>",
            round(
                totals[model]["profit"],
                2
            ),
            "R"
        )

    print(
        "\n" + "=" * 65
    )

    print(
        "✅ BACKTEST COMPARE FINISHED"
    )

    print(
        "=" * 65
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
