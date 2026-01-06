import asyncio, aiohttp, json, os, re, threading, time
from telegram import Bot
from flask import Flask
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

# ================= CACHE =================
sent_cache = {}  # uid -> timestamp
if os.path.exists(CACHE_FILE):
    sent_cache = json.load(open(CACHE_FILE))

def save_cache():
    json.dump(sent_cache, open(CACHE_FILE, "w"))

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
    t = (cli + msg).lower()
    if "whatsapp" in t: return "WhatsApp","🟢","🔔🔔🔔"
    if "facebook" in t: return "Facebook","🔵","🚨🚨🚨"
    if "google" in t: return "Google","🟡","🔥🔥🔥"
    return cli.upper(),"📩","🔔🔔🔔"

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
🏷️ #{country.replace(" ","")} #{service}OTP
━━━━━━━━━━━━━━━━━━
""".strip()

# ================= FETCH =================
async def fetch_api(session, url, token):
    async with session.get(url, params={"token":token,"records":RECORDS}, timeout=20) as r:
        if r.status != 200:
            return []
        return (await r.json()).get("data", [])

async def worker():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                cleanup_cache()
                for _, url, token in APIS:
                    data = await fetch_api(session, url, token)
                    for d in data:
                        uid = d["dt"] + d["num"] + d["message"]
                        if uid in sent_cache:
                            continue
                        sent_cache[uid] = time.time()
                        save_cache()
                        await bot.send_message(CHANNEL_ID, format_message(d))
            except Exception as e:
                print("SAFE ERROR:", e)
                await asyncio.sleep(5)
            await asyncio.sleep(FETCH_INTERVAL)

# ================= KEEP ALIVE =================
app = Flask("alive")
@app.route("/")
def home():
    return "BOT LIVE"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ================= START =================
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    asyncio.run(worker())
