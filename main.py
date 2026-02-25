import os
import asyncio
import sqlite3
import yt_dlp
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- SOZLAMALAR ---
API_TOKEN = '8508069648:AAHukmF8Xcl44IQe6iTWkRaK-R7AuNVgfrc'
ADMIN_ID = 5775388579

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AdminStates(StatesGroup):
    waiting_for_channel = State()

DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect("bot_settings.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT OR IGNORE INTO settings VALUES ('channel', '')")
    conn.commit()
    conn.close()

def get_channel():
    conn = sqlite3.connect("bot_settings.db")
    res = conn.execute("SELECT value FROM settings WHERE key='channel'").fetchone()
    conn.close()
    return res[0] if res else ""

# --- KEYBOARDS ---
def get_admin_keyboard():
    kb = [
        [KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📢 Kanalni sozlash"), KeyboardButton(text="❌ Kanalni o'chirish")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder="Admin paneli...")

# --- OBUNA TEKSHIRISH ---
async def check_sub(user_id):
    channel = get_channel()
    if not channel or not channel.startswith('@'):
        return True
    try:
        chat_member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        if chat_member.status in ["left", "kicked"]:
            return False
    except:
        return True
    return True

# --- YUKLASH FUNKSIYALARI ---
def download_media(url, is_audio=False):
    unique_id = str(uuid.uuid4())[:8]
    file_path = f"{DOWNLOAD_DIR}/{unique_id}.%(ext)s"
    
    ydl_opts = {
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }

    if is_audio:
        # Musiqa qidirish va yuklash sozlamalari
        ydl_opts.update({
            'format': 'bestaudio/best',
            'default_search': 'ytsearch1',
            'outtmpl': f"{DOWNLOAD_DIR}/{unique_id}",
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
        final_path = f"{DOWNLOAD_DIR}/{unique_id}.mp3"
    else:
        # Video yuklash (Insta, TikTok, VK)
        ydl_opts.update({'format': 'best', 'outtmpl': file_path})

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if 'entries' in info: info = info['entries'][0]
        
        caption = info.get('description') or info.get('title') or ""
        title = info.get('title', 'Musiqa')
        artist = info.get('uploader', 'Bot')
        
        path = final_path if is_audio else ydl.prepare_filename(info)
        return path, caption, title, artist

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    conn = sqlite3.connect("bot_settings.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()
    
    if message.from_user.id == ADMIN_ID:
        await message.answer("Siz adminsiz!", reply_markup=get_admin_keyboard())
    else:
        await message.answer("🚀 Link yuboring (Insta, VK, TikTok) yoki musiqa nomini yozing!")

@dp.message(F.text == "📊 Statistika", F.from_user.id == ADMIN_ID)
async def stats(message: types.Message):
    conn = sqlite3.connect("bot_settings.db")
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    await message.answer(f"👤 Foydalanuvchilar: {count} ta")

@dp.message(F.text == "📢 Kanalni sozlash", F.from_user.id == ADMIN_ID)
async def set_channel_start(message: types.Message, state: FSMContext):
    await message.answer("Kanal usernamesini yuboring (Masalan: @kanal):")
    await state.set_state(AdminStates.waiting_for_channel)

@dp.message(AdminStates.waiting_for_channel)
async def set_channel_done(message: types.Message, state: FSMContext):
    new_channel = message.text.strip()
    if new_channel.startswith('@'):
        conn = sqlite3.connect("bot_settings.db")
        conn.execute("UPDATE settings SET value=? WHERE key='channel'", (new_channel,))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Kanal {new_channel} ga o'zgartirildi.")
        await state.clear()
    else:
        await message.answer("⚠️ Username @ bilan boshlanishi kerak!")

@dp.message(F.text == "❌ Kanalni o'chirish", F.from_user.id == ADMIN_ID)
async def delete_channel(message: types.Message):
    conn = sqlite3.connect("bot_settings.db")
    conn.execute("UPDATE settings SET value='' WHERE key='channel'")
    conn.commit()
    conn.close()
    await message.answer("✅ Obuna o'chirildi.")

@dp.message(F.text)
async def handle_all(message: types.Message):
    if not await check_sub(message.from_user.id):
        channel = get_channel()
        return await message.answer(f"❌ Botdan foydalanish uchun kanalga a'zo bo'ling:\n{channel}")

    url = message.text
    is_link = url.startswith("http")
    status = await message.answer("Qidirilmoqda... 📥" if not is_link else "Yuklanmoqda... 📥")

    try:
        loop = asyncio.get_event_loop()
        file_path, caption, title, artist = await loop.run_in_executor(None, download_media, url, not is_link)
        
        if os.path.exists(file_path):
            if is_link:
                await bot.send_video(message.chat.id, video=FSInputFile(file_path), caption=caption[:1024])
            else:
                await bot.send_audio(message.chat.id, audio=FSInputFile(file_path), title=title, performer=artist)
            
            await status.delete()
            os.remove(file_path)
        else:
            await status.edit_text("❌ Topilmadi.")
    except Exception as e:
        print(f"Xato: {e}")
        await status.edit_text("⚠️ Xatolik yuz berdi!")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
