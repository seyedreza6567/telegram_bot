def calculate_risk(
    entry_price,
    signal,
    atr=None,
    risk_percent=1.0,
    stop_atr=2.0,
    tp1_atr=2.0,
    tp2_atr=4.0
):

    try:

        entry_price = float(
            entry_price
        )

    except Exception:

        return {
            "valid": False,
            "reason": "قیمت ورود نامعتبر است"
        }

    if entry_price <= 0:

        return {
            "valid": False,
            "reason": "قیمت ورود نامعتبر است"
        }

    if signal not in [
        "LONG",
        "SHORT"
    ]:

        return {
            "valid": False,
            "reason": "سیگنال معتبر نیست"
        }

    if atr is None:

        return {
            "valid": False,
            "reason": "ATR موجود نیست"
        }

    try:

        atr = float(atr)

    except Exception:

        return {
            "valid": False,
            "reason": "ATR نامعتبر است"
        }

    if atr <= 0:

        return {
            "valid": False,
            "reason": "ATR باید بزرگ‌تر از صفر باشد"
        }

    if signal == "LONG":

        stop_loss = (
            entry_price -
            atr * stop_atr
        )

        tp1 = (
            entry_price +
            atr * tp1_atr
        )

        take_profit = (
            entry_price +
            atr * tp2_atr
        )

    else:

        stop_loss = (
            entry_price +
            atr * stop_atr
        )

        tp1 = (
            entry_price -
            atr * tp1_atr
        )

        take_profit = (
            entry_price -
            atr * tp2_atr
        )

    return {
        "valid": True,
        "signal": signal,
        "entry_price": round(
            entry_price,
            8
        ),
        "atr": round(
            atr,
            8
        ),
        "stop_loss": round(
            stop_loss,
            8
        ),
        "tp1": round(
            tp1,
            8
        ),
        "take_profit": round(
            take_profit,
            8
        ),
        "risk_percent": risk_percent,
        "stop_atr": stop_atr,
        "tp1_atr": tp1_atr,
        "tp2_atr": tp2_atr
    }


if __name__ == "__main__":

    print(
        calculate_risk(
            entry_price=100000,
            signal="LONG",
            atr=1000
        )
    )
