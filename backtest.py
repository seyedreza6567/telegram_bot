import pandas as pd
import numpy as np

from scanner import get_klines
from analysis_engine import analyze


# =========================================================
# تنظیمات اصلی
# =========================================================

SYMBOLS = [
    "BTC-SWAP-USDT",
    "ETH-SWAP-USDT",
    "BNB-SWAP-USDT",
    "SOL-SWAP-USDT",
    "XRP-SWAP-USDT",
    "DOGE-SWAP-USDT",
    "ADA-SWAP-USDT",
    "AVAX-SWAP-USDT",
    "LINK-SWAP-USDT",
    "DOT-SWAP-USDT",
    "LTC-SWAP-USDT",
    "UNI-SWAP-USDT",
    "SUI-SWAP-USDT",
]

TIMEFRAME = "1h"

# تعداد کندل تاریخی
CANDLE_LIMIT = 1000

# حداقل داده برای شروع تحلیل
MIN_ANALYSIS_CANDLES = 250

# ---------------------------------------------------------
# مدیریت معامله
# ---------------------------------------------------------

ATR_SL = 2.0
ATR_TP1 = 2.0
ATR_TP2 = 4.0

# بعد از TP1، حد ضرر بخش باقی‌مانده به Entry منتقل می‌شود
MOVE_SL_TO_ENTRY_AFTER_TP1 = True

# درصد معامله‌ای که در TP1 بسته می‌شود
TP1_CLOSE_PERCENT = 50.0

# درصد باقی‌مانده برای TP2
TP2_CLOSE_PERCENT = 50.0

# حداکثر مدت باز ماندن معامله
MAX_HOLD_CANDLES = 100

# حداقل Score برای ورود
MIN_SCORE = 7

# حداقل اختلاف امتیاز LONG و SHORT برای پذیرفتن سیگنال
# (این مقدار قبلاً تعریف شده بود ولی هیچ‌جا اعمال نمی‌شد - اصلاح شد)
MIN_DIRECTION_DIFFERENCE = 3

# هزینه معامله (کارمزد ورود+خروج + اسلیپیج تخمینی) بر حسب R
# قبلاً اصلاً لحاظ نمی‌شد که نتیجه را خوش‌بینانه‌تر از واقعیت نشان می‌داد
COST_PER_TRADE_R = 0.05


# =========================================================
# ابزارهای کمکی
# =========================================================

def safe_float(value, default=None):

    try:
        value = float(value)

        if np.isfinite(value):
            return value

        return default

    except Exception:
        return default


def get_symbol_name(symbol):

    return (
        symbol
        .replace("-SWAP-USDT", "")
        .replace("-USDT", "")
    )


# =========================================================
# ساخت معامله از نتیجه analysis_engine
# =========================================================

def build_trade(result):

    if not result:
        return None

    signal = result.get(
        "signal",
        "NO TRADE"
    )

    if signal not in ["LONG", "SHORT"]:
        return None

    score = safe_float(
        result.get("score"),
        0
    )

    if score < MIN_SCORE:
        return None

    # -----------------------------------------------------
    # اصلاح ۲: اعمال واقعی فیلتر MIN_DIRECTION_DIFFERENCE
    #
    # اگر analysis_engine شما امتیاز جداگانه برای LONG و SHORT
    # برمی‌گرداند (مثلاً long_score / short_score) این فیلتر
    # سیگنال‌هایی که اختلاف کمی بین دو جهت دارند را رد می‌کند.
    #
    # اگر analysis_engine شما این دو کلید را برنمی‌گرداند،
    # این بخش را با نام واقعی کلیدهای خروجی خودتان جایگزین کنید.
    # -----------------------------------------------------

    long_score = result.get("long_score")
    short_score = result.get("short_score")

    if long_score is not None and short_score is not None:

        long_score = safe_float(long_score, 0)
        short_score = safe_float(short_score, 0)

        direction_diff = abs(long_score - short_score)

        if direction_diff < MIN_DIRECTION_DIFFERENCE:
            return None

    price = safe_float(
        result.get("price")
    )

    atr = safe_float(
        result.get("atr")
    )

    if price is None or atr is None:
        return None

    if atr <= 0 or price <= 0:
        return None

    if signal == "LONG":

        stop_loss = (
            price
            -
            atr * ATR_SL
        )

        tp1 = (
            price
            +
            atr * ATR_TP1
        )

        tp2 = (
            price
            +
            atr * ATR_TP2
        )

    else:

        stop_loss = (
            price
            +
            atr * ATR_SL
        )

        tp1 = (
            price
            -
            atr * ATR_TP1
        )

        tp2 = (
            price
            -
            atr * ATR_TP2
        )

    return {
        "signal": signal,
        "score": score,
        "confidence": result.get(
            "confidence",
            0
        ),
        "entry": price,
        "atr": atr,
        "stop_loss": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
    }


