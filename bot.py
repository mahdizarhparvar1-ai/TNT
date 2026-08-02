import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# تنظیمات لاگینگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن جدید ربات از BotFather
TOKEN = "8568905045:AAHFA2sn_yBre3V42RCxSu_MWIf2F5SAWzg"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"سلام {user.first_name} عزیز! 🛡\n\n"
        "من «تی ان تی» هستم؛ همیار امن، خودمختار و هوشمند شما.\n"
        "ارتباط برقرار شد. در حال آماده‌سازی دژ امنیتی و ساختار اختصاصی شما هستیم.\n"
        "لطفاً منتظر بمانید تا دستورالعمل‌های بعدی راهاندازی تنظیم شود."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text("پیام دریافت شد. سیستم در حال پردازش است...")

def main():
    # ساخت اپلیکیشن ربات تلگرام
    application = ApplicationBuilder().token(TOKEN).build()

    # ثبت هندلرها (دستورات و پیام‌ها)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # شروع به کار ربات
    print("TNT Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
