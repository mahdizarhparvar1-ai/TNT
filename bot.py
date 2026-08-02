import os
import logging
import sqlite3
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# تنظیمات لوگین
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

# خواندن متغیرهای محیطی
TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def generate_ai_response(content_input):
    """تست هوشمند مدل‌های استاندارد به ترتیب نسخه‌های دقیق"""
    # لیست دقیق اسامی مدل‌های نسخه v1beta و پایدار
    candidate_names = [
        'gemini-1.5-flash-002',
        'gemini-1.5-pro-002',
        'gemini-1.5-flash',
        'gemini-1.5-pro'
    ]
    
    for model_name in candidate_names:
        try:
            m = genai.GenerativeModel(model_name)
            res = m.generate_content(content_input)
            return res.text
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}")
            continue
            
    raise Exception("هیچ‌کدام از مدل‌های جمینای در حال حاضر پاسخگو نیستند.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"سلام {user_name} عزیز! 🛡️\n\nمن «تی‌ان‌تی» هستم؛ دستیار هوشمند و اختصاصی شما. چطور می‌تونم کمکتون کنم؟"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    text = update.message.text

    # ذخیره در دیتابیس
    conn = sqlite3.connect('tnt_memory.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notes (user_id, note_text) VALUES (?, ?)", (user_id, text))
    conn.commit()
    conn.close()

    if GEMINI_API_KEY:
        try:
            response_text = generate_ai_response(text)
            await update.message.reply_text(response_text)
        except Exception as e:
            await update.message.reply_text(f"خطا در ارتباط با هوش مصنوعی: {e}")
    else:
        await update.message.reply_text("کلید API جمینای (GEMINI_API_KEY) در متغیرهای محیطی تنظیم نشده است.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    os.makedirs("downloads", exist_ok=True)
    file_path = os.path.join("downloads", f"chart_{user_id}.jpg")
    
    photo_file = await update.message.photo[-1].get_file()
    await photo_file.download_to_drive(file_path)

    if GEMINI_API_KEY:
        try:
            from PIL import Image
            img = Image.open(file_path)
            response_text = generate_ai_response(["این تصویر/چارت را کامل و هوشمندانه تحلیل کن:", img])
            await update.message.reply_text(response_text)
        except Exception as e:
            await update.message.reply_text(f"خطا در پردازش تصویر: {e}")
    else:
        await update.message.reply_text("تصویر ذخیره شد اما کلید جمینای ست نشده است.")

def main():
    if not TOKEN:
        raise ValueError("خطا: توکن ربات یافت نشد!")

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("TNT Bot with Gemini AI is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
