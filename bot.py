from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN

from scanner import (
    get_klines,
    get_filtered_futures_symbols,
)

from analysis_engine import analyze
from signal_engine import final_signal


SYMBOL = "BTC-SWAP-USDT"


# =========================================================
# ارزهای مهم
# =========================================================

PRIORITY_SYMBOLS = [
    "BTC-SWAP-USDT",
    "ETH-SWAP-USDT",
    "BNB-SWAP-USDT",
    "SOL-SWAP-USDT",
    "XRP-SWAP-USDT",
    "DOGE-SWAP-USDT",
    "ADA-SWAP-USDT",
    "TRX-SWAP-USDT",
    "AVAX-SWAP-USDT",
    "LINK-SWAP-USDT",
    "DOT-SWAP-USDT",
    "LTC-SWAP-USDT",
    "BCH-SWAP-USDT",
    "UNI-SWAP-USDT",
    "SUI-SWAP-USDT",
]


# =========================================================
# تایم‌فریم‌ها
# =========================================================

SCAN_TIMEFRAMES = [
    "1h",
    "2h",
    "3h",
    "4h",
    "1d",
]


# =========================================================
# منوی اصلی
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    keyboard = [
        ["📈 سیگنال‌ها", "🔥 سیگنال نهایی"],
        ["🔎 اسکن بازار", "💰 قیمت‌ها"],
        ["⚙️ تنظیمات"]
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "🤖 ربات سیگنال فیوچرز فعال شد ✅\n\n"
        "انتخاب کن:",
        reply_markup=reply_markup
    )


# =========================================================
# اسکن چندتایم‌فریمی بازار
#
# FIX: این تابع قبلاً یک منطق تصمیم‌گیری کاملاً جدا و
# ناهماهنگ با signal_engine.py و backtest.py داشت
# (رأی‌گیری ساده + میانگین Score + آستانه‌های متفاوت).
# نتیجه‌اش این بود که بک‌تست هیچ ربطی به رفتار واقعی بات
# نداشت. حالا این تابع مستقیماً از همون final_signal()
# در signal_engine.py استفاده می‌کند - دقیقاً همان منطقی
# که "🔥 سیگنال نهایی" و backtest.py استفاده می‌کنند.
# =========================================================

