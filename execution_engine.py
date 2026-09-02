"""
execution_engine.py

Bridges a signal_engine.py result to an actual (or paper) order on
Toobit. This is the ONLY place that should ever call
toobit_client.place_market_order - keep it that way so there's one
choke point to audit.

Trading mode is controlled by config.TRADING_MODE:
  "PAPER" -> nothing is sent to Toobit's order endpoints. The
             intended order is logged and returned as if it had been
             placed, so the rest of the bot (Telegram messages,
             position bookkeeping) behaves identically to live mode.
             Safe default.
  "LIVE"  -> real orders are sent with real money.

Regardless of mode, position_tracker.py keeps a local record of what
this engine believes is currently open per symbol, so an automatic
scan loop never stacks a second position on a signal that's still
active on the next cycle.
"""

import math
import time

import toobit_client
import position_tracker
import scanner
from config import TRADING_MODE, RISK_PERCENT


class ExecutionError(Exception):
    pass


def calculate_quantity(symbol: str, entry_price: float, stop_loss: float,
                        available_usdt: float, risk_percent: float = None) -> float:
    """
    Position size such that a full stop-loss hit loses exactly
    risk_percent% of available_usdt (before fees/slippage).

    BUG FIX: this used to call a step-size helper with entry_price
    instead of the symbol, and that helper ignored its argument
    entirely and returned a hardcoded 0.001 for every coin. That's
    wrong for both cheap coins (rounds away too much precision) and
    expensive/large-tick coins (could round to an invalid quantity).
    Now it looks up the symbol's real lot size from Toobit.
    """
    risk_percent = RISK_PERCENT if risk_percent is None else risk_percent

    if entry_price <= 0 or stop_loss <= 0:
        raise ExecutionError("قیمت ورود یا حد ضرر نامعتبر است")

    risk_amount_usdt = available_usdt * (risk_percent / 100.0)
    risk_per_contract = abs(entry_price - stop_loss)

    if risk_per_contract <= 0:
        raise ExecutionError("فاصله ورود تا حد ضرر صفر است")

    raw_quantity = risk_amount_usdt / risk_per_contract

    filters = toobit_client.get_symbol_filters(symbol)
    step = filters["step_size"]
    min_qty = filters["min_qty"]

    if step <= 0:
        step = 0.001

    # Floor (never round up) to the exchange's step size - rounding
    # up would silently risk more than risk_percent intended.
    quantity = math.floor(raw_quantity / step) * step
    quantity = round(quantity, 10)

    if quantity < min_qty:
        raise ExecutionError(
            f"{symbol}: حجم محاسبه‌شده ({quantity}) کمتر از حداقل مجاز "
            f"صرافی ({min_qty}) است - با ریسک {risk_percent}% این معامله "
            f"قابل اجرا نیست، رد شد."
        )

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
    # BUG FIX: this guard used to only run in LIVE mode. PAPER mode had
    # no protection at all, so a signal that stayed active across scan
    # cycles would "open" a new fake position every single cycle.
    if position_tracker.is_open(symbol):
        raise ExecutionError(f"{symbol}: پوزیشن باز از قبل ثبت شده (tracker) - رد شد")

    if TRADING_MODE == "LIVE":
        if toobit_client.has_open_position(symbol):
            raise ExecutionError(f"{symbol}: پوزیشن باز از قبل روی صرافی وجود دارد - رد شد")
        available_usdt = toobit_client.get_available_usdt()
    else:
        # PAPER mode: no order is ever sent, but if API keys are already
        # configured we still pull the real balance so the simulated
        # quantity numbers mean something. Falls back to a placeholder
        # if that call fails for any reason (missing keys, network, etc).
        try:
            available_usdt = toobit_client.get_available_usdt()
        except Exception as e:
            print(f"WARN paper balance fetch failed, using placeholder: {e}")
            available_usdt = 1000.0

    quantity = calculate_quantity(symbol, entry, stop_loss, available_usdt)

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
            "note": "شبیه‌سازی - هیچ درخواستی به Toobit ارسال نشد",
        })
        position_tracker.open_position(symbol, {
            "signal": signal,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "quantity": quantity,
            "mode": "PAPER",
            "opened_at": time.time(),
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

    position_tracker.open_position(symbol, {
        "signal": signal,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "quantity": quantity,
        "mode": "LIVE",
        "opened_at": time.time(),
    })

    return result


def sync_positions():
    """
    Call at the start of each auto-scan cycle, BEFORE looking for new
    signals. Clears local tracker entries for symbols whose position
    has actually closed since the last check:

      - LIVE: ask Toobit directly with has_open_position(). If Toobit
        no longer reports a position (SL/TP filled, or closed some
        other way), clear the local tracker entry too.
      - PAPER: nothing on Toobit ever knew about this trade, so this
        is the only way to find out - compare the latest 1h close
        against the tracked stop_loss/take_profit.

    Returns a list of {"symbol", "result", "detail"} for positions
    that closed this cycle, so the caller can notify the user.
    """
    closed = []

    for symbol, pos in list(position_tracker.all_positions().items()):
        if pos.get("mode") == "LIVE":
            try:
                if not toobit_client.has_open_position(symbol):
                    position_tracker.close_position(symbol)
                    closed.append({"symbol": symbol, "result": "CLOSED_ON_EXCHANGE", "detail": pos})
            except Exception as e:
                print(f"WARN sync_positions LIVE {symbol}: {e}")
            continue

        # PAPER
        try:
            df = scanner.get_klines(symbol=symbol, interval="1h", limit=2)
            if df is None or len(df) == 0:
                continue

            price = float(df["close"].iloc[-1])
            signal = pos["signal"]
            sl = pos["stop_loss"]
            tp = pos["take_profit"]

            hit = None
            if signal == "LONG":
                if price <= sl:
                    hit = "SL"
                elif price >= tp:
                    hit = "TP"
            else:
                if price >= sl:
                    hit = "SL"
                elif price <= tp:
                    hit = "TP"

            if hit:
                position_tracker.close_position(symbol)
                closed.append({
                    "symbol": symbol,
                    "result": hit,
                    "detail": pos,
                    "close_price": price,
                })
        except Exception as e:
            print(f"WARN sync_positions PAPER {symbol}: {e}")

    return closed
