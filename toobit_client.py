"""
toobit_client.py

Signed REST client for Toobit Futures (USDT-M) — balance, positions,
opening/closing orders. Used by execution_engine.py.

Docs referenced: https://api-docs.toobit.com/api/code-examples.html
                  https://api-docs.toobit.com/api/usdt-m-account-and-trading.html
"""

import time
import hmac
import hashlib
import requests

from config import TOOBIT_API_KEY, TOOBIT_SECRET_KEY

BASE_URL = "https://api.toobit.com"


class ToobitError(Exception):
    pass


def _sign(params: dict) -> str:
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return hmac.new(
        TOOBIT_SECRET_KEY.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _signed_request(endpoint: str, params: dict = None, method: str = "GET"):
    if not TOOBIT_API_KEY or not TOOBIT_SECRET_KEY:
        raise ToobitError(
            "TOOBIT_API_KEY / TOOBIT_SECRET_KEY تنظیم نشده‌اند "
            "(در Railway → Variables چک کن)."
        )

    params = dict(params or {})
    params["timestamp"] = int(time.time() * 1000)
    params.setdefault("recvWindow", 5000)

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    signature = _sign(params)
    query_string_signed = f"{query_string}&signature={signature}"

    url = f"{BASE_URL}{endpoint}"
    headers = {"X-BB-APIKEY": TOOBIT_API_KEY}

    try:
        if method == "GET":
            r = requests.get(f"{url}?{query_string_signed}", headers=headers, timeout=15)
        else:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            r = requests.post(url, headers=headers, data=query_string_signed, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        # Surface the exchange's own error body (it's usually informative)
        body = None
        try:
            body = r.text
        except Exception:
            pass
        raise ToobitError(f"HTTP {r.status_code}: {body}") from e
    except Exception as e:
        raise ToobitError(str(e)) from e


# =========================================================
# Exchange info / symbol filters
# =========================================================

_SYMBOL_FILTERS_CACHE = {}

# Conservative fallback if a symbol's real filters can't be read
# (e.g. exchangeInfo shape differs from what we parse below). Better
# to size small than to guess a step too big and blow past the
# intended risk.
_FALLBACK_STEP_SIZE = 0.001
_FALLBACK_MIN_QTY = 0.001


def get_exchange_info():
    """Unsigned/public endpoint - contract list, status, filters."""
    r = requests.get(f"{BASE_URL}/api/v1/exchangeInfo", timeout=10)
    r.raise_for_status()
    return r.json()


def get_symbol_filters(symbol: str) -> dict:
    """
    Returns {"step_size": float, "min_qty": float} for a symbol,
    parsed from Toobit's /api/v1/exchangeInfo LOT_SIZE-style filter.

    NOTE: field names here (filterType/stepSize/minQty) follow the
    common Binance-style futures API convention Toobit's docs are
    modeled on. If Toobit's real response uses different field
    names, this silently falls back to the conservative defaults
    above instead of crashing - verify against a live response
    before trusting this for LIVE-mode sizing on low-price/high-
    quantity coins.
    """
    if symbol in _SYMBOL_FILTERS_CACHE:
        return _SYMBOL_FILTERS_CACHE[symbol]

    step_size = _FALLBACK_STEP_SIZE
    min_qty = _FALLBACK_MIN_QTY

    try:
        data = get_exchange_info()
        for contract in data.get("contracts", []):
            if contract.get("symbol") != symbol:
                continue
            for f in contract.get("filters", []):
                filter_type = str(f.get("filterType", "")).upper()
                if filter_type in ("LOT_SIZE", "MARKET_LOT_SIZE"):
                    if f.get("stepSize"):
                        step_size = float(f["stepSize"])
                    if f.get("minQty"):
                        min_qty = float(f["minQty"])
            break
    except Exception as e:
        print(f"WARN get_symbol_filters({symbol}) falling back to defaults: {e}")

    result = {"step_size": step_size, "min_qty": min_qty}
    _SYMBOL_FILTERS_CACHE[symbol] = result
    return result


# =========================================================
# Account
# =========================================================

def get_futures_balance():
    """
    Returns the USDT-margined futures wallet balance info.
    Raises ToobitError on failure — callers must NOT silently
    assume a balance if this fails (that's how you end up sizing
    a real order off a stale/zero number).
    """
    return _signed_request("/api/v1/futures/balance", method="GET")


def get_available_usdt(balance_response=None) -> float:
    """
    Extracts the usable USDT margin balance from the balance
    endpoint's response. Field names come from Toobit's docs;
    if the exchange response shape doesn't match, this raises
    instead of guessing.
    """
    data = balance_response if balance_response is not None else get_futures_balance()

    # Toobit's futures balance response is a list of asset balances.
    if isinstance(data, list):
        for asset in data:
            if str(asset.get("asset", "")).upper() == "USDT":
                for key in ("availableBalance", "available", "balance"):
                    if key in asset:
                        return float(asset[key])
    elif isinstance(data, dict):
        for key in ("availableBalance", "available", "balance"):
            if key in data:
                return float(data[key])

    raise ToobitError(f"فرمت پاسخ موجودی ناشناخته است: {data}")


def get_open_positions():
    return _signed_request("/api/v1/futures/position", method="GET")


def has_open_position(symbol: str) -> bool:
    positions = get_open_positions()
    if not isinstance(positions, list):
        return False
    for p in positions:
        if p.get("symbol") == symbol:
            qty = float(p.get("currentAmount", p.get("positionAmt", 0)) or 0)
            if abs(qty) > 0:
                return True
    return False


# =========================================================
# Orders
# =========================================================

def place_market_order(symbol: str, side: str, quantity: str, client_order_id: str = None):
    """
    side: "BUY_OPEN" (open long) / "SELL_OPEN" (open short)
          "BUY_CLOSE" (close short) / "SELL_CLOSE" (close long)
    quantity: contract quantity as a string, per Toobit's convention.
    """
    params = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": quantity,
    }
    if client_order_id:
        params["newClientOrderId"] = client_order_id
    return _signed_request("/api/v1/futures/order", params, method="POST")


def place_stop_order(symbol: str, side: str, quantity: str, stop_price: float, reduce_only: bool = True):
    """
    Stop-market order used for both stop-loss and take-profit legs
    (take-profit is just a STOP with a price on the favorable side —
    Toobit's futures API exposes both via the same order type with
    a stopPrice trigger; see usdt-m-account-and-trading.html).
    """
    params = {
        "symbol": symbol,
        "side": side,
        "type": "STOP_MARKET",
        "quantity": quantity,
        "stopPrice": stop_price,
    }
    if reduce_only:
        params["reduceOnly"] = "true"
    return _signed_request("/api/v1/futures/order", params, method="POST")


def close_position_market(symbol: str, side: str, quantity: str):
    """side here is the CLOSING side (opposite of the open side)."""
    return place_market_order(symbol, side, quantity, client_order_id=f"close_{int(time.time())}")


if __name__ == "__main__":
    # Manual smoke test — do NOT run this against a live-money key
    # without knowing exactly what it does.
    print(get_futures_balance())
