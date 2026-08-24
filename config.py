import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

# FIX: API keys must never be hardcoded in source code, especially
# in a public GitHub repo. Set these as environment variables in
# Railway (Variables tab) with the exact names below, using your
# NEW keys after revoking the old (leaked) ones.
TOOBIT_API_KEY = os.getenv("TOOBIT_API_KEY")
TOOBIT_SECRET_KEY = os.getenv("TOOBIT_SECRET_KEY")

# =========================================================
# Auto-trading
# =========================================================
# "PAPER" = simulate only, never calls Toobit's order endpoints.
# "LIVE"  = real orders, real money.
# Set via Railway env var TRADING_MODE. Defaults to PAPER so a
# missing/typo'd env var can never accidentally go live.
TRADING_MODE = os.getenv("TRADING_MODE", "PAPER").upper()
if TRADING_MODE not in ("PAPER", "LIVE"):
    TRADING_MODE = "PAPER"

# % of available USDT balance risked per trade (full stop-loss hit).
RISK_PERCENT = float(os.getenv("RISK_PERCENT", "2.0"))
