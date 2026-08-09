from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from config import BOT_TOKEN
from scanner import get_klines
from analysis_engine import analyze
from signal_engine import final_signal
SYMBOL = "BTC-SWAP-USDT"
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📈 سیگنال‌ها":
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
            "⏱️ تایم‌فریم موردنظر را انتخاب کن:",
            reply_markup=reply_markup
        )
        return
    if text == "🔥 سیگنال نهایی":
        await update.message.reply_text(
            "🔎 در حال بررسی ۵ تایم‌فریم...\n\n"
            "1H → 2H → 3H → 4H → 1D\n\n"
            "لطفاً صبر کن..."
        )
        try:
            result = final_signal(SYMBOL)
            signal = result.get("signal", "NO TRADE")
            long_count = result.get("long_count", 0)
            short_count = result.get("short_count", 0)
            long_score = result.get("long_score", 0)
            short_score = result.get("short_score", 0)
            entry_price = result.get("entry_price")
            risk = result.get("risk", {})
            stop_loss = risk.get("stop_loss")
            take_profit = risk.get("take_profit")
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
                f"📈 امتیاز LONG: {long_score}\n"
                f"📉 امتیاز SHORT: {short_score}\n\n"
                f"💰 ورود: {entry_price}\n"
                f"🛑 حد ضرر: {stop_loss}\n"
                f"🎯 حد سود: {take_profit}\n\n"
                "📊 جزئیات تایم‌فریم‌ها:\n"
            )
            for timeframe, data in result["timeframes"].items():
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
            message += (
                "\n\n⚠️ سفارش واقعی ارسال نمی‌شود."
            )
            await update.message.reply_text(message)
        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا در تحلیل:\n{e}"
            )
        return
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
        await update.message.reply_text(
            f"🔎 در حال تحلیل BTC...\n"
            f"⏱️ تایم‌فریم: {interval}\n\n"
            "لطفاً صبر کن..."
        )
        try:
            df = get_klines(
                symbol=SYMBOL,
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
                f"📊 BTC/USDT\n\n"
                f"⏱️ تایم‌فریم: {interval}\n"
                f"{emoji} سیگنال: {signal}\n\n"
                f"⭐ امتیاز: {score}\n"
                f"📈 قدرت شرایط: {confidence}%\n"
                f"📊 RSI: {rsi}\n"
                f"💰 قیمت: {price}\n\n"
                f"📝 دلیل:\n{reason}\n\n"
                "⚠️ فعلاً سفارش واقعی ارسال نمی‌شود."
            )
            await update.message.reply_text(message)
        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا در تحلیل:\n{e}"
            )
        return
    if text == "💰 قیمت‌ها":
        try:
            df = get_klines(
                symbol=SYMBOL,
                interval="1h",
                limit=5
            )
            if df is not None:
                price = df["close"].iloc[-1]
                await update.message.reply_text(
                    f"💰 قیمت BTC:\n\n{price}"
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
    if text == "🔙 برگشت":
        await start(update, context)
        return
app = Application.builder().token(
    BOT_TOKEN
).build()
app.add_handler(
    CommandHandler(
        "start",
        start
    )
)
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        messages
    )
)
app.run_polling()
