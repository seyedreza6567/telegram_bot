"""
execution_engine.py

Bridges a signal_engine.py result to an actual (or paper) order on
Toobit. This is the ONLY place that should ever call
toobit_client.place_market_order — keep it that way so there's one
choke point to audit.

Trading mode is controlled by config.TRADING_MODE:
  "PAPER" -> nothing is sent to Toobit. The intended order is logged
             and returned as if it had been placed, so the rest of
             the bot (Telegram messages, position bookkeeping) behaves
             identically to live mode. Safe default.
  "LIVE"  -> real orders are sent with real money.
"""

import time

import toobit_client
from config import TRADING_MODE, RISK_PERCENT


class ExecutionError(Exception):
    pass


def _get_step_size(symbol: str) -> float:
    # TODO: pull real stepSize/minQty from /api/v1/exchangeInfo per symbol
    # instead of a hardcoded fallback. Left explicit so it's obvious
    # this needs wiring up before serious LIVE use on low-price coins.
    return 0.001


def calculate_quantity(entry_price: float, stop_loss: float, available_usdt: float,
                        risk_percent: float = None) -> float:
    """
    Position size such that a full stop-loss hit loses exactly
    risk_percent% of available_usdt (before fees/slippage).
    """
    risk_percent = RISK_PERCENT if risk_percent is None else risk_percent

    if entry_price <= 0 or stop_loss <= 0:
        raise ExecutionError("قیمت ورود یا حد ضرر نامعتبر است")

    risk_amount_usdt = available_usdt * (risk_percent / 100.0)
    risk_per_contract = abs(entry_price - stop_loss)

    if risk_per_contract <= 0:
        raise ExecutionError("فاصله ورود تا حد ضرر صفر است")

    quantity = risk_amount_usdt / risk_per_contract

    step = _get_step_size(entry_price)
    quantity = max(step, round(quantity / step) * step)
    return quantity


def execute_signal(symbol: str, signal: str, entry: float, stop_loss: float, take_profit: float):
    """
    signal: "LONG" or "SHORT"
    Returns a dict describing what happened (for the Telegram message).
    Raises ExecutionError on anything that should block the trade.
    """
    if signal not in ("LONG", "SHORT"):
        raise ExecutionError("سیگنال نامعتبر است")

    # --- guard: don't stack a second position on the same symbol ---
    if TRADING_MODE == "LIVE":
        if toobit_client.has_open_position(symbol):
            raise ExecutionError(f"{symbol}: پوزیشن باز از قبل وجود دارد — رد شد")
        available_usdt = toobit_client.get_available_usdt()
    else:
        # PAPER mode: no real balance call needed to place a fake order,
        # but you can still wire this to a fixed paper balance if you
        # want quantity numbers that mean something in the message.
        available_usdt = 1000.0  # placeholder paper balance

    quantity = calculate_quantity(entry, stop_loss, available_usdt)

    open_side = "BUY_OPEN" if signal == "LONG" else "SELL_OPEN"
    close_side = "SELL_CLOSE" if signal == "LONG" else "BUY_CLOSE"

    result = {
        "mode": TRADING_MODE,
        "symbol": symbol,
        "signal": signal,
        "quantity": quantity,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "orders": [],
    }

    if TRADING_MODE != "LIVE":
        result["orders"].append({
            "type": "PAPER_MARKET_OPEN",
            "side": open_side,
            "quantity": quantity,
            "note": "شبیه‌سازی — هیچ درخواستی به Toobit ارسال نشد",
        })
        return result

    # ---- LIVE: real orders below this line ----
    open_order = toobit_client.place_market_order(
        symbol=symbol,
        side=open_side,
        quantity=str(quantity),
        client_order_id=f"auto_{symbol}_{int(time.time())}",
    )
    result["orders"].append({"type": "MARKET_OPEN", "response": open_order})

    sl_order = toobit_client.place_stop_order(
        symbol=symbol,
        side=close_side,
        quantity=str(quantity),
        stop_price=stop_loss,
        reduce_only=True,
    )
    result["orders"].append({"type": "STOP_LOSS", "response": sl_order})

    tp_order = toobit_client.place_stop_order(
        symbol=symbol,
        side=close_side,
        quantity=str(quantity),
        stop_price=take_profit,
        reduce_only=True,
    )
    result["orders"].append({"type": "TAKE_PROFIT", "response": tp_order})

    return result
