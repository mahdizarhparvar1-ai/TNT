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

def ask_gemini(prompt_input):
    """دریافت خودکار مدل‌های فعال اکانت شما و پاسخ‌دهی بدون ارور ۴۰۴"""
    if not GEMINI_API_KEY:
        return "کلید API جمینای (GEMINI_API_KEY) ست نشده است."

    # پیدا کردن مدل‌های فعال روی API Key شما
    try:
        active_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                active_models.append(m.name)
        
        logger.info(f"Active models on your key: {active_models}")

        if not active_models:
            return "هیچ مدلی برای این API Key فعال نیست. لطفا کلید جدید از Google AI Studio بگیرید."

        # امتحان کردن مدل‌های پیدا شده یکی پس از دیگری
        for model_name in active_models:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt_input)
                return response.text
            except Exception as inner_e:
                logger.warning(f"Failed with {model_name}: {inner_e}")
                continue

        return "خطا: هیچ‌کدام از مدل‌های موجود روی اکانت شما پاسخ ندادند."

    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        return f"خطا در ارتباط با API گوگل: {e}"

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

    response_text = ask_gemini(text)
    await update.message.reply_text(response_text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    os.makedirs("downloads", exist_ok=True)
    file_path = os.path.join("downloads", f"chart_{user_id}.jpg")
    
    photo_file = await update.message.photo[-1].get_file()
    await photo_file.download_to_drive(file_path)

    try:
        from PIL import Image
        img = Image.open(file_path)
        response_text = ask_gemini(["این تصویر/چارت را کامل و هوشمندانه تحلیل کن:", img])
        await update.message.reply_text(response_text)
    except Exception as e:
        await update.message.reply_text(f"خطا در باز کردن تصویر: {e}")

def main():
    if not TOKEN:
        raise ValueError("خطا: توکن ربات یافت نشد!")

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("TNT Bot with Dynamic Gemini AI is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
