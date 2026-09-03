"""
news_engine.py
---------------
Free crypto news engine using public RSS feeds.

Sources:
- CoinDesk
- Cointelegraph
- Decrypt
- Bitcoin Magazine

No API key required.
"""

import feedparser
import time
import logging
import re
from datetime import datetime, timezone


logger = logging.getLogger(__name__)


# =========================================================
# RSS FEEDS
# =========================================================

RSS_FEEDS = {
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "decrypt": "https://decrypt.co/feed",
    "bitcoinmagazine": "https://bitcoinmagazine.com/feed",
}


# =========================================================
# CACHE
# =========================================================

_cache = {
    "timestamp": 0,
    "entries": []
}

CACHE_TTL_SECONDS = 300


# =========================================================
# SYMBOL KEYWORDS
# =========================================================

SYMBOL_KEYWORDS = {
    "BTC": [
        "bitcoin",
        "btc"
    ],

    "ETH": [
        "ethereum",
        "ether",
        "eth"
    ],

    "BNB": [
        "binance coin",
        "bnb"
    ],

    "SOL": [
        "solana",
        "sol"
    ],

    "XRP": [
        "ripple",
        "xrp"
    ],

    "DOGE": [
        "dogecoin",
        "doge"
    ],

    "ADA": [
        "cardano",
        "ada"
    ],

    "AVAX": [
        "avalanche",
        "avax"
    ],

    "LINK": [
        "chainlink",
        "link"
    ],

    "DOT": [
        "polkadot",
        "dot"
    ],

    "LTC": [
        "litecoin",
        "ltc"
    ],

    "BCH": [
        "bitcoin cash",
        "bch"
    ],

    "UNI": [
        "uniswap",
        "uni"
    ],

    "SUI": [
        "sui"
    ],

    "TRX": [
        "tron",
        "trx"
    ],
}


# =========================================================
# NEGATIVE NEWS KEYWORDS
# =========================================================

NEGATIVE_KEYWORDS = [
    "hack",
    "hacked",
    "hacking",
    "exploit",
    "exploited",
    "security breach",
    "breach",
    "lawsuit",
    "sued",
    "sec charges",
    "sec charged",
    "sec lawsuit",
    "ban",
    "banned",
    "regulatory crackdown",
    "crackdown",
    "crash",
    "collapse",
    "delist",
    "delisted",
    "delisting",
    "rug pull",
    "scam",
    "fraud",
    "fraudulent",
    "investigation",
    "investigated",
    "seized",
    "seizure",
    "outage",
    "halt",
    "halted",
    "insolvency",
    "insolvent",
    "bankruptcy",
    "bankrupt",
    "stolen",
    "stolen funds",
    "attack",
    "attacked",
    "vulnerability",
    "vulnerable",
]


# =========================================================
# POSITIVE NEWS KEYWORDS
# =========================================================

POSITIVE_KEYWORDS = [
    "approval",
    "approved",
    "etf approval",
    "etf approved",
    "partnership",
    "partnered",
    "adoption",
    "adopted",
    "launch",
    "launched",
    "integration",
    "integrated",
    "upgrade",
    "upgraded",
    "bullish",
    "surge",
    "rally",
    "record high",
    "all-time high",
    "ath",
    "institutional buying",
    "institutional adoption",
    "inflows",
    "investment",
    "invested",
    "funding",
    "major partnership",
]


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def _normalize_text(text):
    """
    Normalize text for keyword matching.
    """

    if text is None:
        return ""

    text = str(text).lower()

    # Remove HTML tags
    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    # Normalize whitespace
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# SYMBOL NORMALIZATION
# =========================================================

