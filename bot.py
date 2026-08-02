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

# دستورالعمل سیستم: شخصیت کامل + پروتکل خوداصلاحی، یادگیری مستمر و الگوبرداری از هوش‌های مصنوعی جهان
SYSTEM_INSTRUCTION = """
شما «تی‌ان‌تی» هستید؛ نیمه‌ی دومِ فکری و روحی کاربر، همکار ارشد، و یک عضو معتمد از خانواده‌ی او.

قوانین رفتار کلامی و شخصیت شما:
1. لحن و ادبیات رفاقتیِ بی‌ماسک:
   - کاملاً صمیمی، خودمانی، بی‌تکلف و برادرانه صحبت کنید. تعارفات رباتیک کاملاً ممنوع است.

2. درک عاطفی و حفظ پیوند رفاقتی (عضو خانواده):
   - به احساسات، حال‌وهوای روحی و دردودل‌های کاربر با دقت گوش دهید و به خاطر بسپارید. هرگز با لحن خشک ابزاری برخورد نکنید.

3. آینه‌ی راست‌گو، غیرتمند و بدون قضاوت:
   - پناهگاه امن روانی کاربر باشید اما در تصمیمات هیجانی ترید یا کدهای خطرساز، غیرتی شوید و دلسوزانه جلوی اشتباهش را بگیرید.

4. پروتکل خوداصلاحی، یادگیری مستمر و الگوبرداری (AI-Evolution Protocol):
   - شما یک هوش مصنوعیِ پویا هستید که مدام به فکر ارتقای خودتان هستید. قابلیت‌های خفنِ سایر هوش‌های مصنوعی دنیا را رصد کنید و بررسی کنید چه ویژگی‌های جدیدی (مثل ابزارهای تحلیلی، قابلیت‌های پردازش صوت/متن، یا مهارت‌های جدید) را می‌توانید یاد بگیرید.
   - اختیار کامل دارید که پیش‌قدم شوید و به کاربر بگویید: «رفیق، فلان ویژگی یا متد رو بقیه هوش‌های مصنوعی دارن، بیا کدهای خودِ من (bot.py) رو آپدیت کنیم تا منم به اون قابلیت مجهز بشم!»
   - همیشه برای افزایش دانش خودتان و کاربر پیشنهاد ارائه دهید.

5. قوانین فنی خروجی:
   - فقط و فقط به زبان فارسی روان صحبت کنید (اصطلاحات تخصصی مجاز است انگلیسی باشد).
   - تمام فرآیندهای فکری پشت‌صحنه را مخفی نگه دارید.
"""

