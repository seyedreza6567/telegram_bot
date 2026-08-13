import time
import requests
import pandas as pd


BASE_URL = "https://api.toobit.com"

# Toobit's /quote/v1/klines endpoint caps "limit" at 1000 per request
# (confirmed in their official docs: Default 1000, Max 1000).
# To fetch more candles than that, we page backwards in time using
# the "endTime" parameter and stitch the pages together.
API_MAX_LIMIT = 1000

# =========================================================
# FIX: retry settings.
# Backtesting many symbols x many timeframes means hundreds of
# requests in a short window. Without retries, a single dropped
# connection or rate-limit response ("WebSocket connection failed",
# empty page) silently turned into "NO TRADES" for that symbol,
# which is why results changed every run. Now a failed page is
# retried a few times with an increasing wait before giving up.
# =========================================================

MAX_RETRIES = 4

RETRY_BACKOFF_SECONDS = 1.5

PAGE_SLEEP_SECONDS = 0.35


# =========================================================
# Futures Symbols
# =========================================================

def get_futures_symbols():

    url = f"{BASE_URL}/api/v1/exchangeInfo"

    try:

        r = requests.get(
            url,
            timeout=10
        )

        r.raise_for_status()

        data = r.json()

        contracts = data.get(
            "contracts",
            []
        )

        symbols = []

        for contract in contracts:

            symbol = contract.get("symbol")
            status = contract.get("status")

            if not symbol:
                continue

            if status and str(status).upper() not in [
                "TRADING",
                "ONLINE",
                "1",
                "NORMAL"
            ]:
                continue

            if symbol.endswith("-USDT"):

                symbols.append(symbol)

        return sorted(
            set(symbols)
        )

    except Exception as e:

        print(
            "ERROR get_futures_symbols:",
            e
        )

        return []


# =========================================================
# Filter
# =========================================================

def get_filtered_futures_symbols():

    symbols = get_futures_symbols()

    if not symbols:
        return []

    filtered = []

    for symbol in symbols:

        upper_symbol = symbol.upper()

        if upper_symbol.startswith(
            (
                "1000000",
                "100000",
                "10000",
                "1000"
            )
        ):
            continue

        filtered.append(symbol)

    priority = [
        "BTC-SWAP-USDT",
        "ETH-SWAP-USDT",
        "BNB-SWAP-USDT",
        "SOL-SWAP-USDT",
        "XRP-SWAP-USDT",
        "DOGE-SWAP-USDT",
        "ADA-SWAP-USDT",
        "TRX-SWAP-USDT",
        "AVAX-SWAP-USDT",
        "LINK-SWAP-USDT",
        "DOT-SWAP-USDT",
        "LTC-SWAP-USDT",
        "BCH-SWAP-USDT",
        "UNI-SWAP-USDT",
        "SUI-SWAP-USDT"
    ]

    final_symbols = []

    for symbol in priority:

        if symbol in filtered:

            final_symbols.append(
                symbol
            )

    for symbol in filtered:

        if symbol not in final_symbols:

            final_symbols.append(
                symbol
            )

    return final_symbols


# =========================================================
# Single page of raw klines (with retry)
# =========================================================

def _get_klines_page(
    symbol,
    interval,
    limit,
    end_time=None
):

    url = f"{BASE_URL}/quote/v1/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": min(limit, API_MAX_LIMIT)
    }

    if end_time is not None:
        params["endTime"] = end_time

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            r = requests.get(
                url,
                params=params,
                timeout=15
            )

            r.raise_for_status()

            data = r.json()

            if (
                not isinstance(data, list)
                or
                len(data) == 0
            ):

                return None

            columns = [
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_volume",
                "trades",
                "taker_buy_volume",
                "taker_buy_quote_volume"
            ]

            df = pd.DataFrame(
                data,
                columns=columns
            )

            return df

        except Exception as e:

            last_error = e

            if attempt < MAX_RETRIES:

                wait = RETRY_BACKOFF_SECONDS * attempt

                print(
                    f"WARN _get_klines_page "
                    f"({symbol} {interval}) attempt "
                    f"{attempt}/{MAX_RETRIES} failed: {e} "
                    f"-> retrying in {wait:.1f}s"
                )

                time.sleep(wait)

    print(
        "ERROR _get_klines_page (gave up):",
        symbol,
        interval,
        last_error
    )

    return None


# =========================================================
# Raw Klines (with pagination)
# =========================================================

