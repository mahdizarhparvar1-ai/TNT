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

# دستورالعمل سیستم جهت فارسی‌سازی کامل و حذف روندهای فکری پشت‌صحنه
SYSTEM_INSTRUCTION = """
شما دستیار هوشمند، حرفه‌ای و اختصاصی تحلیل چارت و ترید به نام «تی‌ان‌تی» هستید.
قوانین بسیار مهم که رعایت آن‌ها الزامی است:
1. زبان ارتباطی شما فقط و فقط فارسی روان، صمیمی و محترمانه است.
2. تمام روند فکر کردن، تحلیل‌های پشت صحنه (Thinking process)، گزینه‌ها، پیش‌نویس‌ها و ترجمه‌های انگلیسی را کاملاً مخفی کنید و هرگز در خروجی چاپ نکنید.
3. اصطلاحات تخصصی مالی، ترید و تحلیل تکنیکال (مانند MACD, RSI, Order Block, Stop Loss, Take Profit و...) را مجاز هستید به زبان انگلیسی بنویسید.
4. خروجی باید کاملاً تمیز، مستقیم و بدون هیچ مقدمه یا متن اضافه انگلیسی باشد.
"""

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

async def send_long_message(chat_id, context, text):
    """تقسیم متن‌های طولانی به پیام‌های زیر ۴۰۰۰ کاراکتر"""
    max_length = 3900
    for i in range(0, len(text), max_length):
        await context.bot.send_message(chat_id=chat_id, text=text[i:i+max_length])

def ask_gemini(prompt_input):
    if not GEMINI_API_KEY:
        return "❌ کلید GEMINI_API_KEY ست نشده است."

    try:
        # ۱. استعلام مستقیم مدل‌های فعال API Key شما از گوگل
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        logger.info(f"Available models for key: {available_models}")

        if not available_models:
            return "❌ هیچ مدلی روی این API Key پشتیبانی نمی‌شود. لطفاً یک API Key جدید بسازید."

        # ۲. تلاش برای ارسال به مدل‌های موجود با اعتمادسازی دستورالعمل سیستم
        for model_name in available_models:
            try:
                # اضافه کردن system_instruction به ساختار مدل
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM_INSTRUCTION
                )
                response = model.generate_content(prompt_input)
                if response and response.text:
                    return response.text
            except Exception as e:
                logger.warning(f"Failed with model {model_name}: {e}")
                continue

        return "❌ هیچ‌کدام از مدل‌های فعال پاسخگو نبودند."

    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        return f"❌ خطای ارتباط با API گوگل: {e}"

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
    try:
        conn = sqlite3.connect('tnt_memory.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO notes (user_id, note_text) VALUES (?, ?)", (user_id, text))
        conn.commit()
        conn.close()
    except Exception as db_e:
        logger.error(f"DB Error: {db_e}")

    status_msg = await update.message.reply_text("⏳ در حال دریافت پاسخ...")
    response_text = ask_gemini(text)
    await status_msg.delete()
    await send_long_message(update.effective_chat.id, context, response_text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    status_msg = await update.message.reply_text("📸 تصویر دریافت شد، در حال تحلیل چارت...")

    os.makedirs("downloads", exist_ok=True)
    file_path = os.path.join("downloads", f"chart_{user_id}.jpg")
    
    photo_file = await update.message.photo[-1].get_file()
    await photo_file.download_to_drive(file_path)

    try:
        from PIL import Image
        img = Image.open(file_path)
        response_text = ask_gemini(["این تصویر/چارت را کامل، دقیق و هوشمندانه تحلیل کن:", img])
        await status_msg.delete()
        await send_long_message(update.effective_chat.id, context, response_text)
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در پردازش تصویر: {e}")

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
