import time
import requests

import config


# =========================================================
# SETTINGS
# =========================================================
CRYPTOPANIC_URL = "https://cryptopanic.com/api/v1/posts/"

CACHE_TTL_SECONDS = 600
REQUEST_TIMEOUT = 8
POST_LIMIT = 30

NEWS_BLOCK_THRESHOLD = float(getattr(config, "NEWS_BLOCK_THRESHOLD", 0.35))
MIN_POSTS_FOR_BLOCK = 3

_cache = {}


def _symbol_to_currency(symbol):
    return symbol.split("-")[0].upper()


def _empty_result(reason):
    return {
        "available": False,
        "bias": 0.0,
        "label": "NEUTRAL",
        "post_count": 0,
        "important_count": 0,
        "reason": reason,
    }


def neutral_result(reason="غیرفعال"):
    return _empty_result(reason)


# =========================================================
# FETCH + SCORE
# =========================================================
def get_news_bias(symbol):
    currency = _symbol_to_currency(symbol)

    cached = _cache.get(currency)
    if cached and (time.time() - cached["ts"]) < CACHE_TTL_SECONDS:
        return cached["data"]

    api_key = getattr(config, "CRYPTOPANIC_API_KEY", None)
    if not api_key:
        result = _empty_result("کلید CryptoPanic تنظیم نشده")
        _cache[currency] = {"ts": time.time(), "data": result}
        return result

    params = {
        "auth_token": api_key,
        "currencies": currency,
        "public": "true",
    }

    try:
        response = requests.get(CRYPTOPANIC_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        posts = payload.get("results", [])[:POST_LIMIT]
    except Exception as e:
        result = _empty_result(f"خطای دریافت اخبار: {e}")
        _cache[currency] = {"ts": time.time(), "data": result}
        return result

    if not posts:
        result = _empty_result("خبری یافت نشد")
        _cache[currency] = {"ts": time.time(), "data": result}
        return result

    positive_score = 0.0
    negative_score = 0.0
    important_count = 0

    for post in posts:
        votes = post.get("votes", {}) or {}
        positive = float(votes.get("positive", 0) or 0)
        negative = float(votes.get("negative", 0) or 0)
        liked = float(votes.get("liked", 0) or 0)
        disliked = float(votes.get("disliked", 0) or 0)
        important = float(votes.get("important", 0) or 0)

        weight = 1.0
        if important > 0:
            important_count += 1
            weight = 1.5

        positive_score += (positive + liked) * weight
        negative_score += (negative + disliked) * weight

    total = positive_score + negative_score

    if total <= 0:
        bias = 0.0
    else:
        bias = (positive_score - negative_score) / total

    bias = max(-1.0, min(1.0, bias))

    if bias >= 0.2:
        label = "BULLISH"
    elif bias <= -0.2:
        label = "BEARISH"
    else:
        label = "NEUTRAL"

    result = {
        "available": True,
        "bias": round(bias, 3),
        "label": label,
        "post_count": len(posts),
        "important_count": important_count,
        "reason": "",
    }

    _cache[currency] = {"ts": time.time(), "data": result}
    return result


def should_block(signal, news):
    if not news.get("available"):
        return False
    if news.get("post_count", 0) < MIN_POSTS_FOR_BLOCK:
        return False

    bias = news.get("bias", 0.0)

    if signal == "LONG" and bias <= -NEWS_BLOCK_THRESHOLD:
        return True
    if signal == "SHORT" and bias >= NEWS_BLOCK_THRESHOLD:
        return True
    return False


if __name__ == "__main__":
    for test_symbol in ["BTC-SWAP-USDT", "UNI-SWAP-USDT"]:
        print(test_symbol, "->", get_news_bias(test_symbol))
