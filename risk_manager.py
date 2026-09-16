MIN_RISK_REWARD = 1.2


def build_risk(signal, entry_price, stop_loss, take_profit):
    """
    از روی سیگنال خام (LONG/SHORT) و سطوح قیمتی خروجی analyze()،
    یک دیکشنری ریسک آماده برای اجرا/نمایش می‌سازد؛ شامل tp1
    (خروج جزئی زودتر، نصف فاصله تا TP نهایی) و اعتبارسنجی نسبت
    ریسک به ریوارد.
    """

    result = {
        "valid": False,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "tp1": None,
        "take_profit": take_profit,
    }

    if signal not in ("LONG", "SHORT"):
        return result

    if entry_price is None or stop_loss is None or take_profit is None:
        return result

    risk_distance = abs(entry_price - stop_loss)

    if risk_distance <= 0:
        return result

    reward_distance = abs(take_profit - entry_price)

    risk_reward = reward_distance / risk_distance

    if risk_reward < MIN_RISK_REWARD:
        return result

    if signal == "LONG":
        tp1 = entry_price + (reward_distance * 0.5)
    else:
        tp1 = entry_price - (reward_distance * 0.5)

    result["valid"] = True
    result["tp1"] = round(tp1, 6)

    return result
