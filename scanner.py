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

        print("STATUS:", r.status_code)
        print("RESPONSE:", r.text[:500])

        data = r.json()

        if "data" not in data:
            return None

        df = pd.DataFrame(data["data"])

        return df

    except Exception as e:
        print("ERROR:", e)
        return None


if __name__ == "__main__":

    df = get_klines()

    if df is not None:
        print(df.head())

    else:
        print("خطا در دریافت داده")
