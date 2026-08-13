import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

# FIX: API keys must never be hardcoded in source code, especially
# in a public GitHub repo. Set these as environment variables in
# Railway (Variables tab) with the exact names below, using your
# NEW keys after revoking the old (leaked) ones.
TOOBIT_API_KEY = os.getenv("TOOBIT_API_KEY")

TOOBIT_SECRET_KEY = os.getenv("TOOBIT_SECRET_KEY")
