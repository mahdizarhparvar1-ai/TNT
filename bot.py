def ask_gemini(prompt_input, history_context):
    if not GEMINI_API_KEY:
        return "❌ کلید GEMINI_API_KEY ست نشده است."

    try:
        if isinstance(prompt_input, list):
            user_text = prompt_input[0]
            content_to_send = [
                f"[دستور حیاتی: به هیچ وجه تفکر، تحلیل یا متن انگلیسی قبل از پاسخ ننویس. فقط پاسخ نهایی به زبان فارسی روان و صمیمی].\n[حافظه ماندگار ما و ایده‌ها]:\n{history_context}",
                user_text,
                prompt_input[1]
            ]
        else:
            full_prompt = f"""
[دستور حیاتی و غیرقابل تغییر]: 
به هیچ وجه، تحت هیچ شرایطی، فرآیند فکری، تحلیل، ترجمه یا کلمات انگلیسی به عنوان پیش‌درآمد در خروجی خود ننویسید. خروجی باید صد در صد فقط و فقط به زبان فارسی روان، رفاقتی و خودمانی باشد.

[حافظه ماندگار، دغدغه‌ها، تسک‌ها و ایده‌های تکامل تی‌ان‌تی]:
{history_context}

[درخواست جدید کاربر]:
{prompt_input}
"""
            content_to_send = full_prompt

        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)

        if not available_models:
            return "❌ هیچ مدلی روی این API Key پشتیبانی نمی‌شود."

        for model_name in available_models:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM_INSTRUCTION
                )
                response = model.generate_content(content_to_send)
                if response and response.text:
                    raw_response = response.text.strip()
                    
                    # فیلتر اضطراری: اگر مدل باز هم خطای انگلیسی یا افکار فرستاد، اینجا می‌تونیم مهارش کنیم
                    # ولی با دستورات بالا دیگه نباید بفرسته
                    return raw_response
            except Exception as e:
                logger.warning(f"Failed with model {model_name}: {e}")
                continue

        return "❌ هیچ‌کدام از مدل‌های فعال پاسخگو نبودند."

    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        return f"❌ خطای ارتباط با API گوگل: {e}"
