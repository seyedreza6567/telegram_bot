from scanner import get_klines

# FIX: MAX_SCORE قبلاً اینجا به‌صورت جداگانه و ثابت (15.0) تعریف شده
# بود و بعد از این‌که analysis_engine.py با اضافه شدن ADX/OBV/S-R
# به MAX_SCORE=20 بازمقیاس شد، این کپی جدا هماهنگ نشد. نتیجه‌اش این
# بود که هر امتیاز بین 15 تا 20 به 15 برش می‌خورد و quality
# (score/15) به‌طور مصنوعی به سمت 1.0 متورم می‌شد و همه‌ی آستانه‌های
# MIN_QUALITY در signal_engine.py بدون این‌که کسی آن ثابت را دست
# بزند، سست‌تر می‌شدند. حالا این مقدار مستقیماً از analysis_engine.py
# ایمپورت می‌شود تا دیگر نتوانند از هم جدا بیفتند.

from analysis_engine import analyze, MAX_SCORE as ANALYSIS_MAX_SCORE


TIMEFRAMES = [
    "1h",
    "2h",
    "3h",
    "4h",
    "1d",
]

KLINES_LIMIT = 250


def analyze_all_timeframes(symbol):

    results = {}

    for timeframe in TIMEFRAMES:

        df = get_klines(
            symbol=symbol,
            interval=timeframe,
            limit=KLINES_LIMIT
        )

        if df is None:

            results[timeframe] = {
                "signal": "NO TRADE",
                "score": 0,
                "quality": 0,
                "reason": "دریافت داده ناموفق بود.",
            }

            continue

        analysis = analyze(df)

        quality = (
            analysis.get("score", 0) / ANALYSIS_MAX_SCORE
            if ANALYSIS_MAX_SCORE
            else 0
        )

        analysis["quality"] = round(quality, 4)

        results[timeframe] = analysis

    return results
