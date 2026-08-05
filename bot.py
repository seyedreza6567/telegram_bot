from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ربات فعال شد :white_check_mark:")

TOKEN = "8656837062:AAHEpTcYOsWkyW_ZXi3fIIcD6AtA_YnZU4Y"

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.run_polling()