# =========================================================
# تشخیص ترتیب احتمالی برخورد SL/TP وقتی هر دو در یک کندل
# اتفاق می‌افتند (اصلاح ۱)
#
# قبلاً همیشه فرض می‌شد SL اول خورده که یک سوگیری سیستماتیک
# به سمت نتیجه منفی ایجاد می‌کرد (چون ATR_SL == ATR_TP1).
#
# اینجا از جهت کندل (رابطه open/close) به عنوان یک تخمین
# استفاده می‌کنیم:
# - اگر کندل صعودی باشد (close > open) فرض می‌کنیم قیمت
#   ابتدا پایین رفته (low) سپس بالا رفته (high) → منطقی‌تر
#   است TP روی LONG (که به high نیاز دارد) و SL روی SHORT
#   (که به high نیاز دارد) دیرتر لمس شده باشد. اما چون این
#   فقط یک تخمین است، منطق را برای هر دو جهت معامله جداگانه
#   و صریح می‌نویسیم.
# - اگر کندل نزولی باشد (close < open) عکس حالت بالا.
# - اگر open == close، به روش محافظه‌کارانه قبلی (SL اول)
#   برمی‌گردیم.
#
# این یک تخمین است، نه قطعیت؛ برای دقت واقعی باید از دیتای
# تایم‌فریم پایین‌تر (مثلاً 1m داخل هر کندل 1h) استفاده کرد.
# =========================================================

def resolve_same_candle_order(candle, signal):

    open_ = safe_float(candle["open"])
    close_ = safe_float(candle["close"])

    if open_ is None or close_ is None:
        return "SL_FIRST"

    if close_ > open_:
        # کندل صعودی: احتمالاً low قبل از high لمس شده
        candle_direction = "UP"
    elif close_ < open_:
        # کندل نزولی: احتمالاً high قبل از low لمس شده
        candle_direction = "DOWN"
    else:
        return "SL_FIRST"

    if signal == "LONG":
        # LONG: TP نیاز به high دارد، SL نیاز به low دارد
        if candle_direction == "UP":
            # low (SL) زودتر بوده
            return "SL_FIRST"
        else:
            # high (TP) زودتر بوده
            return "TP_FIRST"

    else:
        # SHORT: TP نیاز به low دارد، SL نیاز به high دارد
        if candle_direction == "UP":
            # high (SL) زودتر بوده
            return "SL_FIRST"
        else:
            # low (TP) زودتر بوده
            return "TP_FIRST"


# =========================================================
# بررسی یک معامله
#
# مدل:
#
# 50% در TP1
# 50% در TP2
#
# بعد از TP1:
# SL بخش دوم → Entry
#
# اگر TP1 خورد و سپس قیمت برگشت:
# نتیجه = 0.5R
#
# اگر TP2 هم خورد:
# نتیجه = 1.5R
#
# اگر قبل از TP1، SL بخورد:
# نتیجه = -1R
# =========================================================

