from telegram import Update
from telegram.ext import ContextTypes
import requests
from config import GEMINI_API_KEY

GEMINI_ENDPOINT = "https://api.gemini.google.com/v1/chat"  # Misol endpoint

async def gemini_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    if not user_message:
        await update.message.reply_text("Iltimos, biror gap yozing.")
        return

    await update.message.reply_chat_action("typing")

    try:
        headers = {
            "Authorization": f"Bearer {GEMINI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gemini-1.5",  # misol model
            "messages": [{"role": "user", "content": user_message}]
        }

        response = requests.post(GEMINI_ENDPOINT, json=data, headers=headers)
        response_json = response.json()

        answer = response_json.get("output_text", "Javob topilmadi 😢")
        await update.message.reply_text(answer)

    except Exception as e:
        await update.message.reply_text("Xatolik yuz berdi 😢")
        print(e)
