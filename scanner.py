import requests

def get_btc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

    try:
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return f"خطای سرور: {r.status_code}"

        data = r.json()

        price = data["price"]

        return f":moneybag: قیمت BTC/USDT:\n{price} دلار"

    except Exception as e:
        return f"خطا: {e}"