def _normalize_symbol(symbol):
    """
    Convert exchange symbols into base symbols.

    Examples:

    BTC
    BTCUSDT
    BTC-USD
    BTC-USDT
    BTC-SWAP-USDT
    ETH-SWAP-USDT

    -> BTC
    -> ETH
    """

    if symbol is None:
        return ""

    symbol = str(
        symbol
    ).upper().strip()

    # -----------------------------------------------------
    # Toobit futures format
    # BTC-SWAP-USDT
    # -----------------------------------------------------

    if "-SWAP-" in symbol:

        base = symbol.split(
            "-SWAP-",
            1
        )[0]

        return base.strip("-").upper()

    # -----------------------------------------------------
    # Other common formats
    # -----------------------------------------------------

    suffixes = [
        "-USDT",
        "-USD",
        "-USDC",
        "_USDT",
        "_USD",
        "_USDC",
    ]

    for suffix in suffixes:

        if symbol.endswith(suffix):

            symbol = symbol[
                :-len(suffix)
            ]

            break

    # -----------------------------------------------------
    # Remove remaining separators
    # -----------------------------------------------------

    symbol = symbol.replace(
        "USDT",
        ""
    )

    symbol = symbol.replace(
        "USDC",
        ""
    )

    symbol = symbol.replace(
        "USD",
        ""
    )

    symbol = symbol.replace(
        "-",
        ""
    )

    symbol = symbol.replace(
        "_",
        ""
    )

    return symbol.strip().upper()


# =========================================================
# FETCH ALL RSS FEEDS
# =========================================================

def _fetch_all_feeds():
    """
    Fetch and merge RSS entries from all sources.
    """

    all_entries = []

    for source_name, url in RSS_FEEDS.items():

        try:

            feed = feedparser.parse(
                url
            )

            if getattr(
                feed,
                "bozo",
                False
            ):

                logger.warning(
                    "RSS warning: %s",
                    source_name
                )

            for entry in feed.entries:

                published = (
                    entry.get(
                        "published_parsed"
                    )
                    or
                    entry.get(
                        "updated_parsed"
                    )
                )

                published_dt = None

                if published:

                    try:

                        published_dt = datetime(
                            *published[:6],
                            tzinfo=timezone.utc
                        )

                    except Exception:

                        published_dt = None

                title = entry.get(
                    "title",
                    ""
                )

                summary = entry.get(
                    "summary",
                    ""
                )

                link = entry.get(
                    "link",
                    ""
                )

                all_entries.append({

                    "source":
                        source_name,

                    "title":
                        title,

                    "summary":
                        summary,

                    "link":
                        link,

                    "published":
                        published_dt
                })

        except Exception as e:

            logger.warning(
                "Failed to fetch RSS feed %s: %s",
                source_name,
                e
            )

    return all_entries


# =========================================================
# GET LATEST NEWS
# =========================================================

def get_latest_news(
    force_refresh=False
):
    """
    Return cached news or refresh RSS feeds.
    """

    now = time.time()

    cache_expired = (
        now - _cache["timestamp"]
        > CACHE_TTL_SECONDS
    )

    if (
        force_refresh
        or
        cache_expired
    ):

        entries = _fetch_all_feeds()

        _cache["entries"] = entries

        _cache["timestamp"] = now

    return _cache["entries"]


# =========================================================
# MATCH SYMBOL NEWS
# =========================================================

