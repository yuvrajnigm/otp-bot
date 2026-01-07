import os, time, json, asyncio, aiohttp, threading, re
from datetime import datetime
from flask import Flask, jsonify
from telegram import Bot
import phonenumbers
import pycountry
from bs4 import BeautifulSoup

# ================== CONFIG ==================
BOT_TOKEN = "8294446224:AAEVBGLnx0KigNEOSAHQ4Psb70YYp7Qi938"
ADMIN_ID = 8449115253
CHANNEL_ID = -1003406789899

HADI_API_TOKEN = "R1NYQjRSQkF8cm5Dak-QWmFpmHZ0i4ZjQoxzdItykoh4lnVHfXZX"
DGROUP_API_TOKEN = "Q1JVQjRSQop9hmhHepdUdUl_hYpblXZ4VHOWQoBTi3pfimxgeG-Q"

FETCH_INTERVAL = 10
CACHE_FILE = "sent_cache.json"

# only this from env
SELF_PING_URL = os.getenv("SELF_PING_URL")

# ================== INIT ==================
bot = Bot(BOT_TOKEN)
START_TIME = time.time()
sent_cache = set()

# ================== CACHE ==================
def load_cache():
    global sent_cache
    if os.path.exists(CACHE_FILE):
        try:
            sent_cache = set(json.load(open(CACHE_FILE)))
        except:
            sent_cache = set()

def save_cache():
    json.dump(list(sent_cache), open(CACHE_FILE, "w"))

load_cache()

# ================== COUNTRY + FLAG ==================
def get_country_info(number):
    try:
        parsed = phonenumbers.parse(number, None)
        region = phonenumbers.region_code_for_number(parsed)
        country = pycountry.countries.get(alpha_2=region)
        name = country.name if country else "Unknown"
        flag = "".join(chr(127397 + ord(c)) for c in region)
        return name, flag
    except:
        return "Unknown", "🏳️"

# ================== DGROUP HTML PARSER ==================
def parse_dgroup_html(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ")

    otp = None
    m = re.search(r"\b\d{4,8}\b", text)
    if m:
        otp = m.group()

    num = "Unknown"
    n = re.search(r"\+?\d{8,15}", text)
    if n:
        num = n.group()

    service = "Unknown"
    if "whatsapp" in text.lower():
        service = "WhatsApp"
    elif "telegram" in text.lower():
        service = "Telegram"
    elif "facebook" in text.lower():
        service = "Facebook"

    return otp, num, service

# ================== FLASK (KEEP ALIVE) ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "OTP Bot Alive", 200

@app.route("/health")
def health():
    return jsonify({"status": "ok", "cache": len(sent_cache)})

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# ================== SELF PING ==================
async def self_ping():
    if not SELF_PING_URL:
        return
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await session.get(SELF_PING_URL + "/health", timeout=10)
            except:
                pass
            await asyncio.sleep(300)

# ================== ADMIN COMMANDS ==================
async def admin_command_listener():
    offset = None
    while True:
        try:
            updates = await bot.get_updates(offset=offset, timeout=20)
            for u in updates:
                offset = u.update_id + 1
                if not u.message or not u.message.text:
                    continue

                chat_id = u.message.chat.id
                text = u.message.text.strip()

                if text == "/start":
                    await bot.send_message(chat_id, "🤖 OTP Bot is running ✅")
                    continue

                if chat_id != ADMIN_ID:
                    continue

                if text == "/status":
                    uptime = int(time.time() - START_TIME)
                    h, m = divmod(uptime // 60, 60)
                    await bot.send_message(
                        ADMIN_ID,
                        f"✅ OTP Bot Online\n"
                        f"⏱ Uptime: {h}h {m}m\n"
                        f"📦 Cached OTPs: {len(sent_cache)}\n"
                        f"🔁 Interval: {FETCH_INTERVAL}s\n"
                        "🟢 Platform: Render/VPS"
                    )

                elif text == "/clearcache":
                    sent_cache.clear()
                    save_cache()
                    await bot.send_message(ADMIN_ID, "🧹 Cache cleared")

        except Exception as e:
            print("CMD ERROR:", e)

        await asyncio.sleep(2)

# ================== OTP WORKER ==================
async def otp_worker():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # ---- HADI (JSON) ----
                hadi_url = f"http://147.135.212.197/crapi/had/viewstats?token={HADI_API_TOKEN}&records=5"
                async with session.get(hadi_url, timeout=15) as r:
                    if "application/json" in r.headers.get("content-type", ""):
                        data = await r.json()
                        for d in data.get("data", []):
                            uid = d.get("dt", "") + d.get("num", "")
                            if uid in sent_cache:
                                continue
                            sent_cache.add(uid)
                            save_cache()

                            country, flag = get_country_info("+" + d.get("num", ""))
                            msg = (
                                f"🔔 {flag} New OTP\n\n"
                                f"📞 Number: +{d.get('num')}\n"
                                f"🔑 OTP: {re.findall(r'\\d{4,8}', d.get('message',''))}\n\n"
                                "Powered By 💗 Yuvraj"
                            )
                            await bot.send_message(CHANNEL_ID, msg)

                # ---- DGROUP (HTML fallback) ----
                dgroup_url = f"http://51.77.216.195/crapi/dgroup/viewstats?token={DGROUP_API_TOKEN}&records=1"
                async with session.get(dgroup_url, timeout=15) as r:
                    html = await r.text()
                    otp, num, service = parse_dgroup_html(html)
                    if otp and num:
                        uid = num + otp
                        if uid not in sent_cache:
                            sent_cache.add(uid)
                            save_cache()
                            country, flag = get_country_info(num)
                            msg = (
                                f"🔔 {flag} {service} OTP\n\n"
                                f"📞 Number: {num}\n"
                                f"🔑 OTP: {otp}\n\n"
                                "Powered By 💗 Yuvraj"
                            )
                            await bot.send_message(CHANNEL_ID, msg)

            except Exception as e:
                print("OTP ERROR:", e)

            await asyncio.sleep(FETCH_INTERVAL)

# ================== DAILY REPORT ==================
async def daily_report():
    await asyncio.sleep(60)
    while True:
        msg = (
            "📊 Daily OTP Report\n\n"
            f"📅 Date: {datetime.utcnow().strftime('%d %b %Y')}\n"
            f"📨 Total Cached OTPs: {len(sent_cache)}\n"
            f"⏱ Interval: {FETCH_INTERVAL}s\n"
            "🟢 Status: Running\n\n"
            "Powered By 💗 Yuvraj"
        )
        await bot.send_message(ADMIN_ID, msg)
        await asyncio.sleep(86400)

# ================== MAIN ==================
async def main():
    asyncio.create_task(otp_worker())
    asyncio.create_task(admin_command_listener())
    asyncio.create_task(self_ping())
    asyncio.create_task(daily_report())

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    asyncio.run(main())
