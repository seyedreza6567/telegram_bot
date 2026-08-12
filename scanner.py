import requests
import pandas as pd


BASE_URL = "https://api.toobit.com"


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
# Raw Klines
# =========================================================

def _get_raw_klines(
    symbol="BTC-SWAP-USDT",
    interval="1h",
    limit=200
):

    url = f"{BASE_URL}/quote/v1/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

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

    except Exception as e:

        print(
            "ERROR _get_raw_klines:",
            e
        )

        return None


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
