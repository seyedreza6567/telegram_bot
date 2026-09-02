"""
position_tracker.py

Lightweight local bookkeeping of which symbols currently have an
open auto-trading position.

Why this exists: execution_engine.execute_signal() previously only
guarded against stacking a second position in LIVE mode (by asking
Toobit directly). PAPER mode had NO such guard - if a signal stayed
active across several scan cycles (which is normal; trends don't
flip every 15 minutes), an automatic scan loop would "open" a brand
new fake position every single cycle for as long as the signal
persisted. This module fixes that for both modes, and also gives
PAPER mode a way to notice its own simulated SL/TP being hit (Toobit
has no record of a paper trade, so nothing else can tell us that).

Persisted to a JSON file so a bot restart doesn't forget about open
paper positions and double-open on the next scan.
"""

import json
import os
import threading

_LOCK = threading.Lock()
_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "open_positions.json")


def _load():
    if not os.path.exists(_FILE):
        return {}
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data):
    with open(_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_open(symbol: str) -> bool:
    with _LOCK:
        return symbol in _load()


def get_position(symbol: str):
    with _LOCK:
        return _load().get(symbol)


def open_position(symbol: str, info: dict):
    with _LOCK:
        data = _load()
        data[symbol] = info
        _save(data)


def close_position(symbol: str):
    with _LOCK:
        data = _load()
        if symbol in data:
            data.pop(symbol)
            _save(data)


def all_positions() -> dict:
    with _LOCK:
        return _load()
