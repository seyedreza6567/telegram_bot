import requests

def get_btc_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"

    try:
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return f"خطای سرور: {r.status_code}"

        data = r.json()

        price = data["bitcoin"]["usd"]

        return f":moneybag: قیمت BTC/USDT:\n{price} دلار"

    except Exception as e:
        return f"خطا: {e}"
