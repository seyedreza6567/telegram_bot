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
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    keyboard = [
        ["📈 سیگنال‌ها", "🔥 سیگنال نهایی"],
        ["💰 قیمت‌ها", "⚙️ تنظیمات"]
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
async def messages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    text = update.message.text
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
            # ذخیره لیست برای استفاده در انتخاب ارز
            context.user_data["futures_symbols"] = symbols
            # نمایش حداکثر 30 ارز در هر پیام
            symbols_to_show = symbols[:30]
            keyboard = []
            row = []
            for symbol in symbols_to_show:
                # حذف پسوند -USDT برای نمایش زیباتر
                display_name = symbol.replace(
                    "-SWAP-USDT",
                    ""
                ).replace(
                    "-USDT",
                    ""
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
            display_name = symbol.replace(
                "-SWAP-USDT",
                ""
            ).replace(
                "-USDT",
                ""
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
    # سیگنال نهایی
    # =====================================================
    if text == "🔥 سیگنال نهایی":
        await update.message.reply_text(
            "🔎 در حال بررسی ۵ تایم‌فریم...\n\n"
            "1H → 2H → 3H → 4H → 1D\n\n"
            "لطفاً صبر کن..."
        )
        try:
            result = final_signal(SYMBOL)
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
                    price = data.get(
                        "price",
                        "-"
                    )
                    atr = data.get(
                        "atr",
                        "-"
                    )
                    stop_loss = data.get(
                        "stop_loss",
                        "-"
                    )
                    take_profit = data.get(
                        "take_profit",
                        "-"
                    )
                    message += (
                        f"\n   💰 قیمت: {price}"
                        f"\n   📏 ATR: {atr}"
                        f"\n   🛑 حد ضرر: {stop_loss}"
                        f"\n   🎯 حد سود: {take_profit}"
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
        interval = text.replace(
            "⏱️ ",
            ""
        ).lower()
        if interval == "24h":
            interval = "1d"
        selected_symbol = context.user_data.get(
            "selected_symbol",
            SYMBOL
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
            stop_loss = result.get(
                "stop_loss",
                None
            )
            take_profit = result.get(
                "take_profit",
                None
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
                    f"\n🛑 حد ضرر: {stop_loss}\n"
                    f"🎯 حد سود: {take_profit}\n"
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
    # قیمت
    # =====================================================
    if text == "💰 قیمت‌ها":
        selected_symbol = context.user_data.get(
            "selected_symbol",
            SYMBOL
        )
        try:
            df = get_klines(
                symbol=selected_symbol,
                interval="1h",
                limit=5
            )
            if df is not None:
                price = df["close"].iloc[-1]
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