async def scan_market(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🔎 در حال اسکن چندتایم‌فریمی بازار Futures...\n\n"
        "⏱️ 1H → 2H → 3H → 4H → 1D\n\n"
        "لطفاً صبر کن..."
    )

    try:

        available_symbols = get_filtered_futures_symbols()

        if not available_symbols:

            await update.message.reply_text(
                "❌ لیست Futures دریافت نشد."
            )

            return

        symbols = [
            symbol
            for symbol in PRIORITY_SYMBOLS
            if symbol in available_symbols
        ]

        if not symbols:

            await update.message.reply_text(
                "❌ ارزهای مهم پیدا نشدند."
            )

            return

        final_results = []

        # =================================================
        # بررسی هر ارز با همان منطق final_signal
        # =================================================

        for symbol in symbols:

            print(
                f"\n========== {symbol} =========="
            )

            try:

                result = final_signal(
                    symbol
                )

            except Exception as e:

                print(
                    f"SIGNAL ERROR {symbol}: {e}"
                )

                continue

            signal = result.get(
                "signal",
                "NO TRADE"
            )

            if signal not in [
                "LONG",
                "SHORT"
            ]:

                continue

            risk = result.get(
                "risk",
                {}
            )

            if not risk.get(
                "valid"
            ):

                continue

            entry = risk.get(
                "entry_price"
            )

            stop_loss = risk.get(
                "stop_loss"
            )

            tp1 = risk.get(
                "tp1"
            )

            tp2 = risk.get(
                "take_profit"
            )

            if (
                entry is None
                or
                stop_loss is None
                or
                tp2 is None
            ):

                continue

            risk_distance = abs(
                entry - stop_loss
            )

            reward_distance = abs(
                tp2 - entry
            )

            if risk_distance <= 0:

                continue

            risk_reward = (
                reward_distance
                / risk_distance
            )

            final_results.append({

                "symbol": symbol,

                "signal": signal,

                "quality_margin":
                    result.get(
                        "quality_margin",
                        0
                    ),

                "long_quality":
                    result.get(
                        "long_quality",
                        0
                    ),

                "short_quality":
                    result.get(
                        "short_quality",
                        0
                    ),

                "lower_long_count":
                    result.get(
                        "lower_long_count",
                        0
                    ),

                "lower_short_count":
                    result.get(
                        "lower_short_count",
                        0
                    ),

                "price": entry,

                "entry": entry,

                "stop_loss": stop_loss,

                "tp1": tp1,

                "tp2": tp2,

                "risk_reward": risk_reward,

                "timeframes":
                    result.get(
                        "timeframes",
                        {}
                    )
            })

        # =================================================
        # اگر فرصت قوی پیدا نشد
        # =================================================

        if not final_results:

            await update.message.reply_text(
                "⚪ در حال حاضر هیچ فرصت قوی‌ای "
                "با فیلتر نهایی (signal_engine) پیدا نشد.\n\n"
                "⚠️ سفارش واقعی ارسال نمی‌شود."
            )

            return

        # =================================================
        # مرتب‌سازی بر اساس فاصله کیفیت long/short و ریسک‌ریوارد
        # =================================================

        final_results.sort(
            key=lambda x: (
                x["quality_margin"],
                x["risk_reward"]
            ),
            reverse=True
        )

        # =================================================
        # فقط ۳ فرصت برتر
        # =================================================

        final_results = final_results[:3]

        # =================================================
        # ساخت پیام
        # =================================================

        message = (
            "🔥 بهترین فرصت‌های فیلترشده\n\n"
            "⏱️ 1H → 2H → 3H → 4H → 1D\n"
            "━━━━━━━━━━━━━━\n"
        )

        for item in final_results:

            symbol = item["symbol"]

            name = (
                symbol
                .replace("-SWAP-USDT", "")
                .replace("-USDT", "")
            )

            signal = item["signal"]

            if signal == "LONG":

                emoji = "🟢"

                quality = item[
                    "long_quality"
                ]

                lower_count = item[
                    "lower_long_count"
                ]

            else:

                emoji = "🔴"

                quality = item[
                    "short_quality"
                ]

                lower_count = item[
                    "lower_short_count"
                ]

            entry = item["entry"]

            stop_loss = item["stop_loss"]

            tp1 = item["tp1"]

            tp2 = item["tp2"]

            risk_reward = round(
                item["risk_reward"],
                1
            )

            message += (
                f"\n{emoji} {name} → {signal}\n"
                f"⭐ کیفیت: "
                f"{round(quality * 100, 1)}%\n"
                f"🎯 تأیید تایم‌فریم پایین: "
                f"{lower_count}\n"
                f"💰 قیمت: "
                f"{item['price']}\n"
                f"📍 Entry: "
                f"{entry}\n"
                f"🛑 Stop Loss: "
                f"{stop_loss}\n"
                f"🎯 TP1: "
                f"{tp1}\n"
                f"🎯 TP2: "
                f"{tp2}\n"
                f"📊 Risk/Reward: "
                f"1:{risk_reward}\n"
            )

            message += "📊 "

            for timeframe in SCAN_TIMEFRAMES:

                data = item[
                    "timeframes"
                ].get(
                    timeframe,
                    {}
                )

                tf_signal = data.get(
                    "signal",
                    "NO TRADE"
                )

                if tf_signal == "LONG":

                    tf_emoji = "🟢"

                elif tf_signal == "SHORT":

                    tf_emoji = "🔴"

                else:

                    tf_emoji = "⚪"

                message += (
                    f"{timeframe}:{tf_emoji} "
                )

            message += "\n"

        message += (
            "\n━━━━━━━━━━━━━━\n"
            "🛡️ فیلتر نهایی فعال است (همان منطق signal_engine.py).\n"
            "⚠️ این نتایج صرفاً تحلیلی هستند.\n"
            "⚠️ سفارش واقعی ارسال نمی‌شود."
        )

        await update.message.reply_text(
            message
        )

    except Exception as e:

        print(
            "SCAN MARKET ERROR:",
            e
        )

        await update.message.reply_text(
            f"❌ خطا در اسکن بازار:\n{e}"
        )


# =========================================================
# پیام‌ها
# =========================================================

