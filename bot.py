import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# تنظیمات لاگ‌گیری برای رصد وضعیت ربات روی سرور
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن ربات شما که از BotFather گرفتیم
TOKEN = os.getenv("TELEGRAM_TOKEN", "8615862462:AAHwmacMNaupYxDnU16JSJv71aC4nKZoC7Y")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"سلام {user.first_name} عزیز! 🛡️\n\n"
        "من «تی ان تی» (TNT) هستم؛ همیار امن، خودمختار و هوشمند شما.\n"
        "ارتباط با سرور ابری با موفقیت برقرار شد. در حال آماده‌سازی دژ امنیتی و ساختار اختصاصی شما هستیم...\n\n"
        "لطفاً منتظر بمانید تا دستورالعمل‌های بعدی راه‌اندازی تنظیم شود."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # فعلاً به صورت بازخورد ساده پیام‌ها را دریافت می‌کنیم تا لایه هوش مصنوعی را کامل متصل کنیم
    await update.message.reply_text(f"پیامت دریافت شد: {text}\nسیستم در حال پردازش است...")

def main():
    # ساخت اپلیکیشن ربات تلگرام
    application = ApplicationBuilder().token(TOKEN).build()

    # ثبت هندلرها (دستورات و پیام‌ها)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # شروع به کار ربات (پشتیبانی از پلتفرم‌های ابری)
    print("TNT Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
