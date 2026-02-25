import os
import asyncio
import sqlite3
import yt_dlp
import uuid
import shutil
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- SOZLAMALAR ---
API_TOKEN = '8508069648:AAHukmF8Xcl44IQe6iTWkRaK-R7AuNVgfrc'
ADMIN_ID = 5775388579

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
BASE_DOWNLOAD_DIR = 'downloads'

class UserStates(StatesGroup):
    waiting_for_music_name = State()

# --- BAZA ---
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
def get_main_keyboard():
    # Asosiy menyuda musiqa qidirish tugmasi
    design = [
        [InlineKeyboardButton(text="🔍 Musiqa qidirish", callback_data="search_music")],
        [InlineKeyboardButton(text="📢 Kanalimiz", url="https://t.me/your_channel")] # O'zingizni kanalingiz
    ]
    return InlineKeyboardMarkup(inline_keyboard=design)

# --- YUKLASH FUNKSIYASI ---
def download_media(query, is_audio=False):
    request_id = str(uuid.uuid4())
    request_dir = os.path.join(BASE_DOWNLOAD_DIR, request_id)
    os.makedirs(request_dir, exist_ok=True)
    
    ydl_opts = {
        'noplaylist': True, 'quiet': True, 'no_warnings': True,
        'outtmpl': os.path.join(request_dir, '%(title)s.%(ext)s'),
    }

    if is_audio:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'default_search': 'ytsearch1',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({'format': 'best'})

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        if 'entries' in info: info = info['entries'][0]
        filename = ydl.prepare_filename(info)
        if is_audio: filename = os.path.splitext(filename)[0] + ".mp3"
        return filename, info.get('description', ''), info.get('title', ''), info.get('uploader', ''), request_dir

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    init_db()
    conn = sqlite3.connect("bot_settings.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()
    
    await message.answer(
        "🚀 Botga xush kelibsiz!\n\nLink yuboring (Insta, TikTok, VK) yoki musiqa qidirish tugmasini bosing.",
        reply_markup=get_main_keyboard()
    )

# Inline tugma bosilganda
@dp.callback_query(F.data == "search_music")
async def music_search_btn(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🎸 Musiqa nomini yoki ijrochisini yozing:")
    await state.set_state(UserStates.waiting_for_music_name)
    await callback.answer()

# Faqat musiqa nomi kutilayotgan holatda ishlaydi
@dp.message(UserStates.waiting_for_music_name)
async def process_music_search(message: types.Message, state: FSMContext):
    query = message.text
    status = await message.answer("🔍 Qidirilmoqda...")
    
    try:
        loop = asyncio.get_event_loop()
        file_path, desc, title, artist, r_dir = await loop.run_in_executor(None, download_media, query, True)
        
        if os.path.exists(file_path):
            await bot.send_audio(
                message.chat.id, 
                audio=FSInputFile(file_path), 
                title=title, 
                performer=artist,
                caption="✅ @SizningBotingiz orqali topildi"
            )
            await status.delete()
            shutil.rmtree(r_dir)
            await state.clear() # Rejimdan chiqish
        else:
            await status.edit_text("❌ Musiqa topilmadi.")
    except Exception as e:
        print(f"ERROR: {e}")
        await status.edit_text("⚠️ Xatolik yuz berdi. Boshqa nom yozib ko'ring.")

# Linklar uchun handler (Instagram, TikTok, VK)
@dp.message(F.text.contains("http"))
async def handle_links(message: types.Message):
    url = message.text
    status = await message.answer("Yuklanmoqda... 📥")
    try:
        loop = asyncio.get_event_loop()
        file_path, desc, title, artist, r_dir = await loop.run_in_executor(None, download_media, url, False)
        
        if os.path.exists(file_path):
            cap = desc[:1020] + "..." if len(desc) > 1024 else desc
            await bot.send_video(message.chat.id, video=FSInputFile(file_path), caption=cap or title)
            await status.delete()
            shutil.rmtree(r_dir)
        else:
            await status.edit_text("❌ Videoni yuklab bo'lmadi.")
    except Exception as e:
        await status.edit_text("⚠️ Link yaroqsiz yoki video yopiq.")

async def main():
    if not os.path.exists(BASE_DOWNLOAD_DIR): os.makedirs(BASE_DOWNLOAD_DIR)
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
