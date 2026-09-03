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
# News filter (CryptoPanic)
# =========================================================
# Set CRYPTOPANIC_API_KEY in Railway (free account at cryptopanic.com).
# If left unset, news_engine.py fails safe: it never blocks a signal,
# it just reports news as "unavailable".
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY")

# Master on/off switch for letting news veto a candle-based signal.
NEWS_FILTER_ENABLED = os.getenv("NEWS_FILTER_ENABLED", "true").lower() == "true"

# How strongly news must disagree with the signal's direction (on a
# -1..1 scale) before it vetoes the trade. Higher = only very lopsided
# news blocks; lower = more cautious.
NEWS_BLOCK_THRESHOLD = float(os.getenv("NEWS_BLOCK_THRESHOLD", "0.35"))
