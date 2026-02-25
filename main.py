import os
import asyncio
import sqlite3
import yt_dlp
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.storage.memory import MemoryStorage

# --- SOZLAMALAR ---
API_TOKEN = '8508069648:AAHukmF8Xcl44IQe6iTWkRaK-R7AuNVgfrc'
ADMIN_ID = 5775388579
CHANNELS = ["@kanal_usernamesi"] # Majburiy obuna kanallari

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# --- BAZA ---
def init_db():
    conn = sqlite3.connect("bot_data.db")
    # Foydalanuvchilar
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    # Kinolar bazasi
    conn.execute("CREATE TABLE IF NOT EXISTS movies (code TEXT PRIMARY KEY, file_id TEXT)")
    conn.commit()
    conn.close()

# --- ADMIN PANEL (Qotirilgan klaviatura) ---
def get_admin_keyboard():
    kb = [
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="🎬 Kino Qo'shish")],
        [KeyboardButton(text="📢 Reklama yuborish")]
    ]
    # input_field_placeholder - klaviatura tepasida yozuv turadi
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder="Admin paneli faol...")

# --- OBUNA TEKSHIRISH ---
async def check_sub(user_id):
    for channel in CHANNELS:
        chat_member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        if chat_member.status == "left":
            return False
    return True

# --- YUKLASH FUNKSIYASI ---
def download_video(url):
    unique_id = str(uuid.uuid4())[:8]
    file_template = f"{DOWNLOAD_DIR}/{unique_id}.%(ext)s"
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': file_template,
        'noplaylist': True,
        'quiet': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        return file_path, info.get('title', 'Video')

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    conn = sqlite3.connect("bot_data.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()
    
    if message.from_user.id == ADMIN_ID:
        await message.answer("Xush kelibsiz, Admin!", reply_markup=get_admin_keyboard())
    else:
        await message.answer("🚀 Link yuboring (Insta, TikTok, VK) yoki kino kodini yozing!")

# Kino kodini tekshirish (Masalan: 1 yozsa kinoni yuboradi)
@dp.message(F.text.isdigit())
async def get_movie(message: types.Message):
    if not await check_sub(message.from_user.id):
        return await message.answer(f"Botdan foydalanish uchun kanallarga a'zo bo'ling: {', '.join(CHANNELS)}")

    code = message.text
    conn = sqlite3.connect("bot_data.db")
    res = conn.execute("SELECT file_id FROM movies WHERE code = ?", (code,)).fetchone()
    conn.close()

    if res:
        await bot.send_video(chat_id=message.chat.id, video=res[0], caption=f"Kino kodi: {code}")
    else:
        await message.answer("❌ Bunday kodli kino topilmadi.")

# Admin uchun kino qo'shish (Video yuborsa bazaga oladi)
@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def add_movie(message: types.Message):
    # Bu yerda bizga vaqtinchalik kod kerak, masalan oxirgi kod + 1
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM movies")
    new_code = cursor.fetchone()[0] + 1
    cursor.execute("INSERT INTO movies VALUES (?, ?)", (str(new_code), message.video.file_id))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Kino bazaga qo'shildi! Kod: {new_code}")

# Linklarni yuklash (Insta, VK, TikTok)
@dp.message(F.text.regexp(r'(https?://[^\s]+)'))
async def handle_links(message: types.Message):
    if not await check_sub(message.from_user.id):
        return await message.answer("Avval kanallarga a'zo bo'ling!")

    url = message.text
    status = await message.answer("Yuklanmoqda... 📥")

    try:
        loop = asyncio.get_event_loop()
        file_path, title = await loop.run_in_executor(None, download_video, url)
        
        video_input = types.FSInputFile(file_path)
        await bot.send_video(chat_id=message.chat.id, video=video_input, caption=title)
        
        await status.delete()
        # Faylni o'chirish (Railway xotirasi to'lmasligi uchun)
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        await status.edit_text("❌ Yuklashda xato! Link noto'g'ri yoki yopiq profil.")

# Statistika tugmasi
@dp.message(F.text == "📊 Statistika")
async def stats(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect("bot_data.db")
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        await message.answer(f"Bot a'zolari: {count} ta")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
