
import asyncio
import os
import logging
import shutil
import time
from urllib.parse import urljoin, urlparse

import requests
from datetime import datetime
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
from rembg import remove
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.functions.account import UpdateProfileRequest
from dotenv import load_dotenv
import yt_dlp
import google.generativeai as genai

# --- CONFIGURATION ---
load_dotenv()

# Load environment variables
API_ID = os.getenv("API_ID", "27606796")
API_HASH = os.getenv("API_HASH", "b428cbb6aeb2bf0dcd4c507193e56f45")
SESSION_NAME = os.getenv("SESSION_NAME", "hybrid_userbot")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6472114736"))
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "3cd4b14bd6f9ed61b82105a8c3f2f31e")
GENAI_API_KEY = os.getenv("GENAI_API_KEY", "AIzaSyC-h-T764kvHN2N8PQ-IdeJbzXssUfG8Jw")

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Telegram client initialization
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Gemini AI configuration
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")
chat = model.start_chat(history=[])

# Weather region mapping
REGIONS = {
    "Toshkent": "Tashkent", "Andijon": "Andijan", "Farg‘ona": "Fergana", "Namangan": "Namangan",
    "Samarqand": "Samarkand", "Buxoro": "Bukhara", "Xorazm": "Urgench", "Navoiy": "Navoi",
    "Qashqadaryo": "Karshi", "Surxondaryo": "Termiz", "Jizzax": "Jizzakh", "Sirdaryo": "Gulistan",
    "Qoraqalpog‘iston": "Nukus"
}

# Store user data for music search
user_data = {}


# --- UTILITY FUNCTIONS ---
def clean_downloads():
    """Remove temporary files from the downloads directory."""
    if os.path.exists("downloads"):
        shutil.rmtree("downloads")
        os.makedirs("downloads", exist_ok=True)


# --- BOT COMMANDS ---
@client.on(events.NewMessage(pattern=r'^\.start$'))
async def start(event):
    """Handle .start command to display bot menu."""
    await event.reply(
        "🤖 Hybrid UserBot tayyor. Buyruqlar: .ai, .weather, .bgremove, .insta, .clone, .mention, .id")


@client.on(events.NewMessage(pattern=r'^\.ai (.+)'))
async def ai_handler(event):
    """Handle .ai command for Gemini AI interaction."""
    prompt = event.pattern_match.group(1)
    try:
        response = await asyncio.to_thread(chat.send_message, prompt)
        await event.reply(response.text)
    except Exception as e:
        logger.error(f"AI error: {e}")
        await event.reply(f"❌ AI xatoligi: {e}")


@client.on(events.NewMessage(pattern=r'^\.weather(?: (.+))?'))
async def weather_handler(event):
    """Handle .weather command to fetch weather data."""
    city = event.pattern_match.group(1)
    if not city:
        return await event.reply("🌦 Iltimos, shahar yoki viloyat kiriting: `.weather Toshkent`")

    city_api = REGIONS.get(city.strip(), city.strip())
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_api}&appid={OPENWEATHER_API_KEY}&units=metric&lang=uz"

    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()

        if data.get("cod") != 200:
            return await event.reply(f"❌ Shahar topilmadi: {city_api}")

        weather = data['weather'][0]['description'].capitalize()
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        pressure = data['main']['pressure']
        wind = data['wind']['speed']
        sunrise = datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M')
        sunset = datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M')

        text = (
            f"📍 {city_api}:\n"
            f"🌤 Ob-havo: {weather}\n"
            f"🌡 Harorat: {temp}°C\n"
            f"🤔 His qilinadi: {feels_like}°C\n"
            f"💧 Namlik: {humidity}%\n"
            f"📈 Bosim: {pressure} hPa\n"
            f"💨 Shamol: {wind} m/s\n"
            f"🌅 Quyosh chiqishi: {sunrise}\n"
            f"🌇 Quyosh botishi: {sunset}"
        )
        await event.reply(text)
    except requests.RequestException as e:
        logger.error(f"Weather API error: {e}")
        await event.reply(f"❌ Ob-havo xatoligi: {e}")

