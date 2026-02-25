import os
import asyncio
import sqlite3
import yt_dlp
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# --- SOZLAMALAR ---
API_TOKEN = '8508069648:AAHukmF8Xcl44IQe6iTWkRaK-R7AuNVgfrc'
ADMIN_ID = 5775388579
CHANNELS = ["@kanal_usernamesi"] # Majburiy obuna kanali (agar kerak bo'lmasa bo'sh qoldiring [])

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# --- BAZA ---
def init_db():
    conn = sqlite3.connect("users.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

# --- ADMIN PANEL (Qotirilgan) ---
def get_admin_keyboard():
    kb = [
        [KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📢 Reklama yuborish")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder="Admin paneli...")

# --- OBUNA TEKSHIRISH ---
async def check_sub(user_id):
    if not CHANNELS: return True
    for channel in CHANNELS:
        try:
            chat_member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if chat_member.status == "left":
                return False
        except:
            continue
    return True

# --- YUKLASH LOGIKASI ---
def download_video(url):
    unique_id = str(uuid.uuid4())[:8]
    file_path = f"{DOWNLOAD_DIR}/{unique_id}.mp4"
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': file_path,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return file_path, info.get('title', 'Video yuklandi ✅')

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    conn = sqlite3.connect("users.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()
    
    if message.from_user.id == ADMIN_ID:
        await message.answer("Admin xush kelibsiz!", reply_markup=get_admin_keyboard())
    else:
        await message.answer("🚀 Instagram, TikTok yoki VK linkini yuboring!")

@dp.message(F.text.regexp(r'(https?://[^\s]+)'))
async def handle_links(message: types.Message):
    # Majburiy obuna tekshiruvi
    if not await check_sub(message.from_user.id):
        return await message.answer(f"Botdan foydalanish uchun kanalga a'zo bo'ling: {', '.join(CHANNELS)}")

    url = message.text
    status = await message.answer("Yuklanmoqda... 📥")

    try:
        loop = asyncio.get_event_loop()
        file_path, title = await loop.run_in_executor(None, download_video, url)
        
        if os.path.exists(file_path):
            video_input = types.FSInputFile(file_path)
            await bot.send_video(chat_id=message.chat.id, video=video_input, caption=title)
            await status.delete()
            os.remove(file_path) # Railway diskini tozalash
        else:
            await status.edit_text("❌ Videoni yuklashda xatolik yuz berdi.")

    except Exception as e:
        print(f"Xato: {e}")
        await status.edit_text("⚠️ Xatolik! Link xato yoki video yopiq profilda.")

@dp.message(F.text == "📊 Statistika")
async def stats(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect("users.db")
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        await message.answer(f"👤 Jami foydalanuvchilar: {count} ta")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
