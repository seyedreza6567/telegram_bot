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

    # =========================
    # سیگنال‌ها
    # =========================

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

    # =========================
    # سیگنال نهایی
    # =========================

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

                if tf_signal in ["LONG", "SHORT"]:

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
                f"❌ خطا در تحلی