@client.on(events.NewMessage(pattern=r'^\.help$'))
async def help_handler(event):
    text = (
        "**🛠 Buyruqlar ro‘yxati:**\n\n"
        "• `.ai <so‘rov>` — Sun'iy intellektdan javob oladi\n"
        "• `.weather <shahar>` — Ob-havo ma'lumotini ko‘rsatadi\n"
        "• `.bgremove` — Rasm fonini olib tashlaydi (reply orqali)\n"
        "• `.insta <url>` — Instagram video yoki rasmlarini yuklab oladi\n"
        "• `.clone <url>` — Saytni frontend qismini ZIP qilib beradi\n"
        "• `.mention` — Guruhdagi barcha a'zolarni at-mention qiladi\n"
        "• `.id` — Reply qilingan foydalanuvchi yoki guruh ID sini ko‘rsatadi\n"
        "• `.ping` — Botning javob tezligini ko‘rsatadi\n"
        "• `.help` — To‘liq yordamchi buyruqlar ro‘yxati\n"

    )
    await event.reply(text)

@client.on(events.NewMessage(pattern=r'^\.ping$'))
async def ping_handler(event):
    start = time.time()
    msg = await event.reply("🏓 Pinging...")
    end = time.time()
    duration = (end - start) * 1000  # millisekund
    await msg.edit(f"🏓 Pong! `{int(duration)}ms`")


@client.on(events.NewMessage(pattern=r'^\.bgremove$'))
async def bgremove_handler(event):
    """Handle .bgremove command to remove image background."""
    if not event.is_reply:
        return await event.reply("📸 Rasmga reply qiling.")

    msg = await event.get_reply_message()
    if not msg.photo:
        return await event.reply("📸 Faqat rasmlar uchun ishlaydi.")

    path = await msg.download_media()
    try:
        image = Image.open(path).convert("RGBA")
        output = remove(image)
        bio = BytesIO()
        output = output.convert("RGB")  # JPG format
        output.save(bio, format='JPEG')
        bio.name = "removed_bg.jpg"
        bio.seek(0)
        await event.reply("✅ Fon olib tashlandi:", file=bio)
    except Exception as e:
        logger.error(f"Background removal error: {e}")
        await event.reply(f"❌ Rasm xatoligi: {e}")
    finally:
        if path and os.path.exists(path):
            os.remove(path)


@client.on(events.NewMessage(pattern=r'^\.insta (.+)'))
async def insta_download(event):
    """Handle .insta command to download Instagram videos."""
    url = event.pattern_match.group(1)
    try:
        ydl_opts = {
            'outtmpl': 'downloads/video.%(ext)s',
            'format': 'mp4',
            'quiet': True,
            'no_warnings': True
        }
        os.makedirs("downloads", exist_ok=True)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        await event.reply("✅ Yuklandi", file=filename)
    except Exception as e:
        logger.error(f"Instagram download error: {e}")
        await event.reply(f"❌ Instagram xatoligi: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)



# @client.on(events.NewMessage(pattern=r'^\.clone (.+)'))
# async def clone_website(event):
#     """Handle .clone command to download website HTML."""
#     url = event.pattern_match.group(1)
#     try:
#         r = requests.get(url, timeout=10)
#         r.raise_for_status()
#         os.makedirs("downloads", exist_ok=True)
#         path = "downloads/site.html"
#         with open(path, 'w', encoding='utf-8') as f:
#             f.write(r.text)
#         await event.reply("✅ Sayt nusxalandi", file=path)
#     except requests.RequestException as e:
#         logger.error(f"Website clone error: {e}")
#         await event.reply(f"❌ Clone xatoligi: {e}")
#     finally:
#         if os.path.exists(path):
#             os.remove(path)


@client.on(events.NewMessage(pattern=r'^\.clone (.+)'))
async def clone_website(event):
    url = event.pattern_match.group(1)
    base_folder = "downloads"
    site_folder = os.path.join(base_folder, "site")
    zip_path = os.path.join(base_folder, "site.zip")

    try:
        os.makedirs(site_folder, exist_ok=True)
        r = requests.get(url, timeout=10)
        r.raise_for_status()

        html_path = os.path.join(site_folder, "index.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(r.text)

        soup = BeautifulSoup(r.text, "html.parser")
        resources = []

        for tag in soup.find_all(['link', 'script', 'img']):
            src = tag.get('href') or tag.get('src')
            if src:
                full_url = urljoin(url, src)
                parsed_url = urlparse(src)
                filename = os.path.basename(parsed_url.path)
                folder = "assets"
                if not filename:
                    continue
                try:
                    res = requests.get(full_url, timeout=5)
                    res.raise_for_status()
                    asset_path = os.path.join(site_folder, folder)
                    os.makedirs(asset_path, exist_ok=True)
                    file_path = os.path.join(asset_path, filename)
                    with open(file_path, 'wb') as f:
                        f.write(res.content)
                    # Update the src/href to local path
                    if tag.name == "link":
                        tag['href'] = f"{folder}/{filename}"
                    else:
                        tag['src'] = f"{folder}/{filename}"
                except Exception:
                    continue

        # Save modified HTML
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))

        # Zip the folder
        shutil.make_archive(site_folder, 'zip', site_folder)

        # Send zip
        await event.reply("✅ Sayt nusxalandi:", file=zip_path)

    except Exception as e:
        await event.reply(f"❌ Xatolik: {e}")

    finally:
        # Clean up
        if os.path.exists(base_folder):
            shutil.rmtree(base_folder)