def simulate_trade(
    df,
    entry_index,
    trade
):

    signal = trade["signal"]

    entry = trade["entry"]

    original_sl = trade["stop_loss"]

    tp1 = trade["tp1"]

    tp2 = trade["tp2"]

    current_sl = original_sl

    tp1_hit = False

    tp2_hit = False

    last_index = min(
        len(df),
        entry_index + MAX_HOLD_CANDLES + 1
    )

    # -------------------------------------------------------
    # اصلاح ۳: شروع بررسی از خود کندل entry_index
    #
    # چون analyze() روی df.iloc[:entry_index] اجرا می‌شود،
    # سیگنال بر اساس داده‌ی تا انتهای کندل (entry_index - 1)
    # صادر شده و ورود عملاً در ابتدای کندل entry_index رخ
    # می‌دهد. قبلاً شبیه‌سازی از entry_index + 1 شروع می‌شد و
    # همین کندل ورود اصلاً برای برخورد SL/TP چک نمی‌شد.
    # -------------------------------------------------------

    for i in range(
        entry_index,
        last_index
    ):

        candle = df.iloc[i]

        high = safe_float(
            candle["high"]
        )

        low = safe_float(
            candle["low"]
        )

        if high is None or low is None:
            continue

        # =================================================
        # LONG
        # =================================================

        if signal == "LONG":

            # ---------------------------------------------
            # قبل از TP1
            # ---------------------------------------------

            if not tp1_hit:

                hit_sl = low <= current_sl
                hit_tp1 = high >= tp1

                if hit_sl and hit_tp1:

                    order = resolve_same_candle_order(
                        candle, signal
                    )

                    if order == "SL_FIRST":

                        return {
                            "result": "SL",
                            "r": -1.0 - COST_PER_TRADE_R,
                            "bars": i - entry_index
                        }

                    else:
                        # TP1 زودتر لمس شده، ادامه می‌دهیم
                        tp1_hit = True

                        if MOVE_SL_TO_ENTRY_AFTER_TP1:
                            current_sl = entry

                        if high >= tp2:

                            return {
                                "result": "TP2",
                                "r": 1.5 - COST_PER_TRADE_R,
                                "bars": i - entry_index
                            }

                        continue

                if hit_sl:

                    return {
                        "result": "SL",
                        "r": -1.0 - COST_PER_TRADE_R,
                        "bars": i - entry_index
                    }

                if hit_tp1:

                    tp1_hit = True

                    if MOVE_SL_TO_ENTRY_AFTER_TP1:

                        current_sl = entry

                    # اگر در همان کندل TP2 هم لمس شود
                    if high >= tp2:

                        tp2_hit = True

                        return {
                            "result": "TP2",
                            "r": 1.5 - COST_PER_TRADE_R,
                            "bars": i - entry_index
                        }

                    continue

            # ---------------------------------------------
            # بعد از TP1
            # ---------------------------------------------

            else:

                # TP2
                if high >= tp2:

                    tp2_hit = True

                    return {
                        "result": "TP2",
                        "r": 1.5 - COST_PER_TRADE_R,
                        "bars": i - entry_index
                    }

                # SL دوم = Entry
                if low <= current_sl:

                    return {
                        "result": "TP1",
                        "r": 0.5 - COST_PER_TRADE_R,
                        "bars": i - entry_index
                    }

        # =================================================
        # SHORT
        # =================================================

        else:

            # ---------------------------------------------
            # قبل از TP1
            # ---------------------------------------------

            if not tp1_hit:

                hit_sl = high >= current_sl
                hit_tp1 = low <= tp1

                if hit_sl and hit_tp1:

                    order = resolve_same_candle_order(
                        candle, signal
                    )

                    if order == "SL_FIRST":

                        return {
                            "result": "SL",
                            "r": -1.0 - COST_PER_TRADE_R,
                            "bars": i - entry_index
                        }

                    else:
                        tp1_hit = True

                        if MOVE_SL_TO_ENTRY_AFTER_TP1:
                            current_sl = entry

                        if low <= tp2:

                            return {
                                "result": "TP2",
                                "r": 1.5 - COST_PER_TRADE_R,
                                "bars": i - entry_index
                            }

                        continue

                if hit_sl:

                    return {
                        "result": "SL",
                        "r": -1.0 - COST_PER_TRADE_R,
                        "bars": i - entry_index
                    }

                if hit_tp1:

                    tp1_hit = True

                    if MOVE_SL_TO_ENTRY_AFTER_TP1:

                        current_sl = entry

                    # TP2 در همان کندل
                    if low <= tp2:

                        tp2_hit = True

                        return {
                            "result": "TP2",
                            "r": 1.5 - COST_PER_TRADE_R,
                            "bars": i - entry_index
                        }

                    continue

            # ---------------------------------------------
            # بعد از TP1
            # ---------------------------------------------

            else:

                if low <= tp2:

                    tp2_hit = True

                    return {
                        "result": "TP2",
                        "r": 1.5 - COST_PER_TRADE_R,
                        "bars": i - entry_index
                    }

                if high >= current_sl:

                    return {
                        "result": "TP1",
                        "r": 0.5 - COST_PER_TRADE_R,
                        "bars": i - entry_index
                    }

    # =====================================================
    # اگر بعد از مدت مشخص هنوز باز بود
    # =====================================================

    last_close = safe_float(
        df.iloc[
            last_index - 1
        ]["close"]
    )

    if last_close is None:

        return {
            "result": "OPEN",
            "r": 0.0,
            "bars": last_index - entry_index
        }

    # اگر TP1 قبلاً خورده باشد
    # حداقل همان 0.5R را حفظ می‌کنیم

    if tp1_hit:

        return {
            "result": "TP1",
            "r": 0.5 - COST_PER_TRADE_R,
            "bars": last_index - entry_index
        }

    return {
        "result": "OPEN",
        "r": 0.0,
        "bars": last_index - entry_index
    }


