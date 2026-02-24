import os
import re
import asyncio
import yt_dlp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- SOZLAMALAR ---
API_TOKEN = '8508069648:AAHukmF8Xcl44IQe6iTWkRaK-R7AuNVgfrc'
ADMIN_ID = 5775388579 # Avvalgi xabarlarda bergan ID ingiz

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Yuklab olingan videolar uchun papka
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# --- HASHTAGLARNI AJRATISH ---
def extract_hashtags(text):
    if not text:
        return ""
    # Matndagi barcha #belgisi bilan boshlangan so'zlarni topish
    hashtags = re.findall(r"#\w+", text)
    return " ".join(hashtags)

# --- VIDEO YUKLASH (yt-dlp) ---
def download_video(url):
    ydl_opts = {
        'format': 'best', # Eng yaxshi sifat (Telegram uchun mos)
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        # Sarlavha va tavsifdan hashtaglarni qidirish uchun matn yig'ish
        full_info = f"{info.get('title', '')} {info.get('description', '')}"
        return file_path, full_info

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "🚀 **Instagram, TikTok va YouTube Downloader!**\n\n"
        "Menga video linkini yuboring, men sizga videoni va undagi **#hashtaglarni** yuboraman."
    )

@dp.message(F.text.regexp(r'(https?://[^\s]+)'))
async def handle_link(message: types.Message):
    url = message.text
    # Faqat kerakli saytlarni tekshirish
    if not any(x in url for x in ['instagram.com', 'tiktok.com', 'youtube.com', 'youtu.be']):
        return # Boshqa linklarga javob bermaydi

    status_msg = await message.answer("Tahlil qilinmoqda, kuting... ⏳")

    try:
        # Videoni serverga yuklab olish (async muhitda ishlashi uchun)
        loop = asyncio.get_event_loop()
        file_path, info_text = await loop.run_in_executor(None, download_video, url)
        
        # Hashtaglarni olish
        hashtags = extract_hashtags(info_text)
        
        # Videoni Telegramga yuborish
        video_file = types.FSInputFile(file_path)
        await bot.send_video(
            chat_id=message.chat.id,
            video=video_file,
            caption=f"📝 **Hashtaglar:**\n\n{hashtags}" if hashtags else "Hashtaglar topilmadi.",
            parse_mode="Markdown"
        )
        
        await status_msg.delete()
        
        # Railway xotirasini tejash uchun videoni serverdan o'chirish
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        print(f"Xato: {e}")
        await status_msg.edit_text("❌ Kechirasiz, videoni yuklab bo'lmadi. Linkni tekshiring yoki video yopiq profilda bo'lishi mumkin.")

# --- ADMIN PANEL (STATISTIKA) ---
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_stat(message: types.Message):
    await message.answer("👨‍💻 Admin panelga xush kelibsiz!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
