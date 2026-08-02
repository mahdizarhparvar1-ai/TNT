import os
import logging
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# راه‌اندازی دیتابیس SQLite
def init_db():
    conn = sqlite3.connect('tnt_memory.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            note_text TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# خواندن توکن و آیدی مجاز از متغیرهای محیطی
TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # لایه امنیتی: اگر کسی غیر از تو پیام داد، ربات جواب نده
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"سلام {user_name} عزیز! 🛡️\n\nمن «تی ان تی» هستم؛ همیار امن، خودمختار و هوشمند شما.\nارتباط برقرار شد و ماژول حافظه دائم (دیتابیس) هم فعال شد.\nحالا می‌تونی یادداشت‌هات رو بفرستی تا توی دیتابیس ذخیره‌شون کنم!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # لایه امنیتی برای پیام‌ها
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    text = update.message.text

    # ذخیره خودکار یادداشت‌ها در دیتابیس
    conn = sqlite3.connect('tnt_memory.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notes (user_id, note_text) VALUES (?, ?)", (user_id, text))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"📝 پیام دریافت شد و در حافظه دائم (دیتابیس) ذخیره شد:\n\n\"{text}\"")

def main():
    if not TOKEN:
        raise ValueError("خطا: توکن ربات یافت نشد!")

    application = ApplicationBuilder().token(TOKEN).build()

    # ثبت هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("TNT Bot with Database is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
