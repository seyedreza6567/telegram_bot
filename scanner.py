import requests

def get_btc_price():
    url = "https://api.toobit.com/api/v1/ticker?symbol=BTCUSDT"

    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        return f"قیمت BTC: {data}"

    except Exception as e:
        return f"خطا: {e}"
