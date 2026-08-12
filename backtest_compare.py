import pandas as pd
import numpy as np

from scanner import get_klines
from analysis_engine import analyze


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

TIMEFRAME = "1h"
CANDLE_LIMIT = 1000
MIN_ANALYSIS_CANDLES = 250
MAX_HOLD_CANDLES = 100
COST_R = 0.05


def safe_float(value):

    try:
        value = float(value)

        if np.isfinite(value):
            return value

    except Exception:
        pass

    return None


def symbol_name(symbol):

    return symbol.replace(
        "-SWAP-USDT",
        ""
    )


# =========================================================
# SIMULATE
# =========================================================

def simulate_trade(
    df,
    entry_index,
    signal,
    atr,
    model
):

    entry = safe_float(
        df.iloc[entry_index]["open"]
    )

    if entry is None or atr is None or atr <= 0:
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

            # -------------------------------------------------
            # BEFORE TP1
            # -------------------------------------------------

            if not tp1_hit:

                hit_sl = low <= sl
                hit_tp1 = high >= tp1

                # محافظه کارانه:
                # اگر SL و TP1 داخل یک کندل هر دو دیده شوند
                # SL را اول در نظر می‌گیریم.

                if hit_sl:

                    return {
                        "result": "SL",
                        "r": -1.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp1:

                    # =================================================
                    # MODEL C
                    # =================================================

                    if model == "C":

                        # C اصلاً TP1 ندارد
                        pass

                    else:

                        tp1_hit = True

                        # اگر TP2 همان کندل خورده باشد
                        if high >= tp2:

                            return {
                                "result": "TP2",
                                "r": 1.5 - COST_R,
                                "bars": j - entry_index + 1
                            }

                        continue

            # =================================================
            # MODEL C
            # =================================================

            if model == "C":

                if high >= tp2:

                    return {
                        "result": "TP2",
                        "r": 2.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

            # =================================================
            # AFTER TP1
            # =================================================

            elif tp1_hit:

                # -------------------------------------------------
                # MODEL A
                # TP1 -> BE
                # -------------------------------------------------

                if model == "A":

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

                # -------------------------------------------------
                # MODEL B
                # TP1 -> SL اولیه
                # -------------------------------------------------

                elif model == "B":

                    hit_sl = low <= sl
                    hit_tp2 = high >= tp2

                    if hit_sl and hit_tp2:

                        return {
                            "result": "TP1",
                            "r": -0.5 - COST_R,
                            "bars": j - entry_index + 1
                        }

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

            # -------------------------------------------------
            # BEFORE TP1
            # -------------------------------------------------

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

                    if model == "C":

                        pass

                    else:

                        tp1_hit = True

                        if low <= tp2:

                            return {
                                "result": "TP2",
                                "r": 1.5 - COST_R,
                                "bars": j - entry_index + 1
                            }

                        continue

            # =================================================
            # MODEL C
            # =================================================

            if model == "C":

                if low <= tp2:

                    return {
                        "result": "TP2",
                        "r": 2.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

            # =================================================
            # AFTER TP1
            # =================================================

            elif tp1_hit:

                # -------------------------------------------------
                # MODEL A
                # -------------------------------------------------

                if model == "A":

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

                # -------------------------------------------------
                # MODEL B
                # -------------------------------------------------

                elif model == "B":

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
# STATS
# =========================================================

def stats(trades):

    if not trades:

        return {
            "trades": 0,
            "tp2": 0,
            "tp1": 0,
            "sl": 0,
            "timeout": 0,
            "win_rate": 0,
            "profit": 0
        }

    data = pd.DataFrame(trades)

    tp2 = len(
        data[data["result"] == "TP2"]
    )

    tp1 = len(
        data[data["result"] == "TP1"]
    )

    sl = len(
        data[data["result"] == "SL"]
    )

    timeout = len(
        data[data["result"] == "TIMEOUT"]
    )

    wins = tp1 + tp2

    completed = wins + sl

    win_rate = (
        wins / completed * 100
        if completed > 0
        else 0
    )

    profit = float(
        data["r"].sum()
    )

    return {
        "trades": len(data),
        "tp2": tp2,
        "tp1": tp1,
        "sl": sl,
        "timeout": timeout,
        "win_rate": win_rate,
        "profit": profit
    }


# =========================================================
# ONE SYMBOL
# =========================================================

def backtest_symbol(symbol):

    print(
        "\n" + "=" * 60
    )

    print(
        "TEST:",
        symbol_name(symbol)
    )

    print(
        "=" * 60
    )

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

    df = df.reset_index(
        drop=True
    )

    signals = []

    for i in range(
        MIN_ANALYSIS_CANDLES,
        len(df) - 1
    ):

        historical = df.iloc[:i].copy()

        try:

            result = analyze(
                historical
            )

        except Exception:

            continue

        signal = result.get(
            "signal",
            "NO TRADE"
        )

        if signal not in [
            "LONG",
            "SHORT"
        ]:

            continue

        atr = safe_float(
            result.get("atr")
        )

        if atr is None or atr <= 0:

            continue

        signals.append({
            "entry_index": i,
            "signal": signal,
            "atr": atr
        })

    if not signals:

        return None

    all_trades = {
        "A": [],
        "B": [],
        "C": []
    }

    for item in signals:

        for model in [
            "A",
            "B",
            "C"
        ]:

            trade = simulate_trade(
                df,
                item["entry_index"],
                item["signal"],
                item["atr"],
                model
            )

            if trade:

                all_trades[model].append(
                    trade
                )

    result = {}

    for model in [
        "A",
        "B",
        "C"
    ]:

        result[model] = stats(
            all_trades[model]
        )

    return result


# =========================================================
# MAIN
# =========================================================

def main():

    totals = {

        "A": {
            "trades": 0,
            "tp2": 0,
            "tp1": 0,
            "sl": 0,
            "timeout": 0,
            "profit": 0.0
        },

        "B": {
            "trades": 0,
            "tp2": 0,
            "tp1": 0,
            "sl": 0,
            "timeout": 0,
            "profit": 0.0
        },

        "C": {
            "trades": 0,
            "tp2": 0,
            "tp1": 0,
            "sl": 0,
            "timeout": 0,
            "profit": 0.0
        }
    }

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
                "ERROR:",
                symbol,
                e
            )

    print(
        "\n" + "=" * 60
    )

    print(
        "FINAL EXIT COMPARISON"
    )

    print(
        "=" * 60
    )

    for model in [
        "A",
        "B",
        "C"
    ]:

        d = totals[model]

        wins = (
            d["tp1"] +
            d["tp2"]
        )

        completed = (
            wins +
            d["sl"]
        )

        win_rate = (
            wins / completed * 100
            if completed > 0
            else 0
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
        "\n" + "=" * 60
    )

    print(
        "TEST FINISHED"
    )

    print(
        "=" * 60
    )


if __name__ == "__main__":

    main()
