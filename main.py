import os
import asyncio
import sqlite3
import yt_dlp
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

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect("users.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect("users.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_users_count():
    conn = sqlite3.connect("users.db")
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return count

# --- REKLAMA HOLATI ---
class AdminStates(StatesGroup):
    waiting_for_ads = State()

# --- VIDEO YUKLASH (yt-dlp) ---
def download_video(url):
    # downloads papkasi borligini tekshirish
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
        
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        
        # Sarlavha va Tavsifni birlashtirish
        title = info.get('title', '')
        desc = info.get('description', '')
        
        if desc and title in desc:
            full_caption = desc
        else:
            full_caption = f"{title}\n\n{desc}".strip()
            
        return file_path, full_caption

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    add_user(message.from_user.id)
    await message.answer(
        "👋 **Xush kelibsiz!**\n\n"
        "Menga Instagram Reels, TikTok yoki YouTube Shorts linkini yuboring.\n"
        "Men sizga videoni barcha matnlari bilan yuklab beraman! 📥"
    )

# Admin Panel
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    count = get_users_count()
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📢 Reklama yuborish", callback_data="send_reklama")],
        [types.InlineKeyboardButton(text="📊 Statistika", callback_data="stat_check")]
    ])
    await message.answer(f"🛠 **Admin Panel**\n\nFoydalanuvchilar: {count} ta", reply_markup=kb)

@dp.callback_query(F.data == "send_reklama", F.from_user.id == ADMIN_ID)
async def reklama_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Reklama matnini (yoki rasm/video) yuboring:")
    await state.set_state(AdminStates.waiting_for_ads)
    await call.answer()

@dp.message(AdminStates.waiting_for_ads, F.from_user.id == ADMIN_ID)
async def broadcast_ads(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("users.db")
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    
    send_count = 0
    for user in users:
        try:
            await message.copy_to(chat_id=user[0])
            send_count += 1
            await asyncio.sleep(0.05) # Spamdan himoya
        except:
            pass
    
    await message.answer(f"✅ Reklama {send_count} ta foydalanuvchiga yuborildi.")
    await state.clear()

# Video yuklash qismi
@dp.message(F.text.regexp(r'(https?://[^\s]+)'))
async def handle_video_links(message: types.Message):
    url = message.text
    if not any(x in url for x in ['instagram.com', 'tiktok.com', 'youtube.com', 'youtu.be']):
        return

    status = await message.answer("Tahlil qilinmoqda... ⏳")

    try:
        # Yuklab olish (async muhitda)
        loop = asyncio.get_event_loop()
        file_path, full_text = await loop.run_in_executor(None, download_video, url)
        
        # Telegram caption limitini tekshirish (1024 belgi)
        if len(full_text) > 1024:
            full_text = full_text[:1020] + "..."

        # Videoni yuborish
        video_input = types.FSInputFile(file_path)
        await bot.send_video(
            chat_id=message.chat.id,
            video=video_input,
            caption=full_text if full_text else "Video matni yo'q.",
            parse_mode=None
        )
        
        await status.delete()
        
        # Faylni serverdan o'chirish (Railway xotirasini tejash)
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        print(f"Xato: {e}")
        await status.edit_text("❌ Xatolik: Videoni yuklab bo'lmadi. Profil yopiq bo'lishi mumkin.")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
