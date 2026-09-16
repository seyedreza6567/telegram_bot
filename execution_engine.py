import config
import position_tracker
import toobit_client
from scanner import get_klines


class ExecutionError(Exception):
    """خطای عادی اجرا - چیزی برای اطلاع فوری به کاربر نیست
    (مثلاً پوزیشن از قبل باز است، یا حجم خیلی کوچک است)."""
    pass


class UnprotectedPositionError(ExecutionError):
    """
    وضعیت بحرانی: سفارش باز کردن پوزیشن روی صرافی موفق بوده اما
    ثبت حد ضرر/حد سود شکست خورده و حتی تلاش برای بستن اضطراری
    (emergency flatten) هم ناموفق بوده - یعنی الان یک پوزیشن واقعی
    و کاملاً بدون محافظت روی صرافی باز است. این باید همیشه فوراً
    و به‌صورت جدا از سایر خطاها به کاربر اطلاع داده شود.
    """
    pass


# =========================================================
# محاسبه حجم معامله
#
# FIX: قبلاً این تابع entry_price را به‌جای symbol به تابع
# step-size می‌داد، و آن تابع هم اصلاً از ورودی‌اش استفاده
# نمی‌کرد و همیشه 0.001 هاردکد برمی‌گرداند - یعنی حجم واقعی
# برای همه‌ی نمادها (حتی DOGE/XRP با قیمت خیلی پایین‌تر) یکسان
# و غلط محاسبه می‌شد. حالا از step_size/min_qty واقعی نماد
# استفاده می‌شود و به‌جای round، همیشه به پایین گرد می‌شود
# (floor) تا هیچ‌وقت بیشتر از ریسک مجاز باز نشود.
# =========================================================

def calculate_quantity(symbol, entry_price, stop_loss, balance):

    risk_amount = balance * (config.RISK_PERCENT / 100.0)

    risk_per_unit = abs(entry_price - stop_loss)

    if risk_per_unit <= 0:
        raise ExecutionError("فاصله ورود تا حد ضرر نامعتبر است.")

    raw_quantity = risk_amount / risk_per_unit

    if config.TRADING_MODE == "LIVE":

        quantity = toobit_client.round_quantity_down(symbol, raw_quantity)

        filters = toobit_client.get_symbol_filters(symbol)

        if quantity < filters["min_qty"]:
            raise ExecutionError(
                f"حجم محاسبه‌شده ({quantity}) کمتر از حداقل مجاز "
                f"({filters['min_qty']}) است."
            )

    else:

        # در PAPER هم دقت معقولی اعمال می‌کنیم تا اعداد واقعی‌تر
        # به نظر برسند، بدون نیاز به اتصال واقعی به صرافی.
        quantity = round(raw_quantity, 4)

    return quantity


def _get_balance():

    if config.TOOBIT_API_KEY and config.TOOBIT_SECRET_KEY:

        try:
            return toobit_client.get_available_balance_usdt()
        except Exception as e:
            print("BALANCE fetch error, falling back:", e)

    return config.PAPER_FALLBACK_BALANCE_USDT


# =========================================================
# اجرای سیگنال
# =========================================================

def execute_signal(symbol, signal, entry, stop_loss, take_profit):

    if signal not in ("LONG", "SHORT"):
        raise ExecutionError("سیگنال نامعتبر است.")

    # ---- محافظ Stacking: هم در PAPER و هم در LIVE ----
    # قبلاً این محافظ فقط در حالت LIVE اجرا می‌شد - در PAPER هیچ
    # محافظتی نبود، یعنی یک حلقه‌ی خودکار می‌توانست هر بار اسکن
    # یک پوزیشن فرضی جدید برای همان نماد باز کند تا وقتی سیگنال
    # فعال بود.
    if position_tracker.has_open_position(symbol):
        raise ExecutionError(f"پوزیشن باز موجود برای {symbol}.")

    balance = _get_balance()

    quantity = calculate_quantity(symbol, entry, stop_loss, balance)

    if config.TRADING_MODE == "LIVE":

        return _execute_live(
            symbol, signal, entry, stop_loss, take_profit, quantity
        )

    return _execute_paper(
        symbol, signal, entry, stop_loss, take_profit, quantity
    )


