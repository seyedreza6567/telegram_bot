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
# TRADE SIMULATION
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

    if entry is None:
        return None

    if atr is None or atr <= 0:
        return None

    # =====================================================
    # MODEL SETTINGS
    # =====================================================

    # MODEL A
    # همان مدل فعلی
    #
    # SL = 2 ATR
    # TP1 = 2 ATR
    # TP2 = 4 ATR
    # نصف موقعیت TP1
    # نصف موقعیت TP2
    # بعد از TP1 -> BE

    if model == "A":

        sl_atr = 2.0
        tp1_atr = 2.0
        tp2_atr = 4.0

        tp1_r = 0.5
        tp2_r = 1.5

    # =====================================================
    # MODEL B
    #
    # SL = 2 ATR
    # TP1 = 2 ATR
    # TP2 = 4 ATR
    #
    # بعد از TP1:
    # نصف موقعیت در TP1
    # نصف باقی‌مانده در TP2
    #
    # اما BE واقعی:
    # اگر TP1 خورد و بعد برگشت،
    # بخش باقی‌مانده صفر می‌شود.
    #
    # این مدل برای مقایسه با مدل فعلی
    # از نظر محاسبه پوزیشن است.
    # =====================================================

    elif model == "B":

        sl_atr = 2.0
        tp1_atr = 2.0
        tp2_atr = 4.0

        tp1_r = 0.5
        tp2_r = 1.5

    # =====================================================
    # MODEL C
    #
    # بدون TP1
    #
    # SL = 2 ATR
    # TP = 4 ATR
    # =====================================================

    elif model == "C":

        sl_atr = 2.0
        tp1_atr = None
        tp2_atr = 4.0

        tp1_r = None
        tp2_r = 2.0

    else:

        return None

    # =====================================================
    # LEVELS
    # =====================================================

    if signal == "LONG":

        sl = entry - (
            atr * sl_atr
        )

        if tp1_atr is not None:

            tp1 = entry + (
                atr * tp1_atr
            )

        else:

            tp1 = None

        tp2 = entry + (
            atr * tp2_atr
        )

    elif signal == "SHORT":

        sl = entry + (
            atr * sl_atr
        )

        if tp1_atr is not None:

            tp1 = entry - (
                atr * tp1_atr
            )

        else:

            tp1 = None

        tp2 = entry - (
            atr * tp2_atr
        )

    else:

        return None

    tp1_hit = False

    last_index = min(
        len(df),
        entry_index +
        MAX_HOLD_CANDLES +
        1
    )

    # =====================================================
    # CANDLE LOOP
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
            # MODEL C
            # -------------------------------------------------

            if model == "C":

                hit_sl = low <= sl

                hit_tp = high >= tp2

                if hit_sl and hit_tp:

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

                if hit_tp:

                    return {
                        "result": "TP",
                        "r": 2.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

                continue

            # -------------------------------------------------
            # MODEL A / B
            # -------------------------------------------------

            if not tp1_hit:

                hit_sl = low <= sl

                hit_tp1 = high >= tp1

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

                    # اگر TP2 در همان کندل نیز دیده شود
                    if high >= tp2:

                        return {
                            "result": "TP2",
                            "r": tp2_r - COST_R,
                            "bars": j - entry_index + 1
                        }

                    continue

            else:

                hit_be = low <= entry

                hit_tp2 = high >= tp2

                if hit_be and hit_tp2:

                    return {
                        "result": "TP1",
                        "r": tp1_r - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_be:

                    return {
                        "result": "TP1",
                        "r": tp1_r - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp2:

                    return {
                        "result": "TP2",
                        "r": tp2_r - COST_R,
                        "bars": j - entry_index + 1
                    }

        # =====================================================
        # SHORT
        # =====================================================

        elif signal == "SHORT":

            # -------------------------------------------------
            # MODEL C
            # -------------------------------------------------

            if model == "C":

                hit_sl = high >= sl

                hit_tp = low <= tp2

                if hit_sl and hit_tp:

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

                if hit_tp:

                    return {
                        "result": "TP",
                        "r": 2.0 - COST_R,
                        "bars": j - entry_index + 1
                    }

                continue

            # -------------------------------------------------
            # MODEL A / B
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
                            "r": tp2_r - COST_R,
                            "bars": j - entry_index + 1
                        }

                    continue

            else:

                hit_be = high >= entry

                hit_tp2 = low <= tp2

                if hit_be and hit_tp2:

                    return {
                        "result": "TP1",
                        "r": tp1_r - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_be:

                    return {
                        "result": "TP1",
                        "r": tp1_r - COST_R,
                        "bars": j - entry_index + 1
                    }

                if hit_tp2:

                    return {
                        "result": "TP2",
                        "r": tp2_r - COST_R,
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
# CALCULATE MODEL STATS
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

    profit = float(
        data["r"].sum()
    )

    return {
        "trades": len(data),
        "tp2": tp2,
        "tp1": tp1,
        "tp": tp,
        "sl": sl,
        "timeout": timeout,
        "win_rate": win_rate,
        "profit": profit
    }


# =========================================================
# BACKTEST ONE SYMBOL
# =========================================================

def backtest_symbol(symbol):

    print(
        "\n" + "=" * 65
    )

    print(
        "COMPARE:",
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
    # IMPORTANT
    # فقط یک بار سیگنال‌ها تولید می‌شوند
    # =====================================================

    signals = []

    i = MIN_ANALYSIS_CANDLES

    while i < len(df) - 1:

        historical = df.iloc[:i].copy()

        try:

            analysis = analyze(
                historical
            )

        except Exception:

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

        # -------------------------------------------------
        # این سیگنال ثابت است و هر سه مدل
        # دقیقاً از همین استفاده می‌کنند.
        # -------------------------------------------------

        signals.append({

            "entry_index": i,

            "signal": signal,

            "atr": atr

        })

        # برای جلوگیری از معاملات هم‌پوشان
        # از مدل A برای تعیین زمان سیگنال بعدی استفاده
        # نمی‌کنیم؛ فقط یک کندل جلو می‌رویم.
        #
        # بنابراین تمام سیگنال‌ها ثبت می‌شوند.
        # -------------------------------------------------

        i += 1

    if not signals:

        print(
            "NO SIGNALS"
        )

        return None

    # =====================================================
    # RUN THREE MODELS
    # =====================================================

    model_trades = {
        "A": [],
        "B": [],
        "C": []
    }

    for signal_data in signals:

        entry_index = signal_data[
            "entry_index"
        ]

        signal = signal_data[
            "signal"
        ]

        atr = signal_data[
            "atr"
        ]

        for model in [
            "A",
            "B",
            "C"
        ]:

            trade = simulate_trade(
                df=df,
                entry_index=entry_index,
                signal=signal,
                atr=atr,
                model=model
            )

            if trade is not None:

                model_trades[
                    model
                ].append({

                    "signal": signal,

                    "result": trade["result"],

                    "r": trade["r"],

                    "bars": trade["bars"],

                    "entry_index": entry_index

                })

    # =====================================================
    # STATS
    # =====================================================

    stats = {}

    for model in [
        "A",
        "B",
        "C"
    ]:

        stats[model] = calculate_stats(
            model_trades[model]
        )

    return stats


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "\n" + "=" * 65
    )

    print(
        "🚀 EXIT MODEL COMPARISON"
    )

    print(
        "=" * 65
    )

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

    symbol_results = []

    for symbol in SYMBOLS:

        try:

            result = backtest_symbol(
                symbol
            )

            if result is None:

                continue

            symbol_results.append(
                (
                    symbol,
                    result
                )
            )

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
    # FINAL RESULTS
    # =====================================================

    print(
        "\n\n" + "=" * 65
    )

    print(
        "🏆 FINAL COMPARISON"
    )

    print(
        "=" * 65
    )

    for model in [
        "A",
        "B",
        "C"
    ]:

        data = totals[model]

        wins = (
            data["tp2"] +
            data["tp1"] +
            data["tp"]
        )

        completed = (
            wins +
            data["sl"]
        )

        win_rate = (
            wins / completed * 100
            if completed > 0
            else 0
        )

        print(
            "\n--------------------------------"
        )

        if model == "A":

            print(
                "MODEL A — CURRENT"
            )

            print(
                "SL 2 ATR | TP1 2 ATR | TP2 4 ATR"
            )

        elif model == "B":

            print(
                "MODEL B — SAME EXIT LEVELS"
            )

            print(
                "SL 2 ATR | TP1 2 ATR | TP2 4 ATR"
            )

        elif model == "C":

            print(
                "MODEL C — SINGLE TP"
            )

            print(
                "SL 2 ATR | TP 4 ATR"
            )

        print(
            "Trades:",
            data["trades"]
        )

        print(
            "TP2:",
            data["tp2"]
        )

        print(
            "TP1:",
            data["tp1"]
        )

        print(
            "TP:",
            data["tp"]
        )

        print(
            "SL:",
            data["sl"]
        )

        print(
            "TIMEOUT:",
            data["timeout"]
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
                data["profit"],
                2
            ),
            "R"
        )

    # =====================================================
    # SYMBOL SUMMARY
    # =====================================================

    print(
        "\n\n" + "=" * 65
    )

    print(
        "SYMBOL SUMMARY"
    )

    print(
        "=" * 65
    )

    for symbol, result in symbol_results:

        print(
            "\n",
            symbol_name(symbol)
        )

        for model in [
            "A",
            "B",
            "C"
        ]:

            print(
                " Model",
                model,
                "| Trades:",
                result[model]["trades"],
                "| Profit:",
                round(
                    result[model]["profit"],
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
