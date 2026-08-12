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
# SIMULATE MODEL A
#
# SL  = 2 ATR
# TP1 = 2 ATR
# TP2 = 4 ATR
#
# TP1:
# نصف پوزیشن بسته می‌شود
#
# بعد از TP1:
# باقی‌مانده BE
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

                # محافظه کارانه:
                # اگر SL و TP1 در یک کندل باشند،
                # SL اول محسوب می‌شود.

                if hit_sl:

                    return {
                        "result": "SL",
                        "r": -1.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp1:

                    tp1_hit = True

                    # اگر TP2 همان کندل خورده باشد
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
# SIMULATE MODEL B
#
# SL  = 2 ATR
# TP1 = 2 ATR
# TP2 = 4 ATR
#
# TP1:
# نصف پوزیشن بسته می‌شود
#
# بعد از TP1:
# SL باقی‌مانده همان SL اولیه است.
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
# SIMULATE MODEL C
#
# SL = 2 ATR
# TP = 4 ATR
# بدون TP1
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
# STATS
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

    data = pd.DataFrame(
        trades
    )

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

    tp = len(
        data[
            data["result"] == "TP"
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

    wins = (
        tp1 +
        tp2 +
        tp
    )

    completed = (
        wins +
        sl
    )

    win_rate = (
        wins / completed * 100
        if completed > 0
        else 0
    )

    return {
        "trades": len(data),
        "tp2": tp2,
        "tp1": tp1,
        "tp": tp,
        "sl": sl,
        "timeout": timeout,
        "win_rate": win_rate,
        "profit": float(
            data["r"].sum()
        )
    }


# =========================================================
# BACKTEST SYMBOL
# =========================================================

def backtest_symbol(symbol):

    print(
        "\n" + "=" * 65
    )

    print(
        "BACKTEST:",
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

    df = df.reset_index(
        drop=True
    )

    model_trades = {
        "A": [],
        "B": [],
        "C": []
    }

    # =====================================================
    # IMPORTANT
    #
    # یک فرصت ورود
    # سپس معامله تا پایان
    # سپس جستجوی سیگنال بعدی
    # =====================================================

    i = MIN_ANALYSIS_CANDLES

    while i < len(df) - 1:

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
        # هر سه مدل از همین ورود استفاده می‌کنند.
        # =================================================

        trade_a = simulate_model_a(
            df,
            i,
            signal,
            atr
        )

        trade_b = simulate_model_b(
            df,
            i,
            signal,
            atr
        )

        trade_c = simulate_model_c(
            df,
            i,
            signal,
            atr
        )

        if trade_a is not None:

            model_trades["A"].append(
                trade_a
            )

        if trade_b is not None:

            model_trades["B"].append(
                trade_b
            )

        if trade_c is not None:

            model_trades["C"].append(
                trade_c
            )

        # =================================================
        # CRITICAL
        #
        # معامله A را معیار پایان فرصت می‌گیریم.
        # بنابراین ورود بعدی تا پایان معامله قبلی
        # اتفاق نمی‌افتد.
        # =================================================

        if trade_a is not None:

            bars = trade_a.get(
                "bars",
                1
            )

            i += max(
                1,
                bars
            )

        else:

            i += 1

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
                "ERROR:",
                symbol,
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
            d["tp1"] +
            d["tp2"] +
            d["tp"]
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
        "\n" + "=" * 65
    )

    print(
        "✅ COMPARISON FINISHED"
    )

    print(
        "=" * 65
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
