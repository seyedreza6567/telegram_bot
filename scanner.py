import requests
import pandas as pd


BASE_URL = "https://api.toobit.com"


def _get_raw_klines(symbol="BTC-SWAP-USDT", interval="1h", limit=200):

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

        print("STATUS:", r.status_code)
        print("RESPONSE:", r.text[:500])

        r.raise_for_status()

        data = r.json()

        if not isinstance(data, list) or len(data) == 0:
            print("داده کندل دریافت نشد")
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
        ).reset_index(drop=True)

        return df

    except Exception as e:
        print("ERROR:", e)
        return None


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

    df = df.set_index("open_time")

    result = df.resample("3h").agg({
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

    return result.tail(limit).reset_index(
        drop=True
    )


def get_klines(
    symbol="BTC-SWAP-USDT",
    interval="1h",
    limit=200
):

    if interval.lower() == "3h":

        print("ساخت تایم‌فریم 3H از کندل‌های 1H ...")

        return _build_3h_from_1h(
            symbol=symbol,
            limit=limit
        )

    return _get_raw_klines(
        symbol=symbol,
        interval=interval,
        limit=limit
    )


if __name__ == "__main__":

    df = get_klines(
        symbol="BTC-SWAP-USDT",
        interval="3h",
        limit=250
    )

    if df is not None:

        print("\nداده 3H دریافت شد ✅")
        print(df.tail())

    else:

        print("\nخطا در دریافت داده 3H ❌")