# =========================================================
# بک‌تست یک ارز
# =========================================================

def backtest_symbol(symbol):

    print("\n" + "=" * 70)

    print(
        f"🔎 BACKTEST: {get_symbol_name(symbol)}"
    )

    print("=" * 70)

    try:

        df = get_klines(
            symbol=symbol,
            interval=TIMEFRAME,
            limit=CANDLE_LIMIT
        )

    except Exception as e:

        print(
            f"❌ خطا در دریافت {symbol}: {e}"
        )

        return None

    if df is None:

        print(
            "❌ داده دریافت نشد"
        )

        return None

    if len(df) < MIN_ANALYSIS_CANDLES + 20:

        print(
            f"❌ داده کافی نیست: {len(df)}"
        )

        return None

    df = df.copy()

    trades = []

    tp2_count = 0
    tp1_count = 0
    sl_count = 0
    open_count = 0

    total_r = 0.0

    signals_found = 0
    signals_rejected = 0

    total_hold_bars = 0

    # =====================================================
    # شروع حرکت تاریخی
    # =====================================================

    i = MIN_ANALYSIS_CANDLES

    while i < len(df) - 10:

        historical_df = df.iloc[
            :i
        ].copy()

        # -----------------------------------------------
        # تحلیل فقط با داده‌ای که در آن لحظه وجود داشته
        # -----------------------------------------------

        try:

            analysis = analyze(
                historical_df
            )

        except Exception as e:

            print(
                f"⚠️ خطای تحلیل در کندل {i}: {e}"
            )

            i += 1

            continue

        signal = analysis.get(
            "signal",
            "NO TRADE"
        )

        if signal in [
            "LONG",
            "SHORT"
        ]:

            signals_found += 1

        trade = build_trade(
            analysis
        )

        if trade is None:

            signals_rejected += 1

            i += 1

            continue

        # =================================================
        # شبیه‌سازی معامله
        # =================================================

        outcome = simulate_trade(
            df=df,
            entry_index=i,
            trade=trade
        )

        result_name = outcome[
            "result"
        ]

        result_r = outcome[
            "r"
        ]

        hold_bars = outcome[
            "bars"
        ]

        total_hold_bars += hold_bars

        # =================================================
        # آمار
        # =================================================

        if result_name == "TP2":

            tp2_count += 1

            total_r += result_r

        elif result_name == "TP1":

            tp1_count += 1

            total_r += result_r

        elif result_name == "SL":

            sl_count += 1

            total_r += result_r

        else:

            open_count += 1

        trades.append({
            "symbol": symbol,
            "index": i,
            "signal": trade["signal"],
            "score": trade["score"],
            "confidence": trade["confidence"],
            "entry": trade["entry"],
            "stop_loss": trade["stop_loss"],
            "tp1": trade["tp1"],
            "tp2": trade["tp2"],
            "result": result_name,
            "profit_r": result_r,
            "hold_bars": hold_bars
        })

        # =================================================
        # جلوگیری از ورود دوباره قبل از پایان معامله
        # =================================================

        jump = max(
            1,
            hold_bars
        )

        i += jump

    # =====================================================
    # آمار نهایی ارز
    # =====================================================

    completed = (
        tp2_count
        + tp1_count
        + sl_count
    )

    wins = (
        tp2_count
        + tp1_count
    )

    if completed > 0:

        win_rate = (
            wins / completed
        ) * 100

    else:

        win_rate = 0.0

    if len(trades) > 0:

        avg_hold = (
            total_hold_bars
            /
            len(trades)
        )

    else:

        avg_hold = 0.0

    # =====================================================
    # گزارش
    # =====================================================

    print(
        f"\n📊 {get_symbol_name(symbol)}"
    )

    print(
        f"📈 معاملات: {len(trades)}"
    )

    print(
        f"🔎 سیگنال پیدا شده: {signals_found}"
    )

    print(
        f"⚪ سیگنال رد شده: {signals_rejected}"
    )

    print(
        f"🟢 TP2: {tp2_count}"
    )

    print(
        f"🟢 TP1: {tp1_count}"
    )

    print(
        f"🔴 SL: {sl_count}"
    )

    print(
        f"⚪ باز: {open_count}"
    )

    print(
        f"🎯 Win Rate: {win_rate:.2f}%"
    )

    print(
        f"💰 نتیجه: {total_r:.2f}R"
    )

    print(
        f"⏱️ میانگین نگهداری: {avg_hold:.1f} کندل"
    )

    return {
        "symbol": symbol,
        "trades": len(trades),
        "signals_found": signals_found,
        "signals_rejected": signals_rejected,
        "tp2": tp2_count,
        "tp1": tp1_count,
        "sl": sl_count,
        "open": open_count,
        "wins": wins,
        "win_rate": win_rate,
        "profit_r": total_r,
        "avg_hold": avg_hold,
        "trade_data": trades
    }


