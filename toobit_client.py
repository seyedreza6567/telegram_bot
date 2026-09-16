import math

import ccxt

import config


# =========================================================
# این ماژول فقط زمانی واقعاً به توبیت وصل می‌شود که
# TRADING_MODE=LIVE باشد. در PAPER هیچ سفارشی از اینجا
# ارسال نمی‌شود (execution_engine.py خودش چک می‌کند).
#
# از ccxt استفاده می‌کنیم چون امضای درخواست‌ها (HMAC) و
# اندپوینت‌های سفارش را به‌صورت تست‌شده و استاندارد پیاده‌سازی
# کرده - ریسک اشتباه در پیاده‌سازی دستی signing برای معاملات
# واقعی را حذف می‌کند.
# =========================================================

_exchange = None


def get_exchange():

    global _exchange

    if _exchange is not None:
        return _exchange

    _exchange = ccxt.toobit({
        "apiKey": config.TOOBIT_API_KEY,
        "secret": config.TOOBIT_SECRET_KEY,
        "enableRateLimit": True,
        "options": {
            "defaultType": "swap",
        },
    })

    _exchange.load_markets()

    return _exchange


def to_ccxt_symbol(symbol):
    """
    "BTC-SWAP-USDT" یا "BTC-USDT" -> "BTC/USDT:USDT" (فرمت یکپارچه ccxt)
    """

    base = (
        symbol
        .replace("-SWAP-USDT", "")
        .replace("-USDT", "")
        .upper()
    )

    return f"{base}/USDT:USDT"


# =========================================================
# اطلاعات نماد / اندازه قدم (Lot Size)
# =========================================================

def get_exchange_info():

    exchange = get_exchange()

    return exchange.markets


def get_symbol_filters(symbol):
    """
    step_size و min_qty واقعی نماد را از ccxt برمی‌گرداند.

    FIX: قبلاً این تابع مقدار entry_price را می‌گرفت (بی‌ربط)
    و همیشه 0.001 را برای هر ارزی هاردکد شده برمی‌گرداند - یعنی
    محاسبه حجم برای ارزهایی مثل DOGE/XRP کاملاً غلط بود.
    حالا واقعاً از دیتای بازار (market precision/limits) خوانده
    می‌شود.
    """

    exchange = get_exchange()

    ccxt_symbol = to_ccxt_symbol(symbol)

    market = exchange.market(ccxt_symbol)

    amount_precision = market.get("precision", {}).get("amount")

    if amount_precision is None:
        step_size = 0.001
    elif isinstance(amount_precision, int):
        step_size = 10 ** (-amount_precision)
    else:
        step_size = float(amount_precision)

    min_qty = (
        market.get("limits", {})
        .get("amount", {})
        .get("min")
        or step_size
    )

    return {
        "step_size": step_size,
        "min_qty": min_qty,
    }


def round_quantity_down(symbol, quantity):

    filters = get_symbol_filters(symbol)

    step = filters["step_size"] or 0.001

    if step <= 0:
        return quantity

    steps = math.floor(quantity / step)

    rounded = steps * step

    return round(rounded, 10)


# =========================================================
# موجودی حساب
# =========================================================

def get_available_balance_usdt():

    exchange = get_exchange()

    balance = exchange.fetch_balance()

    usdt = balance.get("USDT", {})

    return float(usdt.get("free") or usdt.get("total") or 0)


# =========================================================
# قیمت لحظه‌ای
# =========================================================

def get_last_price(symbol):

    exchange = get_exchange()

    ccxt_symbol = to_ccxt_symbol(symbol)

    ticker = exchange.fetch_ticker(ccxt_symbol)

    return float(ticker["last"])


# =========================================================
# پوزیشن باز
# =========================================================

def has_open_position(symbol):

    exchange = get_exchange()

    ccxt_symbol = to_ccxt_symbol(symbol)

    positions = exchange.fetch_positions([ccxt_symbol])

    for position in positions:

        contracts = position.get("contracts") or 0

        if contracts and abs(float(contracts)) > 0:
            return True

    return False


def get_open_position(symbol):

    exchange = get_exchange()

    ccxt_symbol = to_ccxt_symbol(symbol)

    positions = exchange.fetch_positions([ccxt_symbol])

    for position in positions:

        contracts = position.get("contracts") or 0

        if contracts and abs(float(contracts)) > 0:
            return position

    return None


# =========================================================
# ثبت سفارش
# =========================================================

def place_market_order(symbol, side, quantity):
    """
    side: "buy" (باز کردن لانگ) یا "sell" (باز کردن شورت)
    """

    exchange = get_exchange()

    ccxt_symbol = to_ccxt_symbol(symbol)

    return exchange.create_order(
        symbol=ccxt_symbol,
        type="market",
        side=side,
        amount=quantity,
    )


def place_stop_loss(symbol, side, quantity, stop_price):
    """
    side: سمتی که پوزیشن را می‌بندد (مخالف جهت پوزیشن باز)
    """

    exchange = get_exchange()

    ccxt_symbol = to_ccxt_symbol(symbol)

    return exchange.create_order(
        symbol=ccxt_symbol,
        type="stop_market",
        side=side,
        amount=quantity,
        params={
            "stopPrice": stop_price,
            "reduceOnly": True,
        },
    )


def place_take_profit(symbol, side, quantity, take_profit_price):

    exchange = get_exchange()

    ccxt_symbol = to_ccxt_symbol(symbol)

    return exchange.create_order(
        symbol=ccxt_symbol,
        type="take_profit_market",
        side=side,
        amount=quantity,
        params={
            "stopPrice": take_profit_price,
            "reduceOnly": True,
        },
    )


def close_position_market(symbol, side, quantity):
    """
    بستن اضطراری پوزیشن با سفارش مارکت reduce-only.
    side باید سمت بستن‌کننده باشد (مخالف جهت پوزیشن باز).
    """

    exchange = get_exchange()

    ccxt_symbol = to_ccxt_symbol(symbol)

    return exchange.create_order(
        symbol=ccxt_symbol,
        type="market",
        side=side,
        amount=quantity,
        params={
            "reduceOnly": True,
        },
    )
