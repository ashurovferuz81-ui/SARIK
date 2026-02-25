import os
import asyncio
import sqlite3
import yt_dlp
import uuid  # Takrorlanmas nom berish uchun
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- SOZLAMALAR ---
API_TOKEN = '8508069648:AAHukmF8Xcl44IQe6iTWkRaK-R7AuNVgfrc'
ADMIN_ID = 5775388579

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Yuklab olish papkasi
DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# --- BAZA ---
def init_db():
    conn = sqlite3.connect("users.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

class AdminStates(StatesGroup):
    waiting_for_ads = State()

# --- ASOSIY YUKLASH FUNKSIYASI ---
def download_video(url):
    unique_id = str(uuid.uuid4())[:8] # Har bir video uchun maxsus ID
    file_template = f"{DOWNLOAD_DIR}/{unique_id}_%(id)s.%(ext)s"
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': file_template,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True, # Xatolarni o'tkazib yuborish
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if not info:
            return None, None
            
        file_path = ydl.prepare_filename(info)
        title = info.get('title', '')
        desc = info.get('description', '')
        full_caption = f"{title}\n\n{desc}".strip()
        
        return file_path, full_caption

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    conn = sqlite3.connect("users.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("🚀 Bot tayyor! Link yuboring, men sizga cheksiz videolar yuklab beraman.")

@dp.message(F.text.regexp(r'(https?://[^\s]+)'))
async def handle_video_links(message: types.Message):
    url = message.text
    # Video servislarini tekshirish
    valid_sites = ['instagram.com', 'tiktok.com', 'youtube.com', 'youtu.be']
    if not any(x in url for x in valid_sites):
        return

    status = await message.answer("Video yuklanmoqda... 📥")

    try:
        # Videoni alohida thread'da yuklash (bot qotib qolmasligi uchun)
        loop = asyncio.get_event_loop()
        file_path, full_text = await loop.run_in_executor(None, download_video, url)
        
        if not file_path or not os.path.exists(file_path):
            await status.edit_text("❌ Videoni yuklab bo'lmadi. Link noto'g'ri yoki video yopiq.")
            return

        # Caption limiti
        if len(full_text) > 1024:
            full_text = full_text[:1020] + "..."

        # Yuborish
        video_input = types.FSInputFile(file_path)
        await bot.send_video(
            chat_id=message.chat.id,
            video=video_input,
            caption=full_text,
            parse_mode=None
        )
        
        await status.delete()
        
        # O'chirish
        os.remove(file_path)

    except Exception as e:
        print(f"Xato: {e}")
        await status.edit_text("⚠️ Xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.")

# Admin Panel (Statistika)
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    conn = sqlite3.connect("users.db")
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    await message.answer(f"📊 Statistika: {count} ta foydalanuvchi.")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
