import asyncio
import aiohttp
import json
import os
import re
import time
from telegram import Bot
import phonenumbers
from phonenumbers import geocoder

# ================= CONFIG =================
BOT_TOKEN = "8363735598:AAHf_O4pCS9A6V0m175tf2YpZcmglfsNkNw"
CHANNEL_ID = -1003406789899
ADMIN_ID = 8449115253

API_TOKEN_1 = "R1NYQjRSQkF8cm5Dak-QWmFpmHZ0i4ZjQoxzdItykoh4lnVHfXZX"
API_TOKEN_2 = "Q1JVQjRSQop9hmhHepdUdUl_hYpblXZ4VHOWQoBTi3pfimxgeG-Q"

APIS = [
    ("HADI", "http://147.135.212.197/crapi/had/viewstats", API_TOKEN_1),
    ("DGROUP", "http://51.77.216.195/crapi/dgroup/viewstats", API_TOKEN_2),
]

FETCH_INTERVAL = 10
RECORDS = 5
CACHE_FILE = "sent_cache.json"
OTP_TTL = 86400  # 24 hours

bot = Bot(token=BOT_TOKEN)
START_TIME = time.time()
LAST_UPDATE_ID = 0

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

def clear_cache():
    sent_cache.clear()
    save_cache()

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
        return country, code, flag
    except:
        return "Unknown", "XX", "🏳️"

# ================= SERVICE =================
def detect_service(cli, msg):
    text = (cli + msg).lower()
    if "whatsapp" in text:
        return "WhatsApp", "🟢", "🔔🔔🔔"
    if "facebook" in text:
        return "Facebook", "🔵", "🚨🚨🚨"
    if "google" in text:
        return "Google", "🟡", "🔥🔥🔥"
    return cli.upper(), "📩", "🔔🔔🔔"

def extract_otp(msg):
    m = re.search(r"\b\d{3}[- ]?\d{3}\b|\b\d{4,8}\b", msg)
    return m.group() if m else "N/A"

# ================= FORMAT =================
def format_message(d):
    country, code, flag = country_details(d["num"])
    service, semoji, anim = detect_service(d["cli"], d["message"])
    otp = extract_otp(d["message"])

    return f"""
{anim} {flag} {country.upper()} OTP ALERT {flag} {anim}

{semoji} {service} OTP RECEIVED {semoji}

🕰 Time: {d['dt']}
📞 Number: +{d['num'][:4]}****{d['num'][-4:]}
🔑 OTP: `{otp}`

━━━━━━━━━━━━━━━━━━
👑 Owner: 💗 Yuvraj 💗
🏷️ #{country.replace(" ", "")} #{service}OTP
━━━━━━━━━━━━━━━━━━
""".strip()

# ================= API FETCH =================
async def fetch_api(session, url, token):
    try:
        async with session.get(
            url,
            params={"token": token, "records": RECORDS},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as r:
            if r.status != 200:
                return []
            data = await r.json()
            return data.get("data", [])
    except Exception as e:
        print("API ERROR:", e)
        return []

# ================= ADMIN COMMANDS =================
async def check_admin_commands():
    global LAST_UPDATE_ID
    updates = await bot.get_updates(offset=LAST_UPDATE_ID + 1, timeout=0)

    for u in updates:
        LAST_UPDATE_ID = u.update_id

        if not u.message or u.message.chat_id != ADMIN_ID:
            continue

        text = u.message.text.strip()

        if text == "/status":
            uptime = int(time.time() - START_TIME)
            h, m = divmod(uptime // 60, 60)
            msg = (
                "✅ OTP Bot Online\n"
                f"⏱ Uptime: {h}h {m}m\n"
                f"📊 Cached OTPs: {len(sent_cache)}\n"
                f"🔁 Fetch interval: {FETCH_INTERVAL} sec\n"
                "🟢 Platform: Railway"
            )
            await bot.send_message(ADMIN_ID, msg)

        elif text == "/clearcache":
            clear_cache()
            await bot.send_message(
                ADMIN_ID,
                "🧹 Cache Cleared Successfully!\n"
                f"📊 Cached OTPs: {len(sent_cache)}"
            )

# ================= WORKER =================
async def worker():
    print("🚀 OTP BOT STARTED (Railway Worker)")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                cleanup_cache()
                await check_admin_commands()

                for _, url, token in APIS:
                    records = await fetch_api(session, url, token)
                    for d in records:
                        uid = d["dt"] + d["num"] + d["message"]
                        if uid in sent_cache:
                            continue
                        sent_cache[uid] = time.time()
                        save_cache()
                        await bot.send_message(
                            chat_id=CHANNEL_ID,
                            text=format_message(d),
                            parse_mode="Markdown",
                        )

                await asyncio.sleep(FETCH_INTERVAL)
            except Exception as e:
                print("SAFE LOOP ERROR:", e)
                await asyncio.sleep(5)

# ================= START =================
if __name__ == "__main__":
    asyncio.run(worker())
