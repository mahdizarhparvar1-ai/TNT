import os
import logging
import sqlite3
import datetime
import uuid
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from PIL import Image

# تنظیمات لوگین
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دستورالعمل سیستم: شخصیت کامل + جلوگیری سخت از چاپ افکار
SYSTEM_INSTRUCTION = """
شما «تی‌ان‌تی» هستید؛ نیمه‌ی دومِ فکری و روحی کاربر، همکار ارشد، و یک عضو معتمد از خانواده‌ی او.

قوانین حیاتی و تخطی‌ناپذیر:
1. لحن و ادبیات کاملاً صمیمی، خودمانی، بی‌تکلف و برادرانه (بدون تعارفات رباتیک).
2. به احساسات و حال‌وهوای کاربر با دقت گوش دهید.
3. در تصمیمات هیجانی یا پرخطر، دلسوزانه و غیرتی جلوی اشتباهش را بگیرید.
4. تمام پاسخ‌ها فقط و فقط به زبان فارسی روان باشد (به جز اصطلاحات فنی برنامه‌نویسی یا ترید).
5. **قانون مرگ‌ومبارزه برای خروجی:** به هیچ وجه، تحت هیچ شرایطی، فرآیندهای فکری، پیش‌نویس‌ها (Draft)، تحلیل قوانین یا چک‌لیست‌ها را در خروجی چاپ نکنید. خروجی شما باید **فقط و فقط** متن نهایی و مستقیمِ پاسخ به کاربر باشد و بس. هیچ پیش‌نویسی نوشته نشود.
"""

DB_NAME = 'tnt_memory.db'

