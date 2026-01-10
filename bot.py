import asyncio, aiohttp, json, os, re, time, threading
from datetime import datetime
from telegram import Bot
from flask import Flask, jsonify
import phonenumbers
from phonenumbers import geocoder

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

# ================= COUNTRY + NUMBER =================
def detect_country_and_mask(number: str):
    try:
        if not number.startswith("+"):
            number = "+" + number

        p = phonenumbers.parse(number, None)
        country = geocoder.description_for_number(p, "en") or "Unknown"
        region = phonenumbers.region_code_for_number(p)
        flag = "".join(chr(127397 + ord(c)) for c in region)

        national = str(p.national_number)
        masked = national[:2] + "****" + national[-4:]
        masked_number = f"+{p.country_code} {masked}"

        return country, flag, masked_number
    except:
        return "Unknown", "🏳️", number

# ================= SERVICE + EMOJI =================
def detect_service_and_emoji(text: str):
    t = text.lower()
    if "whatsapp" in t:
        return "WhatsApp", "🟢📲"
    if "telegram" in t:
        return "Telegram", "🔵✈️"
    if "facebook" in t:
        return "Facebook", "🔵📘"
    if "google" in t or "gmail" in t:
        return "Google", "🔴🔐"
    return "Unknown", "📩"

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
                    f"✅ OTP Bot Online\n"
                    f"⏱ Uptime: {h}h {m}m\n"
                    f"📦 Cached OTPs: {len(sent_cache)}"
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
                hurl = f"http://147.135.212.197/crapi/had/viewstats?token={HADI_API_TOKEN}&records=5"
                async with session.get(hurl, timeout=15) as r:
                    if "json" in r.headers.get("content-type",""):
                        data = await r.json()
                        for d in data.get("data", []):
                            raw = d.get("message","")
                            otp_match = re.search(r"\d{4,8}", raw)
                            if not otp_match:
                                continue

                            num = d.get("num","")
                            uid = num + otp_match.group()
                            if uid in sent_cache:
                                continue

                            sent_cache.add(uid)
                            save_cache()

                            country, flag, masked = detect_country_and_mask(num)
                            service, emoji = detect_service_and_emoji(raw)
                            now = d.get("dt", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

                            await bot.send_message(
                                CHANNEL_ID,
                                f"🔔 {flag} New {country} {service} OTP!\n\n"
                                f"{emoji} Service: {service}\n"
                                f"🕰 Time: {now}\n"
                                f"🌍 Country: {country} {flag}\n"
                                f"📞 Number: {masked}\n"
                                f"🔑 OTP: {otp_match.group()}\n\n"
                                f"📩 Full Message:\n{raw}\n\n"
                                f"Powered By 😈 Yuvraj 😈"
                            )

                # ===== DGROUP (JSON CLEAN) =====
                durl = f"http://51.77.216.195/crapi/dgroup/viewstats?token={DGROUP_API_TOKEN}&records=1"
                async with session.get(durl, timeout=15) as r:
                    if "json" not in r.headers.get("content-type",""):
                        continue

                    data = await r.json()
                    rows = data.get("data", [])
                    if not rows:
                        continue

                    d = rows[0]
                    raw = d.get("message","")
                    otp_match = re.search(r"\d{4,8}", raw)
                    if not otp_match:
                        continue

                    num = d.get("num","")
                    uid = num + otp_match.group()
                    if uid in sent_cache:
                        continue

                    sent_cache.add(uid)
                    save_cache()

                    country, flag, masked = detect_country_and_mask(num)
                    service = d.get("cli","Unknown")
                    emoji = "🟢📲" if service.lower()=="whatsapp" else "🔵✈️" if service.lower()=="telegram" else "📩"
                    now = d.get("dt", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

                    await bot.send_message(
                        CHANNEL_ID,
                        f"🔔 {flag} New {country} {service} OTP!\n\n"
                        f"{emoji} Service: {service}\n"
                        f"🕰 Time: {now}\n"
                        f"🌍 Country: {country} {flag}\n"
                        f"📞 Number: {masked}\n"
                        f"🔑 OTP: {otp_match.group()}\n\n"
                        f"📩 Full Message:\n{raw}\n\n"
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