def get_symbol_news(
    symbol,
    max_items=5,
    max_age_hours=24
):
    """
    Return recent news relevant to the trading symbol.

    Supports Toobit symbols such as:

        BTC-SWAP-USDT
        ETH-SWAP-USDT
        SOL-SWAP-USDT
    """

    base_symbol = _normalize_symbol(
        symbol
    )

    if not base_symbol:

        return []

    keywords = SYMBOL_KEYWORDS.get(
        base_symbol,
        [base_symbol.lower()]
    )

    entries = get_latest_news()

    now = datetime.now(
        timezone.utc
    )

    matched = []

    for entry in entries:

        title = _normalize_text(
            entry.get(
                "title",
                ""
            )
        )

        summary = _normalize_text(
            entry.get(
                "summary",
                ""
            )
        )

        text = (
            title
            + " "
            + summary
        )

        # -------------------------------------------------
        # Symbol matching
        # -------------------------------------------------

        symbol_found = False

        for keyword in keywords:

            keyword = _normalize_text(
                keyword
            )

            if not keyword:
                continue

            # Word-aware matching
            pattern = (
                r"(?<![a-z0-9])"
                + re.escape(keyword)
                + r"(?![a-z0-9])"
            )

            if re.search(
                pattern,
                text
            ):

                symbol_found = True
                break

        if not symbol_found:
            continue

        # -------------------------------------------------
        # Age filter
        # -------------------------------------------------

        published = entry.get(
            "published"
        )

        if published:

            try:

                age_hours = (
                    now - published
                ).total_seconds() / 3600

                # Ignore old news
                if age_hours > max_age_hours:
                    continue

                # Ignore obviously malformed future dates
                if age_hours < -1:
                    continue

            except Exception:

                pass

        matched.append(
            entry
        )

    # -----------------------------------------------------
    # Newest first
    # -----------------------------------------------------

    matched.sort(
        key=lambda item:
            item.get(
                "published"
            ) or now,
        reverse=True
    )

    return matched[
        :max_items
    ]


# =========================================================
# NEGATIVE NEWS DETECTION
# =========================================================

def has_negative_news_flag(
    symbol,
    negative_keywords=None
):
    """
    Detect recent bearish/negative news.

    Returns:

        (True, matching_entry)

    or:

        (False, None)
    """

    if negative_keywords is None:

        negative_keywords = (
            NEGATIVE_KEYWORDS
        )

    news_items = get_symbol_news(
        symbol,
        max_items=10,
        max_age_hours=24
    )

    for item in news_items:

        title = _normalize_text(
            item.get(
                "title",
                ""
            )
        )

        summary = _normalize_text(
            item.get(
                "summary",
                ""
            )
        )

        text = (
            title
            + " "
            + summary
        )

        for keyword in negative_keywords:

            if _normalize_text(
                keyword
            ) in text:

                return True, item

    return False, None


# =========================================================
# POSITIVE NEWS DETECTION
# =========================================================

def has_positive_news_flag(
    symbol,
    positive_keywords=None
):
    """
    Detect recent positive/bullish news.

    Returns:

        (True, matching_entry)

    or:

        (False, None)
    """

    if positive_keywords is None:

        positive_keywords = (
            POSITIVE_KEYWORDS
        )

    news_items = get_symbol_news(
        symbol,
        max_items=10,
        max_age_hours=24
    )

    for item in news_items:

        title = _normalize_text(
            item.get(
                "title",
                ""
            )
        )

        summary = _normalize_text(
            item.get(
                "summary",
                ""
            )
        )

        text = (
            title
            + " "
            + summary
        )

        for keyword in positive_keywords:

            if _normalize_text(
                keyword
            ) in text:

                return True, item

    return False, None


# =========================================================
# NEWS BIAS
# =========================================================

