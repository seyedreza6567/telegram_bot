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
# SL  = -1R
# TP1 = +0.5R
# TP2 = +1.5R
#
# بعد TP1:
# نصف پوزیشن بسته
# نصف باقی مانده BE
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

    if entry is None or atr is None or atr <= 0:
        return None

    if signal == "LONG":

        sl = entry - atr * 2
        tp1 = entry + atr * 2
        tp2 = entry + atr * 4

    elif signal == "SHORT":

        sl = entry + atr * 2
        tp1 = entry - atr * 2
        tp2 = entry - atr * 4

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

            else:

                hit_be = low <= entry
                hit_tp2 = high >= tp2

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
# SL  = -1R
# TP1 = +0.5R
# TP2 = +1.5R
#
# بعد TP1:
# نصف پوزیشن بسته می‌شود
# نصف باقی‌مانده SL اولیه دارد
#
# اگر SL بخورد:
# +0.5R - 0.5R = 0R
#
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

    if entry is None or atr is None or atr <= 0:
        return None

    if signal == "LONG":

        sl = entry - atr * 2
        tp1 = entry + atr * 2
        tp2 = entry + atr * 4

    elif signal == "SHORT":

        sl = entry + atr * 2
        tp1 = entry - atr * 2
        tp2 = entry - atr * 4

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

            else:

                hit_sl = low <= sl
                hit_tp2 = high >= tp2

                if hit_sl:

                    return {
                        "result": "TP1",
                        "r": 0.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp2:

                    return {
                        "result": "TP2",
                        "r": 1.5 - COST_R,
                        "bars": j - entry_index + 1
                    }

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

            else:

                hit_sl = high >= sl
                hit_tp2 = low <= tp2

                if hit_sl:

                    return {
                        "result": "TP1",
                        "r": 0.0 - COST_R,
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

    if entry is None or atr is None or atr <= 0:
        return None

    if signal == "LONG":

        sl = entry - atr * 2
        tp = entry + atr * 4

    elif signal == "SHORT":

        sl = entry + atr * 2
        tp = entry - atr * 4

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

        if signal == "LONG":

            hit_sl = low <= sl
            hit_tp = high >= tp

        else:

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
# STATS
# =========================================================

def calculate_stats(trades):

    stats = {
        "trades": len(trades),
        "tp2": 0,
        "tp1": 0,
        "tp": 0,
        "sl": 0,
        "timeout": 0,
        "profit": 0.0
    }

    for trade in trades:

        result = trade.get(
            "result",
            "TIMEOUT"
        )

        r = safe_float(
            trade.get("r", 0)
        )

        if r is None:
            r = 0.0

        stats["profit"] += r

        if result == "TP2":
            stats["tp2"] += 1

        elif result == "TP1":
            stats["tp1"] += 1

        elif result == "TP":
            stats["tp"] += 1

        elif result == "SL":
            stats["sl"] += 1

        else:
            stats["timeout"] += 1

    wins = (
        stats["tp2"]
        +
        stats["tp1"]
        +
        stats["tp"]
    )

    completed = (
        wins +
        stats["sl"]
    )

    stats["win_rate"] = (
        wins / completed * 100
        if completed > 0
        else 0.0
    )

    return stats


# =========================================================
# GENERATE COMMON ENTRIES
#
# فقط وقتی وارد می‌شویم که سیگنال
# از حالت دیگر به LONG یا SHORT تغییر کند.
#
# بنابراین یک LONG که 20 کندل پشت‌سرهم
# باقی مانده، 20 معامله تولید نمی‌کند.
# =========================================================

def generate_entries(df):

    entries = []

    previous_signal = "NO TRADE"

    for i in range(
        MIN_ANALYSIS_CANDLES,
        len(df) - 1
    ):

        historical = df.iloc[:i].copy()

        try:

            analysis = analyze(
                historical
            )

        except Exception as e:

            print(
                "ANALYSIS ERROR:",
                i,
                e
            )

            continue

        if not isinstance(
            analysis,
            dict
        ):

            continue

        signal = analysis.get(
            "signal",
            "NO TRADE"
        )

        # -----------------------------------------------
        # فقط تغییر وضعیت به LONG / SHORT
        # -----------------------------------------------

        new_long = (
            signal == "LONG"
            and
            previous_signal != "LONG"
        )

        new_short = (
            signal == "SHORT"
            and
            previous_signal != "SHORT"
        )

        if new_long or new_short:

            atr = safe_float(
                analysis.get("atr")
            )

            if atr is not None and atr > 0:

                entries.append({
                    "index": i,
                    "signal": signal,
                    "atr": atr
                })

        previous_signal = signal

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

    df = df.copy().reset_index(
        drop=True
    )

    entries = generate_entries(
        df
    )

    print(
        "COMMON ENTRIES:",
        len(entries)
    )

    model_trades = {
        "A": [],
        "B": [],
        "C": []
    }

    # =====================================================
    # SAME ENTRIES FOR ALL MODELS
    # =====================================================

    for entry in entries:

        index = entry["index"]
        signal = entry["signal"]
        atr = entry["atr"]

        trade_a = simulate_model_a(
            df,
            index,
            signal,
            atr
        )

        trade_b = simulate_model_b(
            df,
            index,
            signal,
            atr
        )

        trade_c = simulate_model_c(
            df,
            index,
            signal,
            atr
        )

        if trade_a is not None:
            model_trades["A"].append(trade_a)

        if trade_b is not None:
            model_trades["B"].append(trade_b)

        if trade_c is not None:
            model_trades["C"].append(trade_c)

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

        model: {
            "trades": 0,
            "tp2": 0,
            "tp1": 0,
            "tp": 0,
            "sl": 0,
            "timeout": 0,
            "profit": 0.0
        }

        for model in [
            "A",
            "B",
            "C"
        ]
    }

    # =====================================================
    # SYMBOLS
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
    # FINAL
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
            d["tp2"]
            +
            d["tp1"]
            +
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

        if model == "A":

            expected = (
                d["tp2"] * (1.5 - COST_R)
                +
                d["tp1"] * (0.5 - COST_R)
                +
                d["sl"] * (-1.0 - COST_R)
            )

        elif model == "B":

            expected = (
                d["tp2"] * (1.5 - COST_R)
                +
                d["tp1"] * (0.0 - COST_R)
                +
                d["sl"] * (-1.0 - COST_R)
            )

        else:

            expected = (
                d["tp"] * (2.0 - COST_R)
                +
                d["sl"] * (-1.0 - COST_R)
            )

        difference = (
            d["profit"] -
            expected
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
                expected,
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
    # CONSISTENCY
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

    a = totals["A"]["trades"]
    b = totals["B"]["trades"]
    c = totals["C"]["trades"]

    if a == b == c:

        print(
            "ENTRY COUNT: OK"
        )

        print(
            "COMMON TRADES:",
            a
        )

    else:

        print(
            "ENTRY COUNT: ERROR"
        )

        print(
            "A:",
            a
        )

        print(
            "B:",
            b
        )

        print(
            "C:",
            c
        )

    # =====================================================
    # SUMMARY
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
            f"MODEL {model}:"
            f"{totals[model]['profit']:.2f}"
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
