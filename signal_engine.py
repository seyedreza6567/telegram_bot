from multi_timeframe import analyze_all_timeframes
from risk_manager import build_risk
import news_engine


# =========================================================
# آستانه‌ها (نسخه سخت‌گیرانه نهایی)
#
# - روزانه (1d) و 4 ساعته (4h) باید هر دو هم‌جهت باشند.
# - از سه تایم‌فریم پایین‌تر (1h/2h/3h) حداقل 2 تا باید
#   هم‌جهت با سیگنال نهایی باشند.
# - MIN_QUALITY و MIN_DIRECTIONAL_RATIO بر اساس
#   MAX_SCORE=20 در analysis_engine.py محاسبه می‌شوند.
# =========================================================

MIN_QUALITY = 0.58

MIN_DIRECTIONAL_RATIO = 0.58

MIN_LOWER_CONFIRMATIONS = 2

LOWER_TIMEFRAMES = ["1h", "2h", "3h"]

HIGH_TIMEFRAMES = ["4h", "1d"]

ENTRY_TIMEFRAME = "4h"


def _get_symbol_news(symbol):
    """
    فراخوانی دفاعی: اگر امضای واقعی news_engine.get_symbol_news
    آرگومان‌های کلیدی max_items/max_age_hours را نپذیرد، به فراخوانی
    ساده‌تر سقوط می‌کند تا فیچر اخبار هیچ‌وقت به‌خاطر ناهماهنگی
    امضا، بی‌سروصدا از کار نیفتد.
    """

    try:

        return news_engine.get_symbol_news(
            symbol,
            max_items=10,
            max_age_hours=24
        )

    except TypeError:

        try:
            return news_engine.get_symbol_news(symbol)
        except Exception as e:
            print(f"NEWS ERROR (fallback) {symbol}: {e}")
            return {"available": False, "label": "NEUTRAL", "post_count": 0}

    except Exception as e:

        print(f"NEWS ERROR {symbol}: {e}")

        return {"available": False, "label": "NEUTRAL", "post_count": 0}


def _news_blocks_signal(signal, news):

    if not news or not news.get("available"):
        return False

    label = news.get("label", "NEUTRAL")

    # اخبار منفی فقط جلوی سیگنال‌های لانگ را می‌گیرد؛
    # شورت مجاز باقی می‌ماند (اخبار بد با شورت هم‌جهت است).
    if signal == "LONG" and label == "BEARISH":
        return True

    return False


def final_signal(symbol):

    timeframes = analyze_all_timeframes(symbol)

    high_signals = {
        tf: timeframes[tf]["signal"]
        for tf in HIGH_TIMEFRAMES
        if tf in timeframes
    }

    daily_signal = high_signals.get("1d", "NO TRADE")
    h4_signal = high_signals.get("4h", "NO TRADE")

    long_count = sum(
        1 for s in timeframes.values() if s.get("signal") == "LONG"
    )

    short_count = sum(
        1 for s in timeframes.values() if s.get("signal") == "SHORT"
    )

    lower_long_count = sum(
        1
        for tf in LOWER_TIMEFRAMES
        if timeframes.get(tf, {}).get("signal") == "LONG"
    )

    lower_short_count = sum(
        1
        for tf in LOWER_TIMEFRAMES
        if timeframes.get(tf, {}).get("signal") == "SHORT"
    )

    long_quality_values = [
        timeframes[tf].get("quality", 0)
        for tf in timeframes
        if timeframes[tf].get("signal") == "LONG"
    ]

    short_quality_values = [
        timeframes[tf].get("quality", 0)
        for tf in timeframes
        if timeframes[tf].get("signal") == "SHORT"
    ]

    long_quality = (
        sum(long_quality_values) / len(long_quality_values)
        if long_quality_values else 0
    )

    short_quality = (
        sum(short_quality_values) / len(short_quality_values)
        if short_quality_values else 0
    )

    total_directional = long_count + short_count

    directional_ratio_long = (
        long_count / total_directional if total_directional else 0
    )

    directional_ratio_short = (
        short_count / total_directional if total_directional else 0
    )

    result = {
        "signal": "NO TRADE",
        "timeframes": timeframes,
        "long_count": long_count,
        "short_count": short_count,
        "lower_long_count": lower_long_count,
        "lower_short_count": lower_short_count,
        "long_quality": round(long_quality, 4),
        "short_quality": round(short_quality, 4),
        "quality_margin": round(abs(long_quality - short_quality), 4),
        "risk": {"valid": False},
        "news": {"available": False, "label": "NEUTRAL", "post_count": 0},
    }

    signal = "NO TRADE"

    if (
        daily_signal == "LONG"
        and h4_signal == "LONG"
        and lower_long_count >= MIN_LOWER_CONFIRMATIONS
        and long_quality >= MIN_QUALITY
        and directional_ratio_long >= MIN_DIRECTIONAL_RATIO
    ):
        signal = "LONG"

    elif (
        daily_signal == "SHORT"
        and h4_signal == "SHORT"
        and lower_short_count >= MIN_LOWER_CONFIRMATIONS
        and short_quality >= MIN_QUALITY
        and directional_ratio_short >= MIN_DIRECTIONAL_RATIO
    ):
        signal = "SHORT"

    if signal in ("LONG", "SHORT"):

        news = _get_symbol_news(symbol)

        result["news"] = news

        if _news_blocks_signal(signal, news):

            result["signal"] = "NO TRADE"
            result["reason"] = "سیگنال به‌دلیل اخبار منفی مسدود شد."

            return result

        entry_tf_data = timeframes.get(ENTRY_TIMEFRAME, {})

        entry_price = entry_tf_data.get("price")
        stop_loss = entry_tf_data.get("stop_loss")
        take_profit = entry_tf_data.get("take_profit")

        risk = build_risk(
            signal=signal,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        result["risk"] = risk

        if risk.get("valid"):
            result["signal"] = signal

    return result
