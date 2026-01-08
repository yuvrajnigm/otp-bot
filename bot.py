import asyncio, aiohttp, json, os, re, time, threading
from datetime import datetime
from telegram import Bot
from flask import Flask, jsonify
import phonenumbers
from phonenumbers import geocoder
from bs4 import BeautifulSoup

# ================= CONFIG =================
BOT_TOKEN = "8294446224:AAEVBGLnx0KigNEOSAHQ4Psb70YYp7Qi938"
ADMIN_ID = 8449115253
CHANNEL_ID = -1003406789899

HADI_API_TOKEN = "R1NYQjRSQkF8cm5Dak-QWmFpmHZ0i4ZjQoxzdItykoh4lnVHfXZX"
DGROUP_API_TOKEN = "Q1JVQjRSQop9hmhHepdUdUl_hYpblXZ4VHOWQoBTi3pfimxgeG-Q"

FETCH_INTERVAL = 10
CACHE_FILE = "sent_cache.json"

bot = Bot(BOT_TOKEN)
START_TIME = time.time()
sent_cache = set()

# ================= CACHE =================
if os.path.exists(CACHE_FILE):
    try:
        sent_cache = set(json.load(open(CACHE_FILE)))
    except:
        sent_cache = set()

def save_cache():
    json.dump(list(sent_cache), open(CACHE_FILE, "w"))

# ================= COUNTRY + FLAG =================
def detect_country(number):
    try:
        if not number.startswith("+"):
            number = "+" + number

        p = phonenumbers.parse(number, None)
        country = geocoder.description_for_number(p, "en")
        region = phonenumbers.region_code_for_number(p)
        flag = "".join(chr(127397 + ord(c)) for c in region)
        formatted = f"+{p.country_code} {p.national_number}"
        return country or "Unknown", flag, formatted
    except:
        return "Unknown", "🏳️", number

# ================= SERVICE =================
def detect_service(text):
    t = text.lower()
    if "telegram" in t: return "Telegram"
    if "whatsapp" in t: return "WhatsApp"
    if "facebook" in t: return "Facebook"
    if "google" in t or "gmail" in t: return "Google"
    return "Unknown"

# ================= DGROUP HTML =================
def parse_dgroup_html(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ")

    otp = re.search(r"\b\d{4,8}\b", text)
    num = re.search(r"\b\d{9,15}\b", text)

    return (
        otp.group() if otp else None,
        num.group() if num else None,
        detect_service(text),
        text.strip()
    )

# ================= FLASK =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Alive"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

# ================= COMMAND LISTENER =================
async def command_listener():
    offset = None
    while True:
        updates = await bot.get_updates(offset=offset, timeout=30)
        for u in updates:
            offset = u.update_id + 1
            if not u.message or not u.message.text:
                continue

            chat_id = u.message.chat.id
            text = u.message.text.strip()

            if text == "/start":
                await bot.send_message(chat_id, "✅ OTP Bot is running")
                continue

            if chat_id != ADMIN_ID:
                continue

            if text == "/status":
                up = int(time.time() - START_TIME)
                h, m = divmod(up // 60, 60)
                await bot.send_message(
                    ADMIN_ID,
                    f"✅ OTP Bot Online\n⏱ Uptime: {h}h {m}m\n📦 Cached: {len(sent_cache)}"
                )

            if text == "/clearcache":
                sent_cache.clear()
                save_cache()
                await bot.send_message(ADMIN_ID, "🧹 Cache cleared")

        await asyncio.sleep(1)

# ================= OTP WORKER =================
async def otp_worker():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # ===== HADI =====
                url = f"http://147.135.212.197/crapi/had/viewstats?token={HADI_API_TOKEN}&records=5"
                async with session.get(url, timeout=15) as r:
                    if "json" in r.headers.get("content-type",""):
                        data = await r.json()
                        for d in data.get("data", []):
                            otp = re.search(r"\d{4,8}", d["message"])
                            if not otp: continue

                            uid = d["num"] + otp.group()
                            if uid in sent_cache: continue
                            sent_cache.add(uid); save_cache()

                            country, flag, number = detect_country(d["num"])
                            service = detect_service(d["message"])
                            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                            await bot.send_message(
                                CHANNEL_ID,
                                f"🔔 {flag} New {country} {service} OTP!\n\n"
                                f"🕰 Time: {now}\n"
                                f"🌍 Country: {country} {flag}\n"
                                f"🟢 Service: {service}\n"
                                f"📞 Number: {number}\n"
                                f"🔑 OTP: {otp.group()}\n\n"
                                f"📩 Full Message:\n{d['message']}\n\n"
                                f"Powered By 😈 Yuvraj 😈"
                            )

                # ===== DGROUP =====
                durl = f"http://51.77.216.195/crapi/dgroup/viewstats?token={DGROUP_API_TOKEN}&records=1"
                async with session.get(durl, timeout=15) as r:
                    html = await r.text()
                    otp, num, service, full = parse_dgroup_html(html)
                    if otp and num:
                        uid = num + otp
                        if uid not in sent_cache:
                            sent_cache.add(uid); save_cache()
                            country, flag, number = detect_country(num)
                            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                            await bot.send_message(
                                CHANNEL_ID,
                                f"🔔 {flag} New {country} {service} OTP!\n\n"
                                f"🕰 Time: {now}\n"
                                f"🌍 Country: {country} {flag}\n"
                                f"🟢 Service: {service}\n"
                                f"📞 Number: {number}\n"
                                f"🔑 OTP: {otp}\n\n"
                                f"📩 Full Message:\n{full}\n\n"
                                f"Powered By 😈 Yuvraj 😈"
                            )

            except Exception as e:
                print("OTP ERROR:", e)

            await asyncio.sleep(FETCH_INTERVAL)

# ================= MAIN =================
async def main():
    await asyncio.gather(command_listener(), otp_worker())

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