# =========================================================
# رتبه‌بندی ارزها
# =========================================================

def print_ranking(results):

    print(
        "\n\n"
        + "=" * 70
    )

    print(
        "🏆 رتبه‌بندی ارزها"
    )

    print(
        "=" * 70
    )

    # اول بر اساس سود R
    # سپس Win Rate
    # سپس تعداد معاملات

    ranking = sorted(
        results,
        key=lambda x: (
            x["profit_r"],
            x["win_rate"],
            x["trades"]
        ),
        reverse=True
    )

    for rank, result in enumerate(
        ranking,
        start=1
    ):

        symbol = get_symbol_name(
            result["symbol"]
        )

        profit = result[
            "profit_r"
        ]

        win_rate = result[
            "win_rate"
        ]

        trades = result[
            "trades"
        ]

        if profit > 0:

            icon = "🟢"

        elif profit < 0:

            icon = "🔴"

        else:

            icon = "⚪"

        print(
            f"{rank:02d}. {icon} "
            f"{symbol:<6} | "
            f"Profit: {profit:+.2f}R | "
            f"Win: {win_rate:.2f}% | "
            f"Trades: {trades}"
        )

    return ranking


# =========================================================
# گزارش نهایی
# =========================================================

def main():

    print(
        "\n"
        + "=" * 70
    )

    print(
        "🚀 BACKTEST ENGINE"
    )

    print(
        "=" * 70
    )

    print(
        f"⏱️ تایم‌فریم: {TIMEFRAME}"
    )

    print(
        f"📊 کندل تاریخی: {CANDLE_LIMIT}"
    )

    print(
        f"🛑 ATR Stop: {ATR_SL}R"
    )

    print(
        f"🎯 TP1: {ATR_TP1}R"
    )

    print(
        f"🎯 TP2: {ATR_TP2}R"
    )

    print(
        "💡 بعد از TP1: انتقال SL به Entry"
    )

    print(
        f"💸 هزینه هر معامله: {COST_PER_TRADE_R}R"
    )

    print(
        "\n⚠️ بک‌تست فقط برای ارزیابی است."
    )

    all_results = []

    for symbol in SYMBOLS:

        try:

            result = backtest_symbol(
                symbol
            )

            if result is not None:

                all_results.append(
                    result
                )

        except Exception as e:

            print(
                f"\n❌ خطای جدی در "
                f"{get_symbol_name(symbol)}:"
            )

            print(e)

    if not all_results:

        print(
            "\n❌ هیچ نتیجه‌ای برای بک‌تست وجود ندارد."
        )

        return

    # =====================================================
    # رتبه‌بندی
    # =====================================================

    ranking = print_ranking(
        all_results
    )

    # =====================================================
    # مجموع کل
    # =====================================================

    total_trades = sum(
        x["trades"]
        for x in all_results
    )

    total_tp2 = sum(
        x["tp2"]
        for x in all_results
    )

    total_tp1 = sum(
        x["tp1"]
        for x in all_results
    )

    total_sl = sum(
        x["sl"]
        for x in all_results
    )

    total_open = sum(
        x["open"]
        for x in all_results
    )

    total_profit = sum(
        x["profit_r"]
        for x in all_results
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

        overall_win_rate = (
            wins / completed
        ) * 100

    else:

        overall_win_rate = 0.0

    # =====================================================
    # بهترین و بدترین ارز
    # =====================================================

    best = ranking[0]

    worst = ranking[-1]

    # =====================================================
    # گزارش نهایی
    # =====================================================

    print(
        "\n\n"
        + "=" * 70
    )

    print(
        "🏆 گزارش نهایی بک‌تست"
    )

    print(
        "=" * 70
    )

    print(
        f"\n🥇 بهترین ارز: "
        f"{get_symbol_name(best['symbol'])}"
    )

    print(
        f"💰 سود: "
        f"{best['profit_r']:+.2f}R"
    )

    print(
        f"🎯 Win Rate: "
        f"{best['win_rate']:.2f}%"
    )

    print(
        f"\n🔻 ضعیف‌ترین ارز: "
        f"{get_symbol_name(worst['symbol'])}"
    )

    print(
        f"💰 نتیجه: "
        f"{worst['profit_r']:+.2f}R"
    )

    print(
        f"🎯 Win Rate: "
        f"{worst['win_rate']:.2f}%"
    )

    print(
        "\n"
        + "-" * 70
    )

    print(
        f"📈 مجموع معاملات: "
        f"{total_trades}"
    )

    print(
        f"🟢 مجموع TP2: "
        f"{total_tp2}"
    )

    print(
        f"🟢 مجموع TP1: "
        f"{total_tp1}"
    )

    print(
        f"🔴 مجموع SL: "
        f"{total_sl}"
    )

    print(
        f"⚪ معاملات باز: "
        f"{total_open}"
    )

    print(
        f"🎯 Win Rate کلی: "
        f"{overall_win_rate:.2f}%"
    )

    print(
        f"💰 نتیجه فرضی کلی: "
        f"{total_profit:+.2f}R"
    )

    print(
        "\n"
        + "=" * 70
    )

    # =====================================================
    # رتبه‌بندی دوباره برای کپی راحت
    # =====================================================

    print(
        "📋 رتبه‌بندی نهایی"
    )

    print(
        "=" * 70
    )

    for rank, result in enumerate(
        ranking,
        start=1
    ):

        print(
            f"{rank}. "
            f"{get_symbol_name(result['symbol'])} "
            f"| "
            f"{result['win_rate']:.2f}% "
            f"| "
            f"{result['profit_r']:+.2f}R"
        )

    print(
        "\n⚠️ این بک‌تست سود واقعی یا تضمین سود آینده نیست."
    )


# =========================================================
# اجرای برنامه
# =========================================================

if __name__ == "__main__":

    main()
