import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# خواندن امن توکن و آیدی مجاز از متغیرهای محیطی ریلی‌وی
TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # لایه‌ی امنیتی: اگر کسی غیر از تو پیام داد، ربات جواب نده
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"سلام {user_name} عزیز! 🛡️\n\nمن «تی‌ان‌تی» هستم؛ همیار امن، خودمختار و هوشمند شما.\nارتباط برقرار شد. در حال آماده‌سازی دژ امنیتی و ساختار اختصاصی شما هستیم.\nلطفاً منتظر بمانید تا دستورالعمل‌های بعدی راه‌اندازی شود."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # لایه‌ی امنیتی برای پیام‌ها
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    text = update.message.text
    await update.message.reply_text("...پیام دریافت شد. سیستم در حال پردازش است")

def main():
    if not TOKEN:
        raise ValueError("خطا: توکن ربات یافت نشد!")

    application = ApplicationBuilder().token(TOKEN).build()

    # ثبت هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("TNT Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
