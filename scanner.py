import requests

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"


def get_btc_price():
    try:
        r = requests.get(COINGECKO_URL, timeout=10)
        r.raise_for_status()

        data = r.json()
        price = data["bitcoin"]["usd"]

        return f"💰 قیمت BTC/USDT:\n{price:,} دلار"

    except requests.RequestException as e:
        return f"❌ خطای ارتباط با سرور:\n{e}"

    except KeyError:
        return "❌ اطلاعات قیمت دریافت نشد."