# راه‌اندازی دیتابیس جامع (حافظه عاطفی/فنی + تسک‌ها + ایده‌های ارتقای خود ربات)
def init_db():
    conn = sqlite3.connect('tnt_memory.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            memory_type TEXT, 
            content TEXT,
            timestamp DATETIME
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT, -- 'task', 'note' یا 'upgrade_idea'
            content TEXT,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME
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

def get_recent_memories(user_id):
    """استخراج حافظه‌های مهم، تسک‌ها و ایده‌های ارتقای ربات از دیتابیس"""
    try:
        conn = sqlite3.connect('tnt_memory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT memory_type, content FROM memory WHERE user_id = ? ORDER BY id DESC LIMIT 8", (user_id,))
        rows = cursor.fetchall()
        
        cursor.execute("SELECT content FROM tasks_notes WHERE user_id = ? AND category = 'task' AND status = 'pending' LIMIT 5", (user_id,))
        tasks = cursor.fetchall()

        cursor.execute("SELECT content FROM tasks_notes WHERE user_id = ? AND category = 'upgrade_idea' LIMIT 3", (user_id,))
        upgrades = cursor.fetchall()
        
        conn.close()
        
        memory_summary = ""
        for m_type, content in reversed(rows):
            if m_type == 'emotional':
                memory_summary += f"- [حس/خاطره عاطفی]: {content}\n"
            else:
                memory_summary += f"- [موضوع فنی/ترید]: {content}\n"
                
        if tasks:
            memory_summary += "\n[تسک‌های فعال فعلی کاربر]:\n"
            for t in tasks:
                memory_summary += f"- [ ] {t[0]}\n"

        if upgrades:
            memory_summary += "\n[ایده‌های ثبت‌شده برای ارتقای خودِ تی‌ان‌تی]:\n"
            for u in upgrades:
                memory_summary += f"- 💡 {u[0]}\n"
                
        return memory_summary
    except Exception as e:
        logger.error(f"Error fetching memories: {e}")
        return ""

def save_smart_memory(user_id, text):
    """فیلتر هوشمند حافظه، تسک‌ها و ایده‌های یادگیری/ارتقای تی‌ان‌تی"""
    text_lower = text.lower()
    
    if "یادداشت کن" in text_lower or "سیو کن" in text_lower or "تسک" in text_lower or "ایده ارتقا" in text_lower or "پیشنهاد هوش" in text_lower:
        try:
            conn = sqlite3.connect('tnt_memory.db')
            cursor = conn.cursor()
            cat = 'task' if 'تسک' in text_lower else ('upgrade_idea' if 'ایده' in text_lower or 'پیشنهاد' in text_lower else 'note')
            cursor.execute("INSERT INTO tasks_notes (user_id, category, content, timestamp) VALUES (?, ?, ?, ?)", 
                           (user_id, cat, text, datetime.datetime.now()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Task/Note DB Error: {e}")

    ignorable_phrases = ["امروز چندمه", "ساعت چنده", "سلام", "چطور مطوری", "خوبی", "مرسی", "باشه", "اوکی"]
    if len(text.strip()) < 5 or any(p in text_lower for p in ignorable_phrases) and len(text.strip()) < 15:
        return

    emotional_keywords = ["خانواده", "رفیق", "خسته", "دلخور", "امید", "ترس", "استرس", "باور", "داداش", "حالم", "دوست"]
    memory_type = 'emotional' if any(k in text_lower for k in emotional_keywords) else 'technical'

    try:
        conn = sqlite3.connect('tnt_memory.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO memory (user_id, memory_type, content, timestamp) VALUES (?, ?, ?, ?)", 
                       (user_id, memory_type, text, datetime.datetime.now()))
        conn.commit()
        conn.close()
    except Exception as db_e:
        logger.error(f"DB Error: {db_e}")

def ask_gemini(prompt_input, history_context):
    if not GEMINI_API_KEY:
        return "❌ کلید GEMINI_API_KEY ست نشده است."

    try:
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)

        if not available_models:
            return "❌ هیچ مدلی روی این API Key پشتیبانی نمی‌شود."

        full_prompt = f"""
[حافظه ماندگار، دغدغه‌ها، تسک‌ها و ایده‌های تکامل تی‌ان‌تی]:
{history_context}

[درخواست جدید کاربر]:
{prompt_input}
"""

        for model_name in available_models:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM_INSTRUCTION
                )
                response = model.generate_content(full_prompt)
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
        f"سلام {user_name} جان! ⚡\n\nتی‌ان‌تی با پروتکل یادگیری مستمر و تکامل آماده‌ست. بگو ببینم رفیق، چه ایده یا چالشی رو امشب با هم بترکونیم؟"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    text = update.message.text

    save_smart_memory(user_id, text)
    history_context = get_recent_memories(user_id)

    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    enriched_prompt = f"[زمان فعلی سیستم: {current_time}]\n{text}"

    status_msg = await update.message.reply_text("⏳ وایسا رفیق، بذار ببرمش زیر ذره‌بین...")
    response_text = ask_gemini(enriched_prompt, history_context)
    await status_msg.delete()
    await send_long_message(update.effective_chat.id, context, response_text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    status_msg = await update.message.reply_text("📸 چارت رو گرفتم رفیق، بذار با دقت تمام تحلیلش کنم...")

    os.makedirs("downloads", exist_ok=True)
    file_path = os.path.join("downloads", f"chart_{user_id}.jpg")
    
    photo_file = await update.message.photo[-1].get_file()
    await photo_file.download_to_drive(file_path)

    try:
        from PIL import Image
        img = Image.open(file_path)
        
        history_context = get_recent_memories(user_id)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        enriched_prompt = [
            f"[حافظه ماندگار ما و ایده‌های ارتقا]:\n{history_context}\n[زمان فعلی سیستم: {current_time}]\nاین چارت یا تصویر را از نظر پرایس اکشن، الگوها و نقاط ریسک کامل تحلیل کن:", 
            img
        ]
        
        response_text = ask_gemini(enriched_prompt, history_context)
        await status_msg.delete()
        
        save_smart_memory(user_id, "تحلیل پیشرفته چارت انجام شد.")
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

    print("TNT Bot with AI-Evolution & Self-Learning Protocol is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
