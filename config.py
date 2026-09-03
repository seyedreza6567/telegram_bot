import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

TOOBIT_API_KEY = os.getenv("TOOBIT_API_KEY")
TOOBIT_SECRET_KEY = os.getenv("TOOBIT_SECRET_KEY")

# =========================================================
# Auto-trading
# =========================================================
TRADING_MODE = os.getenv("TRADING_MODE", "PAPER").upper()
if TRADING_MODE not in ("PAPER", "LIVE"):
    TRADING_MODE = "PAPER"

RISK_PERCENT = float(os.getenv("RISK_PERCENT", "2.0"))

AUTO_SCAN_MINUTES = int(os.getenv("AUTO_SCAN_MINUTES", "15"))

# =========================================================
# News filter (free RSS-based, via news_engine.py)
# =========================================================
# news_engine.py pulls from CoinDesk/Cointelegraph/Decrypt/Bitcoin
# Magazine RSS feeds - no API key needed. If it fails to fetch for
# any reason, it fails safe: it never blocks a signal, it just
# reports news as "unavailable".
#
# Master on/off switch for letting news veto a candle-based signal.
NEWS_FILTER_ENABLED = os.getenv("NEWS_FILTER_ENABLED", "true").lower() == "true"