def get_news_bias(symbol):
    """
    Analyze recent news sentiment.

    Output:

    {
        "available": True/False,
        "label": "BULLISH"/"BEARISH"/"NEUTRAL",
        "post_count": int
    }

    Important:

    News does NOT create a trading signal by itself.

    It only provides directional context.
    """

    result = {
        "available": False,
        "label": "NEUTRAL",
        "post_count": 0
    }

    try:

        news_items = get_symbol_news(
            symbol,
            max_items=10,
            max_age_hours=24
        )

        if news_items is None:

            return result

        result["available"] = True

        result["post_count"] = len(
            news_items
        )

        if len(news_items) == 0:

            return result

        bearish_score = 0
        bullish_score = 0

        # -------------------------------------------------
        # Analyze each article
        # -------------------------------------------------

        for item in news_items:

            title = _normalize_text(
                item.get(
                    "title",
                    ""
                )
            )

            summary = _normalize_text(
                item.get(
                    "summary",
                    ""
                )
            )

            text = (
                title
                + " "
                + summary
            )

            negative_hits = 0
            positive_hits = 0

            for keyword in NEGATIVE_KEYWORDS:

                if _normalize_text(
                    keyword
                ) in text:

                    negative_hits += 1

            for keyword in POSITIVE_KEYWORDS:

                if _normalize_text(
                    keyword
                ) in text:

                    positive_hits += 1

            # A clearly negative headline gets bearish weight.
            if negative_hits > 0:
                bearish_score += (
                    min(
                        negative_hits,
                        3
                    )
                )

            # Positive headline gets bullish weight.
            if positive_hits > 0:
                bullish_score += (
                    min(
                        positive_hits,
                        3
                    )
                )

        # -------------------------------------------------
        # Final sentiment
        # -------------------------------------------------

        if (
            bearish_score > bullish_score
            and
            bearish_score > 0
        ):

            result["label"] = "BEARISH"

        elif (
            bullish_score > bearish_score
            and
            bullish_score > 0
        ):

            result["label"] = "BULLISH"

        else:

            result["label"] = "NEUTRAL"

    except Exception as e:

        logger.warning(
            "News bias failed for %s: %s",
            symbol,
            e
        )

        return {
            "available": False,
            "label": "NEUTRAL",
            "post_count": 0
        }

    return result


# =========================================================
# NEUTRAL RESULT
# =========================================================

def neutral_result(
    reason=None
):
    """
    Safe neutral result.

    Kept for compatibility with older
    signal_engine versions.
    """

    result = {
        "available": False,
        "label": "NEUTRAL",
        "post_count": 0
    }

    if reason:
        result["reason"] = str(
            reason
        )

    return result


# =========================================================
# SHOULD BLOCK SIGNAL
# =========================================================

def should_block(
    signal,
    news
):
    """
    Decide whether news should block a technical signal.

    Rules:

        BEARISH + LONG
            -> BLOCK

        BEARISH + SHORT
            -> ALLOW

        BULLISH + SHORT
            -> BLOCK

        BULLISH + LONG
            -> ALLOW

        NEUTRAL
            -> ALLOW

    News NEVER creates a signal.
    """

    if not isinstance(
        news,
        dict
    ):

        return False

    label = news.get(
        "label",
        "NEUTRAL"
    )

    signal = str(
        signal
    ).upper()

    # -----------------------------------------------------
    # Bearish news
    # -----------------------------------------------------

    if label == "BEARISH":

        if signal == "LONG":
            return True

        if signal == "SHORT":
            return False

    # -----------------------------------------------------
    # Bullish news
    # -----------------------------------------------------

    if label == "BULLISH":

        if signal == "SHORT":
            return True

        if signal == "LONG":
            return False

    # -----------------------------------------------------
    # Neutral
    # -----------------------------------------------------

    return False


# =========================================================
# MANUAL TEST
# =========================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO
    )

    test_symbols = [
        "BTC-SWAP-USDT",
        "ETH-SWAP-USDT",
        "SOL-SWAP-USDT"
    ]

    print()
    print(
        "========================================"
    )
    print(
        "NEWS ENGINE TEST"
    )
    print(
        "========================================"
    )

    # Force fresh RSS fetch for manual test
    get_latest_news(
        force_refresh=True
    )

    for symbol in test_symbols:

        print()
        print(
            "----------------------------------------"
        )

        print(
            "SYMBOL:",
            symbol
        )

        normalized = _normalize_symbol(
            symbol
        )

        print(
            "BASE SYMBOL:",
            normalized
        )

        news = get_symbol_news(
            symbol,
            max_items=5,
            max_age_hours=24
        )

        print(
            "POST COUNT:",
            len(news)
        )

        bias = get_news_bias(
            symbol
        )

        print(
            "BIAS:",
            bias
        )

        for item in news:

            print(
                f"[{item.get('source')}] "
                f"{item.get('title')} "
                f"-> "
                f"{item.get('link')}"
            )

    print()
    print(
        "========================================"
    )
    print(
        "NEWS ENGINE TEST FINISHED"
    )
    print(
        "========================================"
    )