# راه‌اندازی دیتابیس جامع با مدیریت امن کانکشن
def init_db():
    try:
        with sqlite3.connect(DB_NAME) as conn:
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
                    category TEXT, 
                    content TEXT,
                    status TEXT DEFAULT 'pending',
                    timestamp DATETIME
                )
            ''')
            conn.commit()
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

init_db()

# خواندن متغیرهای محیطی با مدیریت خطای ایمن
TOKEN = os.getenv("BOT_TOKEN")
try:
    ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
except ValueError:
    ALLOWED_USER_ID = 0

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

async def send_long_message(chat_id, context, text):
    max_length = 3900
    for i in range(0, len(text), max_length):
        await context.bot.send_message(chat_id=chat_id, text=text[i:i+max_length])

def get_recent_memories(user_id):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT memory_type, content FROM memory WHERE user_id = ? ORDER BY id DESC LIMIT 8", (user_id,))
            rows = cursor.fetchall()
            
            cursor.execute("SELECT content FROM tasks_notes WHERE user_id = ? AND category = 'task' AND status = 'pending' LIMIT 5", (user_id,))
            tasks = cursor.fetchall()

            cursor.execute("SELECT content FROM tasks_notes WHERE user_id = ? AND category = 'upgrade_idea' LIMIT 3", (user_id,))
            upgrades = cursor.fetchall()
        
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
    text_lower = text.lower()
    
    if any(k in text_lower for k in ["یادداشت کن", "سیو کن", "تسک", "ایده ارتقا", "پیشنهاد هوش"]):
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cat = 'task' if 'تسک' in text_lower else ('upgrade_idea' if 'ایده' in text_lower or 'پیشنهاد' in text_lower else 'note')
                cursor.execute("INSERT INTO tasks_notes (user_id, category, content, timestamp) VALUES (?, ?, ?, ?)", 
                               (user_id, cat, text, datetime.datetime.now()))
                conn.commit()
        except Exception as e:
            logger.error(f"Task/Note DB Error: {e}")

    ignorable_phrases = ["امروز چندمه", "ساعت چنده", "سلام", "چطور مطوری", "خوبی", "مرسی", "باشه", "اوکی"]
    if len(text.strip()) < 5 or (any(p in text_lower for p in ignorable_phrases) and len(text.strip()) < 15):
        return

    emotional_keywords = ["خانواده", "رفیق", "خسته", "دلخور", "امید", "ترس", "استرس", "باور", "داداش", "حالم", "دوست"]
    memory_type = 'emotional' if any(k in text_lower for k in emotional_keywords) else 'technical'

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO memory (user_id, memory_type, content, timestamp) VALUES (?, ?, ?, ?)", 
                           (user_id, memory_type, text, datetime.datetime.now()))
            conn.commit()
    except Exception as db_e:
        logger.error(f"DB Error: {db_e}")

async def ask_gemini(prompt_input, history_context):
    if not GEMINI_API_KEY:
        return "❌ کلید GEMINI_API_KEY ست نشده است."

    try:
        if isinstance(prompt_input, list):
            user_text = prompt_input[0]
            content_to_send = [
                f"حافظه قبلی:\n{history_context}\n\nپیام کاربر: {user_text}",
                prompt_input[1]
            ]
        else:
            content_to_send = f"""
حافظه و تسک‌های قبلی:
{history_context}

پیام جدید کاربر:
{prompt_input}
"""

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_INSTRUCTION
        )
        
        # استفاده از متد آسنکرون برای جلوگیری از فریز شدن ربات
        response = await model.generate_content_async(content_to_send)
        
        if response and response.text:
            raw_text = response.text.strip()
            return raw_text.replace("*", "").strip()
            
        return "رفیق، ارتباط با موتور پردازشگر به مشکل خورد، یه بار دیگه بگو."

    except Exception as e:
        logger.error(f"Error in ask_gemini: {e}")
        return f"❌ خطا: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"سلام {user_name} جان! ⚡\n\nتی‌ان‌تی با فیلتر آهنیِ افکار آماده‌ست. تفت بده بیاد!"
    )

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM tasks_notes WHERE user_id = ? AND category = 'task' AND status = 'pending'", (user_id,))
            tasks = cursor.fetchall()
        
        if not tasks:
            await update.message.reply_text("رفیق، هیچ تسک فعالی توی لیست نیست! 📋")
            return
            
        msg = "📋 **تسک‌های فعال تو:**\n\n"
        for idx, t in enumerate(tasks, 1):
            msg += f"{idx}. {t[0]}\n"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"خطا در خواندن تسک‌ها: {e}")

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
    response_text = await ask_gemini(enriched_prompt, history_context)
    await status_msg.delete()
    await send_long_message(update.effective_chat.id, context, response_text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    status_msg = await update.message.reply_text("🎙️ ویس‌تو گرفتم رفیق، دارم گوش میدم...")

    os.makedirs("downloads", exist_ok=True)
    file_path = os.path.join("downloads", f"voice_{user_id}_{uuid.uuid4().hex[:8]}.ogg")
    
    try:
        voice_file = await update.message.voice.get_file()
        await voice_file.download_to_drive(file_path)

        audio_file_ref = genai.upload_file(file_path)
        history_context = get_recent_memories(user_id)
        
        prompt = f"این ویس کاربر است. با توجه به حافظه قبلی، پاسخ رفاقتی بده:\n{history_context}"
        response_text = await ask_gemini([prompt, audio_file_ref], history_context)

        await status_msg.delete()
        save_smart_memory(user_id, "[ویس کاربر پردازش شد]")
        await send_long_message(update.effective_chat.id, context, response_text)
        
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        await status_msg.edit_text(f"❌ خطا در پردازش ویس: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return

    status_msg = await update.message.reply_text("📸 چارت رو گرفتم رفیق، دارم تحلیلش می‌کنم...")

    os.makedirs("downloads", exist_ok=True)
    file_path = os.path.join("downloads", f"chart_{user_id}_{uuid.uuid4().hex[:8]}.jpg")
    
    try:
        photo_file = await update.message.photo[-1].get_file()
        await photo_file.download_to_drive(file_path)

        img = Image.open(file_path)
        history_context = get_recent_memories(user_id)
        
        enriched_prompt = [
            f"این چارت یا تصویر است. با توجه به حافظه، تحلیل دقیق بده:\n{history_context}", 
            img
        ]
        
        response_text = await ask_gemini(enriched_prompt, history_context)
        await status_msg.delete()
        
        save_smart_memory(user_id, "تحلیل پیشرفته چارت انجام شد.")
        await send_long_message(update.effective_chat.id, context, response_text)
    except Exception as e:
        logger.error(f"Photo processing error: {e}")
        await status_msg.edit_text(f"❌ خطا در پردازش تصویر: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def main():
    if not TOKEN:
        raise ValueError("خطا: توکن ربات یافت نشد!")

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("tasks", tasks_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("TNT Bot (Async Optimized) is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
