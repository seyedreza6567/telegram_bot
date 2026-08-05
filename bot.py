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


TOKEN = "8656837062:AAHEpTcYOsWkyW_ZXi3fIIcD6AtA_YnZU4Y"
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.run_polling()