YOUR_ID = 6472114736  # 🔁 Bu yerga o‘z Telegram user_id'ingizni yozing

@client.on(events.NewMessage(pattern=r'^\.mention$'))
async def mention_all(event):
    """Faqat admin (siz) ishlata oladigan umumiy at-mention buyruq."""
    if event.sender_id != YOUR_ID:
        return await event.reply("🚫 Sizda bu buyruqni ishlatish huquqi yo‘q.")

    if not event.is_group:
        return await event.reply("🚫 Bu buyruq faqat guruhlarda ishlaydi.")

    chat = await event.get_input_chat()
    mentions = []
    async for user in client.iter_participants(chat):
        if user.bot or user.deleted:
            continue
        mention = f"[{user.first_name}](tg://user?id={user.id})"
        mentions.append(mention)

    text = '👥 Barcha aʼzolar:\n\n'
    batch = 5  # Telegram limitlaridan chiqmaslik uchun
    for i in range(0, len(mentions), batch):
        try:
            chunk = mentions[i:i + batch]
            await event.reply('\n'.join(chunk), parse_mode='md')
            await asyncio.sleep(2)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
        except Exception as e:
            await event.reply(f"❌ Xatolik: {e}")
@client.on(events.NewMessage(pattern=r'^\.id(?: (.+))?'))
async def id_handler(event):
    """Handle .id command to fetch user ID."""
    username = event.pattern_match.group(1)
    try:
        if username:
            user = await client.get_entity(username)
            await event.reply(f"🆔 ID: {user.id}")
        else:
            await event.reply(f"🙋 Sizning ID: {event.sender_id}")
    except Exception as e:
        logger.error(f"ID fetch error: {e}")
        await event.reply(f"❌ ID xatoligi: {e}")






# --- AUTO PROFILE UPDATE ---
async def auto_update_name():
    """Update profile name with current timestamp every minute."""
    while True:
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        try:
            await client(UpdateProfileRequest(first_name=f"ASLIDDIN NORQOBILOV | {now}"))
            logger.info("Profile name updated")
        except FloodWaitError as e:
            logger.warning(f"Flood wait: {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Profile update error: {e}")
        await asyncio.sleep(60)


# --- LOGIN WITH 2FA ---
async def async_login():
    """Handle Telegram login with 2FA support."""
    await client.connect()
    if not await client.is_user_authorized():
        phone = input("📱 Telefon raqam (+998xxxxxxxxx): ")
        try:
            await client.send_code_request(phone)
            code = input("📩 SMS kod: ")
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("🔐 2-bosqichli parol: ")
                await client.sign_in(password=password)
        except Exception as e:
            logger.error(f"Login error: {e}")
            print(f"❌ Kirish xatoligi: {e}")
            exit(1)
import threading
import requests
import time

# URL bu sizning Railway yoki Render'dagi serveringiz URL'idir
YOUR_WEB_URL = "https://GIBRID-USERBOT.up.railway.app"  # o'zingizning URL'ni kiriting

def auto_ping():
    while True:
        try:
            response = requests.get(YOUR_WEB_URL)
            print(f"[AutoPing] Status: {response.status_code}")
        except Exception as e:
            print(f"[AutoPing Error]: {e}")
        time.sleep(270)  # har 4.5 daqiqada (270 sekundda) ping qiladi

# Avtoping funksiyasini thread orqali ishga tushuramiz
threading.Thread(target=auto_ping).start()


# --- MAIN ---
async def main():
    """Main function to start the bot."""
    try:
        clean_downloads()  # Clean up downloads directory
        await async_login()
        asyncio.create_task(auto_update_name())
        logger.info("✅ Hybrid UserBot ishga tushdi.")
        print("✅ Hybrid UserBot ishga tushdi.")
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Main loop error: {e}")
        print(f"❌ Bot ishga tushmadi: {e}")


if __name__ == "__main__":

    asyncio.run(main())
