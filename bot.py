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


SYMBOL = "BTC-SWAP-USDT"


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

    # -------------------------
    # سیگنال‌ها
    # -------------------------

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

    # -------------------------
    # تحلیل تایم‌فریم
    # -------------------------

    if text in [
        "⏱️ 1H",
        "⏱️ 2H",
        "⏱️ 3H",
        "⏱️ 4H",
        "⏱️ 24H"
    ]:

        interval = text.replace("⏱️ ", "").lower()

        if interval == "24h":
            interval = "1d"

        await update.message.reply_text(
            f"🔎 در حال تحلیل BTC...\n"
            f"⏱️ تایم‌فریم: {interval}\n\n"
            f"لطفاً چند لحظه صبر کن..."
        )

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

        signal = result.get("signal", "NO TRADE")
        score = result.get("score", 0)
        confidence = result.get("confidence", 0)
        rsi = result.get("rsi", "-")
        price = result.get("price", "-")
        reason = result.get("reason", "-")

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
            f"⚠️ این تحلیل توصیه مالی نیست."
        )

        await update.message.reply_text(message)

        return

    # -------------------------
    # قیمت
    # -------------------------

    if text == "💰 قیمت‌ها":

        df = get_klines(
            symbol=SYMBOL,
            interval="1h",
            limit=5
        )

        if df is not None:

            price = df["close"].iloc[-1]

            await update.message.reply_text(
                f"💰 قیمت BTC:\n\n"
                f"{price}"
            )

        else:

            await update.message.reply_text(
                "❌ دریافت قیمت ناموفق بود."
            )

        return

    # -------------------------
    # تنظیمات
    # -------------------------

    if text == "⚙️ تنظیمات":

        await update.message.reply_text(
            "⚙️ تنظیمات ربات به‌زودی اضافه می‌شود."
        )

        return

    # -------------------------
    # برگشت
    # -------------------------

    if text == "🔙 برگشت":

        await start(update, context)

        return


app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(
    CommandHandler("start", start)
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        messages
