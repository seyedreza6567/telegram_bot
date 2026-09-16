import os


# =========================================================
# تلگرام
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN تنظیم نشده است. "
        "آن را در تنظیمات Variables اضافه کن."
    )


# =========================================================
# توبیت (Toobit)
# =========================================================

TOOBIT_API_KEY = os.environ.get("TOOBIT_API_KEY")
TOOBIT_SECRET_KEY = os.environ.get("TOOBIT_SECRET_KEY")


# =========================================================
# حالت معاملاتی
#
# PAPER : فقط شبیه‌سازی - هیچ سفارش واقعی به صرافی ارسال نمی‌شود.
# LIVE  : سفارش واقعی با پول واقعی روی توبیت ارسال می‌شود.
# =========================================================

TRADING_MODE = os.environ.get(
    "TRADING_MODE",
    "PAPER"
).strip().upper()

if TRADING_MODE not in ("PAPER", "LIVE"):
    TRADING_MODE = "PAPER"

if TRADING_MODE == "LIVE" and (
    not TOOBIT_API_KEY
    or
    not TOOBIT_SECRET_KEY
):
    raise RuntimeError(
        "TRADING_MODE=LIVE تنظیم شده اما "
        "TOOBIT_API_KEY / TOOBIT_SECRET_KEY موجود نیست."
    )


# =========================================================
# مدیریت ریسک
# =========================================================

RISK_PERCENT = float(
    os.environ.get(
        "RISK_PERCENT",
        "2.0"
    )
)

# موجودی فرضی برای محاسبه حجم در حالت PAPER، وقتی که
# نتوانیم موجودی واقعی حساب را از توبیت بخوانیم.
PAPER_FALLBACK_BALANCE_USDT = float(
    os.environ.get(
        "PAPER_FALLBACK_BALANCE_USDT",
        "1000"
    )
)

DEFAULT_LEVERAGE = int(
    os.environ.get(
        "DEFAULT_LEVERAGE",
        "5"
    )
)


# =========================================================
# اسکن خودکار
# =========================================================

AUTO_SCAN_MINUTES = int(
    os.environ.get(
        "AUTO_SCAN_MINUTES",
        "15"
    )
)


# =========================================================
# فیلتر اخبار (news_engine.py - منبع رایگان RSS)
# =========================================================

NEWS_FILTER_ENABLED = os.environ.get(
    "NEWS_FILTER_ENABLED",
    "true"
).strip().lower() in ("1", "true", "yes", "on")
