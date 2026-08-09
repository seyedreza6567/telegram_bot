import requests
import pandas as pd


BASE_URL = "https://api.toobit.com"


def get_klines(symbol="BTC-SWAP-USDT", interval="1h", limit=200):

    url = f"{BASE_URL}/quote/v1/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    try:
        r = requests.get(url, params=params, timeout=10)

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

        df = pd.DataFrame(data, columns=columns)

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]

        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["open_time"] = pd.to_datetime(
            df["open_time"],
            unit="ms"
        )

        df["close_time"] = pd.to_datetime(
            df["close_time"],
            unit="ms"
        )

        return df


    except Exception as e:
        print("ERROR:", e)
        return None


if __name__ == "__main__":

    df = get_klines()

    if df is not None:
        print("\nداده دریافت شد ✅")
        print(df.tail())
    else:
        print("\nخطا در دریافت داده ❌")
