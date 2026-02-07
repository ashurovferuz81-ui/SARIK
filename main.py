from telegram.ext import ApplicationBuilder, MessageHandler, filters
from handlers.gemini import gemini_chat
from config import TOKEN

app = ApplicationBuilder().token(TOKEN).build()

# Foydalanuvchidan kelgan matn bo‘yicha Gemini javob beradi
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gemini_chat))

print("Gemini Bot ishga tushdi 🚀")
app.run_polling()