def _execute_paper(symbol, signal, entry, stop_loss, take_profit, quantity):

    position_tracker.open_position(
        symbol=symbol,
        mode="PAPER",
        signal=signal,
        entry_price=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        quantity=quantity,
    )

    return {
        "mode": "PAPER",
        "quantity": quantity,
    }


def _execute_live(symbol, signal, entry, stop_loss, take_profit, quantity):

    open_side = "buy" if signal == "LONG" else "sell"
    close_side = "sell" if signal == "LONG" else "buy"

    try:
        toobit_client.place_market_order(symbol, open_side, quantity)
    except Exception as e:
        raise ExecutionError(f"باز کردن پوزیشن ناموفق بود: {e}")

    # ---- FIX: قبلاً position_tracker.open_position() فقط بعد از
    # موفقیت *هر دو* سفارش SL و TP صدا زده می‌شد. یعنی اگر یکی از
    # آن‌ها شکست می‌خورد، یک پوزیشن واقعی و بدون‌ردیابی روی صرافی
    # باقی می‌ماند. حالا هر خطا در SL/TP بلافاصله باعث تلاش برای
    # بستن اضطراری پوزیشن می‌شود.
    try:

        toobit_client.place_stop_loss(symbol, close_side, quantity, stop_loss)
        toobit_client.place_take_profit(symbol, close_side, quantity, take_profit)

    except Exception as protection_error:

        try:

            toobit_client.close_position_market(symbol, close_side, quantity)

            raise ExecutionError(
                f"ثبت حد ضرر/حد سود ناموفق بود، پوزیشن بسته شد: "
                f"{protection_error}"
            )

        except ExecutionError:

            raise

        except Exception as flatten_error:

            raise UnprotectedPositionError(
                f"ثبت حد ضرر/حد سود ناموفق بود ({protection_error}) "
                f"و بستن اضطراری هم ناموفق بود ({flatten_error})."
            )

    position_tracker.open_position(
        symbol=symbol,
        mode="LIVE",
        signal=signal,
        entry_price=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        quantity=quantity,
    )

    return {
        "mode": "LIVE",
        "quantity": quantity,
    }


# =========================================================
# همگام‌سازی پوزیشن‌ها (تشخیص بسته‌شدن‌ها)
# =========================================================

def _get_last_price(symbol):

    try:

        df = get_klines(symbol=symbol, interval="1h", limit=2)

        if df is not None and len(df) > 0:
            return float(df["close"].iloc[-1])

    except Exception as e:
        print(f"SYNC price error {symbol}: {e}")

    return None


def sync_positions():

    closed = []

    positions = position_tracker.get_all_open_positions()

    for symbol, position in positions.items():

        mode = position.get("mode")

        if mode == "LIVE":

            try:
                still_open = toobit_client.has_open_position(symbol)
            except Exception as e:
                print(f"SYNC live-check error {symbol}: {e}")
                continue

            if still_open:
                continue

            # پوزیشن دیگر روی صرافی باز نیست - یعنی SL یا TP اجرا شده.
            price = _get_last_price(symbol) or position.get("entry_price")

            result = _guess_result(position, price)

            position_tracker.close_position(symbol)

            closed.append({"symbol": symbol, "result": result})

        else:

            price = _get_last_price(symbol)

            if price is None:
                continue

            signal = position.get("signal")
            stop_loss = position.get("stop_loss")
            take_profit = position.get("take_profit")

            hit_stop = (
                (signal == "LONG" and price <= stop_loss)
                or
                (signal == "SHORT" and price >= stop_loss)
            )

            hit_target = (
                (signal == "LONG" and price >= take_profit)
                or
                (signal == "SHORT" and price <= take_profit)
            )

            if not hit_stop and not hit_target:
                continue

            result = "WIN" if hit_target else "LOSS"

            position_tracker.close_position(symbol)

            closed.append({"symbol": symbol, "result": result})

    return closed


def _guess_result(position, price):

    signal = position.get("signal")
    entry = position.get("entry_price")
    take_profit = position.get("take_profit")

    if price is None or entry is None or take_profit is None:
        return "UNKNOWN"

    reward_distance = abs(take_profit - entry)

    if reward_distance <= 0:
        return "UNKNOWN"

    if signal == "LONG":
        progress = (price - entry) / reward_distance
    else:
        progress = (entry - price) / reward_distance

    return "WIN" if progress > 0 else "LOSS"
