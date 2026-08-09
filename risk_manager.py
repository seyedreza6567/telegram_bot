def calculate_risk(
    entry_price,
    signal,
    risk_percent=1.0,
    stop_loss_percent=2.0,
    take_profit_percent=4.0
):

    if entry_price <= 0:
        return {
            "valid": False,
            "reason": "قیمت ورود نامعتبر است"
        }

    if signal not in ["LONG", "SHORT"]:
        return {
            "valid": False,
            "reason": "سیگنال معتبر نیست"
        }

    if signal == "LONG":

        stop_loss = entry_price * (
            1 - stop_loss_percent / 100
        )

        take_profit = entry_price * (
            1 + take_profit_percent / 100
        )

    else:

        stop_loss = entry_price * (
            1 + stop_loss_percent / 100
        )

        take_profit = entry_price * (
            1 - take_profit_percent / 100
        )

    return {
        "valid": True,
        "signal": signal,
        "entry_price": round(entry_price, 4),
        "stop_loss": round(stop_loss, 4),
        "take_profit": round(take_profit, 4),
        "risk_percent": risk_percent,
        "stop_loss_percent": stop_loss_percent,
        "take_profit_percent": take_profit_percent
    }
