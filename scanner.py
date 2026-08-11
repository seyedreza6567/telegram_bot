import requests
import pandas as pd

BASE_URL = "https://api.toobit.com"


# =========================================================
# دریافت لیست قراردادهای Futures فعال
# =========================================================

def get_futures_symbols():

    url = f"{BASE_URL}/api/v1/exchangeInfo"

    try:

        r = requests.get(
            url,
            timeout=10
        )

        print(
            "EXCHANGE INFO STATUS:",
            r.status_code
        )

        r.raise_for_status()

        data = r.json()

        contracts = data.get(
            "contracts",
            []
        )

        if not contracts:

            print(
                "هیچ قرارداد Futures پیدا نشد ❌"
            )

            return []

        symbols = []

        for contract in contracts:

            symbol = contract.get(
                "symbol"
            )

            status = contract.get(
                "status"
            )

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

                symbols.append(
                    symbol
                )

        symbols = sorted(
            set(symbols)
        )

        print(
            f"تعداد قراردادهای Futures فعال: {len(symbols)}"
        )

        # =================================================
        # تست پیدا کردن ارزهای مهم
        # =================================================

        btc_symbols = [
            x for x in symbols
            if "BTC" in x.upper()
        ]

        eth_symbols = [
            x for x in symbols
            if "ETH" in x.upper()
        ]

        bnb_symbols = [
            x for x in symbols
            if "BNB" in x.upper()
        ]

        print(
            "BTC:",
            btc_symbols
        )

        print(
            "ETH:",
            eth_symbols
        )

        print(
            "BNB:",
            bnb_symbols
        )

        return symbols

    except Exception as e:

        print(
            "ERROR get_futures_symbols:",
            e
        )

        return []


# =========================================================
# دریافت لیست قراردادهای مناسب برای نمایش
# =========================================================

def get_filtered_futures_symbols():

    symbols = get_futures_symbols()

    if not symbols:

        return []

    filtered = []

    for symbol in symbols:

        upper_symbol = symbol.upper()

        # فعلاً فقط قراردادهای بسیار عجیب
        # با تعداد صفرهای زیاد حذف شوند

        if upper_symbol.startswith(
            (
                "1000000",
                "100000",
                "10000",
                "1000"
            )
        ):
            continue

        filtered.append(
            symbol
        )

    # =====================================================
    # ارزهای مهم همیشه در ابتدای لیست
    # =====================================================

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

    # اول ارزهای مهمی که واقعاً
    # در لیست Toobit وجود دارند

    for priority_symbol in priority:

        if priority_symbol in filtered:

            final_symbols.append(
                priority_symbol
            )

    # بعد بقیه ارزها

    for symbol in filtered:

        if symbol not in final_symbols:

            final_symbols.append(
                symbol
            )

    print(
        f"تعداد قراردادهای بعد از فیلتر: "
        f"{len(final_symbols)}"
    )

    print(
        "ارزهای مهم موجود:"
    )

    for symbol in final_symbols[:20]:

        print(
            symbol
        )

    return final_symbols


# =========================================================
# دریافت کندل‌های خام
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
            timeout=10
        )

        print(
            "STATUS:",
            r.status_code
        )

        print(
            "RESPONSE:",
            r.text[:500]
        )

        r.raise_for_status()

        data = r.json()

        if not isinstance(data, list) or len(data) == 0:

            print(
                "داده کندل دریافت نشد"
            )

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
            unit="ms"
        )

        df["close_time"] = pd.to_datetime(
            df["close_time"],
            unit="ms"
        )

        df = df.sort_values(
            "open_time"
        ).reset_index(
            drop=True
        )

        return df

    except Exception as e:

        print(
            "ERROR:",
            e
        )

        return None


# =========================================================
# ساخت تایم‌فریم 3H از 1H
# =========================================================

def _build_3h_from_1h(
    symbol="BTC-SWAP-USDT",
    limit=250
):

    df = _get_raw_klines(
        symbol=symbol,
        interval="1h",
        limit=limit * 3
    )

    if df is None or len(df) < 3:

        return None

    df = df.set_index(
        "open_time"
    )

    result = df.resample(
        "3h"
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

    result = result.dropna(
        subset=[
            "open",
            "high",
            "low",
            "close"
        ]
    )

    result = result.reset_index()

    return result.tail(
        limit
    ).reset_index(
        drop=True
    )


# =========================================================
# تابع اصلی دریافت Kline
# =========================================================

def get_klines(
    symbol="BTC-SWAP-USDT",
    interval="1h",
    limit=200
):

    if interval.lower() == "3h":

        print(
            "ساخت تایم‌فریم 3H از کندل‌های 1H ..."
        )

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
# تست مستقیم فایل
# =========================================================

if __name__ == "__main__":

    print(
        "\nدر حال دریافت قراردادهای Futures..."
    )

    symbols = get_futures_symbols()

    print(
        "\nچند قرارداد اول:"
    )

    for symbol in symbols[:20]:

        print(
            symbol
        )

    print(
        "\nدر حال اعمال فیلتر..."
    )

    filtered_symbols = (
        get_filtered_futures_symbols()
    )

    print(
        "\nچند قرارداد فیلترشده:"
    )

    for symbol in filtered_symbols[:20]:

        print(
            symbol
        )

    print(
        "\nتست دریافت BTC..."
    )

    df = get_klines(
        symbol="BTC-SWAP-USDT",
        interval="3h",
        limit=250
    )

    if df is not None:

        print(
            "\nداده 3H دریافت شد ✅"
        )

        print(
            df.tail()
        )

    else:

        print(
            "\nخطا در دریافت داده 3H ❌"
        )
