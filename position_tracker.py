import json
import os
import threading
from datetime import datetime, timezone

STORAGE_PATH = os.environ.get(
    "POSITION_TRACKER_PATH",
    "open_positions.json"
)

_lock = threading.Lock()


def _load():

    if not os.path.exists(STORAGE_PATH):
        return {}

    try:
        with open(STORAGE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("POSITION_TRACKER load error:", e)
        return {}


def _save(data):

    try:
        with open(STORAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("POSITION_TRACKER save error:", e)


def has_open_position(symbol):

    with _lock:
        data = _load()
        return symbol in data


def get_open_position(symbol):

    with _lock:
        data = _load()
        return data.get(symbol)


def get_all_open_positions():

    with _lock:
        return _load()


def open_position(
    symbol,
    mode,
    signal,
    entry_price,
    stop_loss,
    take_profit,
    quantity,
):

    with _lock:

        data = _load()

        data[symbol] = {
            "mode": mode,
            "signal": signal,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "quantity": quantity,
            "opened_at": datetime.now(timezone.utc).isoformat(),
        }

        _save(data)


def close_position(symbol):

    with _lock:

        data = _load()

        if symbol in data:
            del data[symbol]
            _save(data)
