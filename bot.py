from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from scanner import get_btc_price

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [":chart_with_upwards_trend: سیگنال‌ها", ":moneybag: قیمت‌ها"],
        ["⚙ تنظیمات"]
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "ربات سیگنال فیوچرز فعال شد :white_check_mark:\n\nیک گزینه را انتخاب کن:",
        reply_markup=reply_markup
    )


from telegram.ext import MessageHandler, filters

async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == ":chart_with_upwards_trend: سیگنال‌ها":
        await update.message.reply_text(get_btc_price())

    elif text == ":moneybag: قیمت‌ها":
        await update.message.reply_text("بخش قیمت‌ها به‌زودی تکمیل می‌شود.")
TOKEN = "8656837062:AAHEpTcYOsWkyW_ZXi3fIIcD6AtA_YnZU4Y"
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))

app.run_polling()
