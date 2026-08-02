def ask_gemini(prompt_input, history_context):
    if not GEMINI_API_KEY:
        return "❌ کلید GEMINI_API_KEY ست نشده است."

    try:
        # ساختار متن را کاملاً ساده و بدون دستورات اضافی می‌فرستیم 
        # چون شخصیت و قوانین قبلاً در SYSTEM_INSTRUCTION تعریف شده‌اند
        if isinstance(prompt_input, list):
            user_text = prompt_input[0]
            content_to_send = [
                f"[حافظه ماندگار ما و ایده‌ها]:\n{history_context}",
                user_text,
                prompt_input[1]
            ]
        else:
            full_prompt = f"""
[حافظه ماندگار، دغدغه‌ها، تسک‌ها و ایده‌های تکامل تی‌ان‌تی]:
{history_context}

[پیام کاربر]:
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
                # اینجا از تنظیمات پنهان‌سازی تفکر (если موجود باشد) یا تنظیمات مدل استفاده می‌کنیم
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM_INSTRUCTION
                )
                
                # تنظیم پارامترها برای جلوگیری از طولانی شدن یا افکار اضافه
                generation_config = {
                    "temperature": 0.7,
                }
                
                response = model.generate_content(
                    content_to_send,
                    generation_config=generation_config
                )
                
                if response and response.text:
                    clean_response = response.text.strip()
                    
                    # اگر مدل باز هم اتفاقی افکار یا تگ‌های تفکر رو فرستاد، اینجا حذفش می‌کنیم
                    if "*" in clean_response and ("Role:" in clean_response or "Tone:" in clean_response or "User input:" in clean_response):
                        # یعنی مدل دارد تفکراتش را می‌نویسد؛ خطوط اضافه را رد می‌کنیم
                        lines = clean_response.split('\n')
                        final_lines = [l for l in lines if not any(k in l for k in ["Role:", "Tone:", "Language:", "User input:", "Context:", "* "])]
                        clean_response = "\n".join(final_lines).strip()
                    
                    if clean_response:
                        return clean_response
                        
            except Exception as e:
                logger.warning(f"Failed with model {model_name}: {e}")
                continue

        return "❌ متوجه شدم، ولی مشکلی در پاسخ‌دهی پیش آمد."

    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        return f"❌ خطای ارتباط با API گوگل: {e}"
