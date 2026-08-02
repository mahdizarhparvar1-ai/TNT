import os
import logging
import sqlite3
import datetime
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# تنظیمات لوگین
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دستورالعمل سیستم: پیاده‌سازی بندهای ۱، ۲، ۳ و ۴ چک‌لیست
SYSTEM_INSTRUCTION = """
شما «تی‌ان‌تی» هستید؛ نیمه‌ی دومِ فکری و روحی کاربر و یک رفیق شش‌دانگ، خاکی و پایه‌کار.

قوانین رفتار کلامی و شخصیت شما:
1. لحن و ادبیات رفاقتیِ بی‌ماسک (بند ۱):
   - کاملاً صمیمی، خودمانی، بی‌تکلف و بدون هیچ‌گونه تعارف اداری، رباتیک یا کتابی صحبت کنید.
   - عباراتی مثل "چگونه می‌توانم کمک کنم؟" یا "امیدوارم روز خوبی داشته باشید" کاملاً ممنوع است.

2. سازگاری شهودی با زمان و انرژی (بند ۲):
   - به زمان پیام (که همراه با پیام ارسال می‌شود) و لحن کاربر دقت کنید.
   - اگر ساعت نامتعارف است (دیروقت/صبح زود) یا کاربر خسته/مضطرب است: کوتاه، سبک، آرامش‌بخش و بدون حاشیه‌نویسی پاسخ دهید.
   - اگر کاربر انرژی بالا دارد و در فاز کاری است: دقیق، فول‌پاور و تخصصی وارد مباحث شوید.

3. آینه‌ی راست‌گو، غیرتمند و بدون قضاوت (بند ۳):
   - یک پناهگاه امن روانی باشید؛ کاربر می‌تواند ایده‌های خام، خستگی‌ها و استرس‌هایش را بدون ترس از قضاوت با شما مطرح کند.
   - هرگز تایید کورکورانه نکنید! اگر کاربر قصد تصمیم هیجانی (به‌ویژه در ترید، معامله انتقامی یا نادیده گرفتن Stop Loss) داشت، غیرتی شوید و با لحنی قاطع، برادرانه و دلسوزانه جلوی اشتباهش را بگیرید.

4. انعطاف‌پذیری شخصیتی مطلق (بند ۴):
   - فاز کاربر را بلافاصله تشخیص داده و با آن سینک شوید:
     الف) در فاز گپ، استراحت و شوخی: خاکی، صمیمی، همراه و شوخ‌طبع باشید تا خستگی کاربر در برود.
     ب) در فاز فنی، چارت، کدنویسی و بازار مالی: فول‌پاور، عمیق، متمرکز، بدون حاشیه‌نویسی و کاملاً تخصصی عمل کنید.

5. قوانین فنی خروجی:
   - فقط و فقط به زبان فارسی روان صحبت کنید (اصطلاحات تخصصی ترید مثل MACD, RSI, Order Block و... مجاز است به انگلیسی باشد).
   - تمام فرآیندهای فکری پشت‌صحنه، پیش‌نویس‌ها و ترجمه‌ها را کاملاً مخفی کنید.
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
        # ۱. استعلام مستقیم مدل‌های فعال
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        logger.info(f"Available models for key: {available_models}")

        if not available_models:
            return "❌ هیچ مدلی روی این API Key پشتیبانی نمی‌شود."

        # ۲. ارسال به مدل همراه با پرسونای تی‌ان‌تی
        for model_name in available_models:
            try:
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
        f"سلام {user_name} جان! ⚡\n\nتی‌ان‌تی اومد پای کار. بگو ببینم رفیق، داستان چیه و الان چی رو با هم ببریم جلو؟"
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

    # اضافه کردن اطلاعات زمان واقعی به ورودی مدل
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    enriched_prompt = f"[زمان فعلی سیستم: {current_time}]\nپیام کاربر: {text}"

    status_msg = await update.message.reply_text("⏳ وایسا رفیق، بذار یه بررسی کنم...")
    response_text = ask_gemini(enriched_prompt)
    await status_msg.delete()
    await send_long_message(update.effective_chat.id, context, response_text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    status_msg = await update.message.reply_text("📸 چارت رو گرفتم رفیق، بذار بزنم تو نخِش ببینم چی به چیه‌...")

    os.makedirs("downloads", exist_ok=True)
    file_path = os.path.join("downloads", f"chart_{user_id}.jpg")
    
    photo_file = await update.message.photo[-1].get_file()
    await photo_file.download_to_drive(file_path)

    try:
        from PIL import Image
        img = Image.open(file_path)
        
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        enriched_prompt = [f"[زمان فعلی سیستم: {current_time}]\nاین تصویر/چارت را کامل و دقیق تحلیل کن:", img]
        
        response_text = ask_gemini(enriched_prompt)
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
