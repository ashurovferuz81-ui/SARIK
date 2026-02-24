import os
import asyncio
import yt_dlp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- SOZLAMALAR ---
API_TOKEN = '8508069648:AAHukmF8Xcl44IQe6iTWkRaK-R7AuNVgfrc'
ADMIN_ID = 5775388579 

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Yuklab olingan videolar uchun vaqtinchalik papka
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# --- VIDEO YUKLASH FUNKSIYASI ---
def download_video(url):
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
        
        # Video tagidagi barcha matn (Title + Description)
        # Ko'p saytlarda title yoki description birida barcha gaplar bo'ladi
        title = info.get('title', '')
        description = info.get('description', '')
        
        if description and title in description:
            full_text = description
        else:
            full_text = f"{title}\n\n{description}".strip()
            
        return file_path, full_text

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "🎬 **Instagram, TikTok va YouTube Downloader!**\n\n"
        "Menga video linkini yuboring, men sizga videoni va uning ostidagi **barcha matnlarni** yuboraman."
    )

@dp.message(F.text.regexp(r'(https?://[^\s]+)'))
async def handle_link(message: types.Message):
    url = message.text
    
    # Faqat video servislarini tekshirish
    if not any(x in url for x in ['instagram.com', 'tiktok.com', 'youtube.com', 'youtu.be']):
        return

    status_msg = await message.answer("Video tahlil qilinmoqda... 📥")

    try:
        # Videoni yuklab olish
        loop = asyncio.get_event_loop()
        file_path, caption_text = await loop.run_in_executor(None, download_video, url)
        
        # Telegram caption limiti 1024 belgi, shuni hisobga olamiz
        if len(caption_text) > 1024:
            caption_text = caption_text[:1020] + "..."

        # Videoni Telegramga yuborish
        video_file = types.FSInputFile(file_path)
        await bot.send_video(
            chat_id=message.chat.id,
            video=video_file,
            caption=caption_text if caption_text else "Video matni mavjud emas.",
            parse_mode=None # Markdown xatolarini oldini olish uchun
        )
        
        await status_msg.delete()
        
        # Railway xotirasini tejash uchun o'chirish
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        print(f"Xato: {e}")
        await status_msg.edit_text("❌ Videoni yuklab bo'lmadi. Linkni tekshiring yoki video yopiq profilda.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
