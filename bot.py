import asyncio
import aiohttp
import json
import os
import re
import time
import threading
from datetime import datetime
from flask import Flask
from telegram import Bot
import phonenumbers
from phonenumbers import geocoder

# ================= BASIC CONFIG =================
BOT_TOKEN = "8294446224:AAEVBGLnx0KigNEOSAHQ4Psb70YYp7Qi938"
CHANNEL_ID = -1003406789899
ADMIN_ID = 8449115253

API_TOKEN_1 = "R1NYQjRSQkF8cm5Dak-QWmFpmHZ0i4ZjQoxzdItykoh4lnVHfXZX"
API_TOKEN_2 = "Q1JVQjRSQop9hmhHepdUdUl_hYpblXZ4VHOWQoBTi3pfimxgeG-Q"

APIS = [
    ("HADI", "http://147.135.212.197/crapi/had/viewstats", API_TOKEN_1),
    ("DGROUP", "http://51.77.216.195/crapi/dgroup/viewstats", API_TOKEN_2),
]

FETCH_INTERVAL = 12
RECORDS = 5
CACHE_FILE = "sent_cache.json"
OTP_TTL = 86400

SELF_PING_URL = os.getenv("SELF_PING_URL")
SELF_PING_INTERVAL = 300  # 5 min

# ================= DGROUP CONTROL =================
DGROUP_FAIL_COUNT = 0
DGROUP_DISABLED_UNTIL = 0
DGROUP_MAX_FAILS = 5
DGROUP_DISABLE_TIME = 600
DGROUP_RETRY_DELAY = 30

# ================= ERROR ALERT CONTROL =================
LAST_ERROR_TIME = 0
ERROR_COOLDOWN = 300

# ================= BOT INIT =================
bot = Bot(token=BOT_TOKEN)
bot.delete_webhook(drop_pending_updates=True)

app = Flask(__name__)
START_TIME = time.time()

# ================= DAILY STATS =================
sent_today = 0
last_report_date = datetime.utcnow().date()

# ================= CACHE =================
sent_cache = {}
if os.path.exists(CACHE_FILE):
    try:
        sent_cache = json.load(open(CACHE_FILE))
    except:
        sent_cache = {}

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(sent_cache, f)

def cleanup_cache():
    now = time.time()
    for k in list(sent_cache.keys()):
        if now - sent_cache[k] > OTP_TTL:
            del sent_cache[k]
    save_cache()

# ================= COUNTRY =================
def country_details(number):
    try:
        num = phonenumbers.parse("+" + number)
        country = geocoder.description_for_number(num, "en")
        code = phonenumbers.region_code_for_number(num)
        flag = "".join(chr(127397 + ord(c)) for c in code)
        return country, flag
    except:
        return "Unknown", "🏳️"

# ================= SERVICE =================
def detect_service(cli, msg):
    t = (cli + msg).lower()
    if "whatsapp" in t:
        return "WhatsApp", "🟢"
    if "facebook" in t:
        return "Facebook", "🔵"
    if "google" in t:
        return "Google", "🟡"
    return cli.upper(), "📩"

def extract_otp(msg):
    m = re.search(r"\b\d{3}[- ]?\d{3}\b|\b\d{4,8}\b", msg)
    return m.group() if m else "N/A"

def format_message(d):
    country, flag = country_details(d["num"])
    service, emoji = detect_service(d["cli"], d["message"])
    otp = extract_otp(d["message"])
    return f"""
🔔 {flag} {country} OTP ALERT 🔔

{emoji} Service: {service}
📞 Number: +{d['num'][:4]}****{d['num'][-4:]}
🔑 OTP: `{otp}`

👑 Owner: 💗 Yuvraj 💗
""".strip()

# ================= KEEP ALIVE =================
@app.route("/")
def home():
    return "Bot Alive"

@app.route("/health")
def health():
    return {"status": "ok", "cache": len(sent_cache)}

# ================= ALERT =================
async def send_crash_alert(error):
    global LAST_ERROR_TIME
    now = time.time()
    if now - LAST_ERROR_TIME < ERROR_COOLDOWN:
        return
    LAST_ERROR_TIME = now
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🚨 OTP BOT ERROR ALERT 🚨\n"
            f"⏰ Time: {datetime.utcnow()}\n"
            f"❌ Error: {error}"
        )
    except:
        pass

# ================= DAILY REPORT =================
async def daily_report():
    global sent_today, last_report_date
    while True:
        await asyncio.sleep(60)
        now = datetime.utcnow()
        if now.date() != last_report_date:
            uptime = int(time.time() - START_TIME)
            h, m = divmod(uptime // 60, 60)
            await bot.send_message(
                ADMIN_ID,
                f"📊 DAILY OTP REPORT\n"
                f"📅 Date: {last_report_date}\n"
                f"📨 OTPs Sent: {sent_today}\n"
                f"📦 Cache Size: {len(sent_cache)}\n"
                f"⏱ Uptime: {h}h {m}m\n"
                f"🟢 Status: Online"
            )
            sent_today = 0
            last_report_date = now.date()

# ================= SELF PING =================
async def self_ping():
    if not SELF_PING_URL:
        return
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await session.get(SELF_PING_URL + "/health", timeout=10)
            except:
                pass
            await asyncio.sleep(SELF_PING_INTERVAL)

# ================= OTP WORKER =================
async def otp_worker():
    global sent_today, DGROUP_FAIL_COUNT, DGROUP_DISABLED_UNTIL

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                cleanup_cache()

                for name, url, token in APIS:

                    if name == "DGROUP":
                        if time.time() < DGROUP_DISABLED_UNTIL:
                            continue

                    try:
                        async with session.get(
                            url,
                            params={"token": token, "records": RECORDS},
                            timeout=20
                        ) as r:

                            ctype = r.headers.get("Content-Type", "")
                            if "application/json" not in ctype:
                                raise Exception(f"{name} non-JSON response")

                            data = (await r.json()).get("data", [])

                            if name == "DGROUP":
                                DGROUP_FAIL_COUNT = 0

                            for d in data:
                                uid = d["dt"] + d["num"] + d["message"]
                                if uid in sent_cache:
                                    continue
                                sent_cache[uid] = time.time()
                                save_cache()
                                sent_today += 1
                                bot.send_message(CHANNEL_ID, format_message(d))

                    except Exception as e:
                        if name == "DGROUP":
                            DGROUP_FAIL_COUNT += 1
                            if DGROUP_FAIL_COUNT >= DGROUP_MAX_FAILS:
                                DGROUP_DISABLED_UNTIL = time.time() + DGROUP_DISABLE_TIME
                                DGROUP_FAIL_COUNT = 0
                                await bot.send_message(
                                    ADMIN_ID,
                                    "⚠️ DGROUP API disabled for 10 minutes (auto)"
                                )
                            await asyncio.sleep(DGROUP_RETRY_DELAY)
                        else:
                            await send_crash_alert(e)

                await asyncio.sleep(FETCH_INTERVAL)

            except Exception as e:
                await send_crash_alert(e)
                await asyncio.sleep(5)

# ================= START =================
def start_async():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(otp_worker())
    loop.create_task(self_ping())
    loop.create_task(daily_report())
    loop.run_forever()

if __name__ == "__main__":
    threading.Thread(target=start_async, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
