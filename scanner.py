import requests
import pandas as pd

BASE_URL = "https://api.toobit.com"

def get_klines(symbol="BTCUSDT", interval="1h", limit=200):
    url = f"{BASE_URL}/api/v1/market/kline"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()

        data = r.json()

        if "data" not in data:
            return None

        df = pd.DataFrame(data["data"])

        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)

        return df

    except Exception as e:
        print(e)
        return None


if name == "__main__":
    df = get_klines()

    if df is not None:
        print(df.tail())
    else:
        print("خطا در دریافت داده")