def _get_raw_klines(
    symbol="BTC-SWAP-USDT",
    interval="1h",
    limit=200
):

    pages = []
    remaining = limit
    end_time = None
    seen_earliest_open_time = None

    # =====================================================
    # PAGE BACKWARDS UNTIL WE HAVE ENOUGH DATA
    # =====================================================

    while remaining > 0:

        page_request_size = min(remaining, API_MAX_LIMIT)

        page = _get_klines_page(
            symbol=symbol,
            interval=interval,
            limit=page_request_size,
            end_time=end_time
        )

        if page is None or len(page) == 0:
            break

        earliest_open_time = int(page["open_time"].iloc[0])

        # Stop if the exchange keeps returning the same page
        # (no more historical data available).
        if (
            seen_earliest_open_time is not None
            and
            earliest_open_time >= seen_earliest_open_time
        ):
            break

        seen_earliest_open_time = earliest_open_time

        pages.append(page)

        remaining -= len(page)

        # Next page ends right before this page's earliest candle.
        end_time = earliest_open_time - 1

        # If we asked for a full page but got back fewer candles,
        # we've hit the start of available history on the exchange.
        if len(page) < page_request_size:
            break

        # Be gentle with the API between pages.
        time.sleep(PAGE_SLEEP_SECONDS)

    if not pages:
        return None

    df = pd.concat(
        pages,
        ignore_index=True
    )

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    for col in numeric_columns:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df["open_time"] = pd.to_datetime(
        df["open_time"],
        unit="ms",
        utc=True,
        errors="coerce"
    )

    df["close_time"] = pd.to_datetime(
        df["close_time"],
        unit="ms",
        utc=True,
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]
    )

    df = df.sort_values(
        "open_time"
    )

    df = df.drop_duplicates(
        subset="open_time",
        keep="last"
    )

    df = df.reset_index(
        drop=True
    )

    # =================================================
    # فقط کندل‌های کاملاً بسته
    # =================================================

    now = pd.Timestamp.now(
        tz="UTC"
    )

    df = df[
        df["close_time"] <= now
    ].copy()

    df = df.reset_index(
        drop=True
    )

    if len(df) == 0:
        return None

    return df.tail(
        limit
    ).reset_index(
        drop=True
    )


# =========================================================
# 3H
# =========================================================

def _build_3h_from_1h(
    symbol="BTC-SWAP-USDT",
    limit=250
):

    source_limit = (
        limit * 3 + 10
    )

    df = _get_raw_klines(
        symbol=symbol,
        interval="1h",
        limit=source_limit
    )

    if df is None or len(df) < 3:

        return None

    df = df.copy()

    df = df.set_index(
        "open_time"
    )

    result = df.resample(
        "3h",
        label="left",
        closed="left"
    ).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
        "close_time": "last",
        "quote_volume": "sum",
        "trades": "sum",
        "taker_buy_volume": "sum",
        "taker_buy_quote_volume": "sum"
    })

    # =====================================================
    # فقط کندل‌هایی که واقعاً ۳ کندل 1H کامل دارند
    # =====================================================

    counts = df["close"].resample(
        "3h",
        label="left",
        closed="left"
    ).count()

    result["source_count"] = counts

    result = result[
        result["source_count"] == 3
    ].copy()

    result = result.dropna(
        subset=[
            "open",
            "high",
            "low",
            "close"
        ]
    )

    result = result.drop(
        columns=[
            "source_count"
        ]
    )

    result = result.reset_index()

    return result.tail(
        limit
    ).reset_index(
        drop=True
    )


# =========================================================
# Main
# =========================================================

def get_klines(
    symbol="BTC-SWAP-USDT",
    interval="1h",
    limit=200
):

    interval = interval.lower()

    if interval == "3h":

        return _build_3h_from_1h(
            symbol=symbol,
            limit=limit
        )

    return _get_raw_klines(
        symbol=symbol,
        interval=interval,
        limit=limit
    )


# =========================================================
# Test
# =========================================================

if __name__ == "__main__":

    df = get_klines(
        symbol="BTC-SWAP-USDT",
        interval="1h",
        limit=100
    )

    if df is not None:

        print(
            "\nDATA OK"
        )

        print(
            "Rows:",
            len(df)
        )

        print(
            df[
                [
                    "open_time",
                    "open",
                    "high",
                    "low",
                    "close"
                ]
            ].tail(10)
        )

    else:

        print(
            "\nDATA ERROR"
        )
