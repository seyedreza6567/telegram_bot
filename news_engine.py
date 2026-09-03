"""
news_engine.py
---------------
Free crypto news fetcher using public RSS feeds (no API key required).

Sources: CoinDesk, Cointelegraph, Decrypt, Bitcoin Magazine.
Uses feedparser to pull latest headlines and filters them by symbol/keyword
so the bot can check for relevant news before confirming a trade signal.

Install requirement (already added to requirements.txt):
    feedparser
"""

import feedparser
import time
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Free public RSS feeds - no auth token needed
RSS_FEEDS = {
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "decrypt": "https://decrypt.co/feed",
    "bitcoinmagazine": "https://bitcoinmagazine.com/feed",
}

# Simple cache to avoid re-fetching every call (news doesn't change every second)
_cache = {"timestamp": 0, "entries": []}
CACHE_TTL_SECONDS = 300  # 5 minutes


def _fetch_all_feeds():
    """Fetch and merge entries from all RSS feeds."""
    all_entries = []
    for source_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                published_dt = (
                    datetime(*published[:6], tzinfo=timezone.utc) if published else None
                )
                all_entries.append({
                    "source": source_name,
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "link": entry.get("link", ""),
                    "published": published_dt,
                })
        except Exception as e:
            logger.warning(f"Failed to fetch RSS feed {source_name}: {e}")
    return all_entries


def get_latest_news(force_refresh: bool = False):
    """Return cached (or freshly fetched) list of news entries from all feeds."""
    now = time.time()
    if force_refresh or (now - _cache["timestamp"] > CACHE_TTL_SECONDS):
        _cache["entries"] = _fetch_all_feeds()
        _cache["timestamp"] = now
    return _cache["entries"]


# Map common trading symbols to keywords to match against news titles/summaries
SYMBOL_KEYWORDS = {
    "BTC": ["bitcoin", "btc"],
    "ETH": ["ethereum", "eth"],
    "BNB": ["binance", "bnb"],
    "SOL": ["solana", "sol"],
    "XRP": ["ripple", "xrp"],
    "DOGE": ["dogecoin", "doge"],
    "ADA": ["cardano", "ada"],
    "AVAX": ["avalanche", "avax"],
    "LINK": ["chainlink", "link"],
    "DOT": ["polkadot", "dot"],
    "LTC": ["litecoin", "ltc"],
    "BCH": ["bitcoin cash", "bch"],
    "UNI": ["uniswap", "uni"],
    "SUI": ["sui"],
    "TRX": ["tron", "trx"],
}


def get_symbol_news(symbol: str, max_items: int = 5, max_age_hours: int = 24):
    """
    Return recent news entries relevant to a given trading symbol
    (e.g. "BTCUSDT" or "BTC").
    """
    base_symbol = symbol.upper().replace("USDT", "").replace("USD", "")
    keywords = SYMBOL_KEYWORDS.get(base_symbol, [base_symbol.lower()])

    entries = get_latest_news()
    now = datetime.now(timezone.utc)
    matched = []

    for entry in entries:
        text = (entry["title"] + " " + entry["summary"]).lower()
        if any(kw in text for kw in keywords):
            if entry["published"]:
                age_hours = (now - entry["published"]).total_seconds() / 3600
                if age_hours > max_age_hours:
                    continue
            matched.append(entry)

    matched.sort(key=lambda e: e["published"] or now, reverse=True)
    return matched[:max_items]


def has_negative_news_flag(symbol: str, negative_keywords=None):
    """
    Very lightweight heuristic: checks if any recent headline for the symbol
    contains a keyword commonly associated with bearish/negative news
    (hack, exploit, lawsuit, ban, crash, delist, etc).
    Returns True if such a headline is found, along with the matching entry.
    """
    if negative_keywords is None:
        negative_keywords = [
            "hack", "exploit", "lawsuit", "sec charges", "ban", "banned",
            "crash", "delist", "delisting", "rug pull", "scam", "fraud",
            "investigation", "seized", "outage", "halt", "hacked",
        ]

    news_items = get_symbol_news(symbol, max_items=10, max_age_hours=24)
    for item in news_items:
        text = (item["title"] + " " + item["summary"]).lower()
        for kw in negative_keywords:
            if kw in text:
                return True, item
    return False, None


if __name__ == "__main__":
    # Quick manual test
    logging.basicConfig(level=logging.INFO)
    news = get_symbol_news("BTC")
    for n in news:
        print(f"[{n['source']}] {n['title']} -> {n['link']}")
