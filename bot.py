from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from scanner import get_btc_price


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        ["📈 سیگنال‌ها", "💰 قیمت‌ها"],
        ["⚙️ تنظیمات"]
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "🤖 ربات سیگنال فیوچرز فعال شد ✅\n\nانتخاب کن:",
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
            "تایم‌فریم را انتخاب کن:",
            reply_markup=reply_markup
        )

    elif text in ["⏱️ 1H", "⏱️ 2H", "⏱️ 3H", "⏱️ 4H", "⏱️ 24H"]:

        timeframe = text.replace("⏱️ ", "")

        await update.message.reply_text(
            f"📊 تحلیل BTC/USDT\n\n"
            f"تایم‌فریم: {timeframe}\n\n"
            f"{get_btc_price()}\n\n"
            "⏳ بخش تحلیل و سیگنال در حال ساخت است..."
        )

    elif text == "💰 قیمت‌ها":

        await update.message.reply_text(
            get_btc_price()
        )

    elif text == "⚙️ تنظیمات":

        await update.message.reply_text(
            "⚙️ تنظیمات ربات به‌زودی اضافه می‌شود."
        )

    elif text == "🔙 برگشت":

        await start(update, context)


TOKEN = "8656837062:AAHEpTcYOsWkyW_ZXi3fIIcD6AtA_YnZU4Y"


app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, messages)
)

app.run_polling()
