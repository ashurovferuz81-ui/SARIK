import os
import asyncio
import sqlite3
import yt_dlp
import uuid
import shutil
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- KONFIGURATSIYA ---
API_TOKEN = '8508069648:AAHukmF8Xcl44IQe6iTWkRaK-R7AuNVgfrc'
ADMIN_ID = 5775388579
DOWNLOAD_DIR = 'downloads'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class BotStates(StatesGroup):
    waiting_for_audio_extraction = State()

# --- BAZA ---
def init_db():
    conn = sqlite3.connect("bot_data.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

# --- YUKLASH FUNKSIYASI (HAMMASI UCHUN) ---
def download_general(url, mode='video'):
    request_id = str(uuid.uuid4())[:8]
    folder = os.path.join(DOWNLOAD_DIR, request_id)
    os.makedirs(folder, exist_ok=True)
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }

    if mode == 'audio_extract':
        # Videodan musiqani sug'urib olish
        ydl_opts.update({
            'format': 'bestaudio/best',
            'outtmpl': f'{folder}/audio.%(ext)s',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        })
    else:
        # Video yuklash (Instagram, YouTube, VK, Kino)
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
            'outtmpl': f'{folder}/video.%(ext)s',
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        if mode == 'audio_extract':
            filename = filename.rsplit('.', 1)[0] + '.mp3'
            
        caption = info.get('description') or info.get('title') or "Video yuklandi ✅"
        return filename, caption, folder

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    init_db()
    # Foydalanuvchini bazaga qo'shish
    conn = sqlite3.connect("bot_data.db")
    conn.execute("INSERT OR IGNORE INTO users VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Videodan musiqani olish", callback_data="extract_audio")]
    ])
    await message.answer("👋 Salom! Instagram, YouTube yoki VK linkini yuboring.\n\n"
                         "Agar videoni o'zini emas, ichidagi musiqasini olmoqchi bo'lsangiz, tugmani bosing.", reply_markup=kb)

@dp.callback_query(F.data == "extract_audio")
async def ask_audio(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔗 Musiqasini olmoqchi bo'lgan video linkini yuboring:")
    await state.set_state(BotStates.waiting_for_audio_extraction)
    await callback.answer()

@dp.message(F.text.startswith("http"))
async def handle_links(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    url = message.text
    status = await message.answer("Ishlamoqdaman... 🚀")

    try:
        loop = asyncio.get_event_loop()
        mode = 'audio_extract' if current_state == BotStates.waiting_for_audio_extraction else 'video'
        
        file_path, caption, folder = await loop.run_in_executor(None, download_general, url, mode)

        if os.path.exists(file_path):
            if mode == 'audio_extract':
                await bot.send_audio(message.chat.id, audio=FSInputFile(file_path), caption="🎧 Musiqa ajratib olindi.")
            else:
                # Instagram caption bilan yuborish
                await bot.send_video(message.chat.id, video=FSInputFile(file_path), caption=caption[:1024])
            
            await status.delete()
            shutil.rmtree(folder) # Tozalash
            await state.clear()
        else:
            await status.edit_text("❌ Xatolik yuz berdi.")
    except Exception as e:
        print(e)
        await status.edit_text("⚠️ Bu linkdan yuklab bo'lmadi. Linkni tekshiring.")

async def main():
    if not os.path.exists(DOWNLOAD_DIR): os.makedirs(DOWNLOAD_DIR)
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