async def messages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text

    # =====================================================
    # اسکن بازار
    # =====================================================

    if text == "🔎 اسکن بازار":

        await scan_market(
            update,
            context
        )

        return

    # =====================================================
    # سیگنال‌ها
    # =====================================================

    if text == "📈 سیگنال‌ها":

        await update.message.reply_text(
            "🔎 در حال دریافت ارزهای Futures از Toobit...\n"
            "لطفاً صبر کن..."
        )

        try:

            symbols = get_filtered_futures_symbols()

            if not symbols:

                await update.message.reply_text(
                    "❌ هیچ قرارداد Futures مناسبی پیدا نشد."
                )

                return

            context.user_data[
                "futures_symbols"
            ] = symbols

            symbols_to_show = symbols[:30]

            keyboard = []

            row = []

            for symbol in symbols_to_show:

                display_name = (
                    symbol
                    .replace("-SWAP-USDT", "")
                    .replace("-USDT", "")
                )

                row.append(display_name)

                if len(row) == 2:

                    keyboard.append(row)

                    row = []

            if row:

                keyboard.append(row)

            keyboard.append(
                ["🔙 برگشت"]
            )

            reply_markup = ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True
            )

            await update.message.reply_text(
                "📊 ارز موردنظر را انتخاب کن:",
                reply_markup=reply_markup
            )

        except Exception as e:

            await update.message.reply_text(
                f"❌ خطا در دریافت ارزها:\n{e}"
            )

        return

    # =====================================================
    # انتخاب ارز
    # =====================================================

    symbols = context.user_data.get(
        "futures_symbols",
        []
    )

    if symbols:

        selected_symbol = None

        for symbol in symbols:

            display_name = (
                symbol
                .replace("-SWAP-USDT", "")
                .replace("-USDT", "")
            )

            if text == display_name:

                selected_symbol = symbol

                break

        if selected_symbol:

            context.user_data[
                "selected_symbol"
            ] = selected_symbol

            keyboard = [
                ["⏱️ 1H", "⏱️ 2H"],
                ["⏱️ 3H", "⏱️ 4H"],
                ["⏱️ 24H"],
                ["🔙 برگشت"]
            ]

            reply_markup = ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True
            )

            await update.message.reply_text(
                f"📊 ارز انتخاب‌شده:\n"
                f"{selected_symbol}\n\n"
                "⏱️ تایم‌فریم موردنظر را انتخاب کن:",
                reply_markup=reply_markup
            )

            return

    # =====================================================
    # سیگنال نهایی BTC
    # =====================================================

    if text == "🔥 سیگنال نهایی":

        await update.message.reply_text(
            "🔎 در حال بررسی ۵ تایم‌فریم BTC...\n\n"
            "1H → 2H → 3H → 4H → 1D\n\n"
            "لطفاً صبر کن..."
        )

        try:

            result = final_signal(
                SYMBOL
            )

            signal = result.get(
                "signal",
                "NO TRADE"
            )

            long_count = result.get(
                "long_count",
                0
            )

            short_count = result.get(
                "short_count",
                0
            )

            if signal == "LONG":

                emoji = "🟢"

            elif signal == "SHORT":

                emoji = "🔴"

            else:

                emoji = "⚪"

            message = (
                "🔥 سیگنال نهایی BTC\n\n"
                f"{emoji} نتیجه: {signal}\n\n"
                f"🟢 LONG: {long_count}\n"
                f"🔴 SHORT: {short_count}\n\n"
                "📊 جزئیات تایم‌فریم‌ها:\n"
            )

            for timeframe, data in result.get(
                "timeframes",
                {}
            ).items():

                tf_signal = data.get(
                    "signal",
                    "NO TRADE"
                )

                score = data.get(
                    "score",
                    0
                )

                message += (
                    f"\n⏱️ {timeframe}"
                    f" → {tf_signal}"
                    f" | Score: {score}"
                )

                if tf_signal in [
                    "LONG",
                    "SHORT"
                ]:

                    message += (
                        f"\n   💰 قیمت: "
                        f"{data.get('price', '-')}"
                        f"\n   📏 ATR: "
                        f"{data.get('atr', '-')}"
                        f"\n   🛑 حد ضرر: "
                        f"{data.get('stop_loss', '-')}"
                        f"\n   🎯 حد سود: "
                        f"{data.get('take_profit', '-')}"
                    )

            message += (
                "\n\n⚠️ سفارش واقعی ارسال نمی‌شود."
            )

            await update.message.reply_text(
                message
            )

        except Exception as e:

            await update.message.reply_text(
                f"❌ خطا در تحلیل نهایی:\n{e}"
            )

        return

    # =====================================================
    # تایم‌فریم
    # =====================================================

    if text in [
        "⏱️ 1H",
        "⏱️ 2H",
        "⏱️ 3H",
        "⏱️ 4H",
        "⏱️ 24H"
    ]:

        interval = (
            text
            .replace("⏱️ ", "")
            .lower()
        )

        if interval == "24h":

            interval = "1d"

        selected_symbol = (
            context.user_data.get(
                "selected_symbol",
                SYMBOL
            )
        )

        await update.message.reply_text(
            f"🔎 در حال تحلیل...\n"
            f"📊 ارز: {selected_symbol}\n"
            f"⏱️ تایم‌فریم: {interval}\n\n"
            "لطفاً صبر کن..."
        )

        try:

            df = get_klines(
                symbol=selected_symbol,
                interval=interval,
                limit=250
            )

            if df is None:

                await update.message.reply_text(
                    "❌ دریافت اطلاعات بازار ناموفق بود."
                )

                return

            result = analyze(df)

            signal = result.get(
                "signal",
                "NO TRADE"
            )

            score = result.get(
                "score",
                0
            )

            confidence = result.get(
                "confidence",
                0
            )

            rsi = result.get(
                "rsi",
                "-"
            )

            price = result.get(
                "price",
                "-"
            )

            atr = result.get(
                "atr",
                "-"
            )

            reason = result.get(
                "reason",
                "-"
            )

            if signal == "LONG":

                emoji = "🟢"

            elif signal == "SHORT":

                emoji = "🔴"

            else:

                emoji = "⚪"

            message = (
                f"📊 {selected_symbol}\n\n"
                f"⏱️ تایم‌فریم: {interval}\n"
                f"{emoji} سیگنال: {signal}\n\n"
                f"⭐ امتیاز: {score}\n"
                f"📈 قدرت شرایط: {confidence}%\n"
                f"📊 RSI: {rsi}\n"
                f"💰 قیمت: {price}\n"
                f"📏 ATR: {atr}\n"
            )

            if signal in [
                "LONG",
                "SHORT"
            ]:

                message += (
                    f"\n🛑 حد ضرر: "
                    f"{result.get('stop_loss', '-')}\n"
                    f"🎯 حد سود: "
                    f"{result.get('take_profit', '-')}\n"
                )

            message += (
                f"\n📝 دلیل:\n{reason}\n\n"
                "⚠️ فعلاً سفارش واقعی ارسال نمی‌شود."
            )

            await update.message.reply_text(
                message
            )

        except Exception as e:

            await update.message.reply_text(
                f"❌ خطا در تحلیل:\n{e}"
            )

        return

    # =====================================================
    # قیمت‌ها
    # =====================================================

    if text == "💰 قیمت‌ها":

        selected_symbol = (
            context.user_data.get(
                "selected_symbol",
                SYMBOL
            )
        )

        try:

            df = get_klines(
                symbol=selected_symbol,
                interval="1h",
                limit=5
            )

            if df is not None:

                price = df[
                    "close"
                ].iloc[-1]

                await update.message.reply_text(
                    f"💰 قیمت {selected_symbol}:\n\n"
                    f"{price}"
                )

            else:

                await update.message.reply_text(
                    "❌ دریافت قیمت ناموفق بود."
                )

        except Exception as e:

            await update.message.reply_text(
                f"❌ خطا:\n{e}"
            )

        return

    # =====================================================
    # تنظیمات
    # =====================================================

    if text == "⚙️ تنظیمات":

        keyboard = [
            ["🛡️ حالت محافظه‌کارانه"],
            ["🎯 تأیید ۴ از ۵"],
            ["📉 حد ضرر: ۲٪"],
            ["📈 حد سود: ۴٪"],
            ["💰 ریسک هر معامله: ۱٪"],
            ["🤖 معاملات خودکار: خاموش"],
            ["🔙 برگشت"]
        ]

        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )

        await update.message.reply_text(
            "⚙️ تنظیمات ربات\n\n"
            "🛡️ حالت محافظه‌کارانه فعال است.\n\n"
            "تنظیم موردنظر را انتخاب کن:",
            reply_markup=reply_markup
        )

        return

    # =====================================================
    # برگشت
    # =====================================================

    if text == "🔙 برگشت":

        await start(
            update,
            context
        )

        return


# =========================================================
# اجرای ربات
# =========================================================

def main():

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            messages
        )
    )

    print(
        "🤖 Bot is starting..."
    )

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":

    main()
