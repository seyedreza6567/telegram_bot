import time
from datetime import datetime, timedelta, timezone

import feedparser


# =========================================================
# منابع رایگان RSS
#
# NOTE: قبلاً از CryptoPanic API استفاده می‌شد اما تیر CryptoPanic
# رایگانشان دیگر قابل استفاده نیست ("upgrade to a Paid API Plan").
# این ماژول جایگزین آن است: چند فید RSS رایگان و معتبر که بدون
# API Key در دسترس‌اند.
# =========================================================

RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://bitcoinmagazine.com/.rss/full/",
]

NEGATIVE_KEYWORDS = [
    "hack",
    "hacked",
    "exploit",
    "exploited",
    "lawsuit",
    "sued",
    "ban",
    "banned",
    "crash",
    "delist",
    "delisted",
    "scam",
    "fraud",
    "rug pull",
    "insolvent",
    "bankruptcy",
    "collapse",
    "outage",
    "breach",
    "investigation",
    "seized",
]

# اسم/سیمبل ارزها برای تطبیق در متن خبر
SYMBOL_ALIASES = {
    "BTC": ["btc", "bitcoin"],
    "ETH": ["eth", "ethereum"],
    "BNB": ["bnb", "binance coin"],
    "SOL": ["sol", "solana"],
    "XRP": ["xrp", "ripple"],
    "DOGE": ["doge", "dogecoin"],
    "ADA": ["ada", "cardano"],
    "TRX": ["trx", "tron"],
    "AVAX": ["avax", "avalanche"],
    "LINK": ["link", "chainlink"],
    "DOT": ["dot", "polkadot"],
    "LTC": ["ltc", "litecoin"],
    "BCH": ["bch", "bitcoin cash"],
    "UNI": ["uni", "uniswap"],
    "SUI": ["sui"],
}

_CACHE = {}
_CACHE_TTL_SECONDS = 300


def _fetch_all_entries():

    now = time.time()

    cached = _CACHE.get("entries")

    if cached and (now - cached["ts"]) < _CACHE_TTL_SECONDS:
        return cached["entries"]

    entries = []

    for url in RSS_FEEDS:

        try:

            feed = feedparser.parse(url)

            for entry in feed.entries:

                published = None

                if getattr(entry, "published_parsed", None):
                    published = datetime(
                        *entry.published_parsed[:6],
                        tzinfo=timezone.utc
                    )

                entries.append({
                    "title": getattr(entry, "title", ""),
                    "summary": getattr(entry, "summary", ""),
                    "published": published,
                })

        except Exception as e:

            print(f"NEWS_ENGINE feed error ({url}): {e}")

    _CACHE["entries"] = {"ts": now, "entries": entries}

    return entries


def _symbol_base(symbol):

    return (
        symbol
        .replace("-SWAP-USDT", "")
        .replace("-USDT", "")
        .upper()
    )


def get_symbol_news(symbol, max_items=10, max_age_hours=24):

    base = _symbol_base(symbol)

    aliases = SYMBOL_ALIASES.get(base, [base.lower()])

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    entries = _fetch_all_entries()

    matched = []

    for entry in entries:

        if entry["published"] and entry["published"] < cutoff:
            continue

        text = f"{entry['title']} {entry['summary']}".lower()

        if any(alias in text for alias in aliases):
            matched.append(entry)

        if len(matched) >= max_items:
            break

    if not matched:

        return {
            "available": False,
            "label": "NEUTRAL",
            "post_count": 0,
            "items": [],
        }

    negative_count = 0

    for entry in matched:

        text = f"{entry['title']} {entry['summary']}".lower()

        if any(keyword in text for keyword in NEGATIVE_KEYWORDS):
            negative_count += 1

    if negative_count > 0:
        label = "BEARISH"
    else:
        label = "NEUTRAL"

    return {
        "available": True,
        "label": label,
        "post_count": len(matched),
        "items": [entry["title"] for entry in matched],
    }


def has_negative_news_flag(symbol):

    news = get_symbol_news(symbol)

    return news.get("label") == "BEARISH"
