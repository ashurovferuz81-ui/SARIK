import os
import asyncio
import sqlite3
import yt_dlp
import uuid
import shutil
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage

# --- SOZLAMALAR ---
API_TOKEN = '8508069648:AAHukmF8Xcl44IQe6iTWkRaK-R7AuNVgfrc'
ADMIN_ID = 5775388579

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Har bir yuklash uchun alohida vaqtinchalik papka yaratamiz
BASE_DOWNLOAD_DIR = 'downloads'

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

# --- YUKLASH LOGIKASI ---
def download_media(query, is_audio=False):
    # Har bir so'rov uchun alohida papka (bir-biriga xalaqit bermasligi uchun)
    request_id = str(uuid.uuid4())
    request_dir = os.path.join(BASE_DOWNLOAD_DIR, request_id)
    os.makedirs(request_dir, exist_ok=True)
    
    output_template = os.path.join(request_dir, '%(title)s.%(ext)s')

    ydl_opts = {
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'outtmpl': output_template,
        'cookiefile': None, # IP bloklanish xavfini kamaytirish uchun
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
        if 'entries' in info:
            info = info['entries'][0]
        
        # Fayl yo'lini topish
        filename = ydl.prepare_filename(info)
        if is_audio:
            filename = os.path.splitext(filename)[0] + ".mp3"
            
        return filename, info.get('description', ''), info.get('title', ''), info.get('uploader', ''), request_dir

# --- HANDLERLAR ---

@dp.message(F.text)
async def handle_all(message: types.Message):
    # Obuna tekshiruvi (get_channel() orqali)
    # ... (oldingi obuna kodi bu yerda qoladi) ...

    url = message.text
    is_link = url.startswith("http")
    status = await message.answer("Siz uchun tayyorlanmoqda... ⏳")

    try:
        # Alohida thread'da ishga tushiramiz
        loop = asyncio.get_event_loop()
        file_path, desc, title, artist, r_dir = await loop.run_in_executor(None, download_media, url, not is_link)
        
        if os.path.exists(file_path):
            if is_link:
                # Instagram/VK Caption (max 1024)
                cap = desc[:1020] + "..." if len(desc) > 1024 else desc
                await bot.send_video(message.chat.id, video=FSInputFile(file_path), caption=cap or title)
            else:
                # Musiqa
                await bot.send_audio(message.chat.id, audio=FSInputFile(file_path), title=title, performer=artist)
            
            await status.delete()
            # Butun boshli so'rov papkasini o'chiramiz (bazada va diskda hech narsa qolmaydi)
            shutil.rmtree(r_dir)
        else:
            await status.edit_text("❌ Xatolik: Fayl yaratilmadi.")
    except Exception as e:
        print(f"ERROR: {e}")
        await status.edit_text("⚠️ Kechirasiz, hozirda bu so'rovni bajarib bo'lmaydi.")

async def main():
    init_db()
    if not os.path.exists(BASE_DOWNLOAD_DIR): os.makedirs(BASE_DOWNLOAD_DIR)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
