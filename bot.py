import os
import re
import json
import asyncio
import aiohttp
import logging
import threading
from flask import Flask
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import phonenumbers
from phonenumbers import geocoder
import pycountry

# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))
API_TOKEN_1 = os.getenv("API_TOKEN_1")
API_TOKEN_2 = os.getenv("API_TOKEN_2")

if not all([BOT_TOKEN, CHAT_ID, ADMIN_ID, API_TOKEN_1, API_TOKEN_2]):
    raise RuntimeError("❌ Missing ENV variables")

# ================= CONFIG =================
FETCH_INTERVAL = 10
RECORD_LIMIT = 5
CACHE_FILE = "sent_cache.json"
SOURCE_STATE_FILE = "source_state.json"

APIS = [
    {"id": "Source 1", "url": "http://147.135.212.197/crapi/had/viewstats", "token": API_TOKEN_1},
    {"id": "Source 2", "url": "http://51.77.216.195/crapi/dgroup/viewstats", "token": API_TOKEN_2},
]

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("OTP-BOT")

bot = Bot(token=BOT_TOKEN)

# ================= KEEP ALIVE =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot running"

def run_web():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

threading.Thread(target=run_web, daemon=True).start()

# ================= HELPERS =================
def load_json(file, default):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def is_otp(msg: str):
    return any(x in msg.lower() for x in ["otp", "code", "verification", "one time"])

def extract_phone(text):
    m = re.search(r"\+?\d{10,15}", text)
    return m.group() if m else None

# ✅ REAL COUNTRY DETECTION (PHONE BASED)
def detect_country(phone):
    try:
        if not phone.startswith("+"):
            phone = "+" + phone

        parsed = phonenumbers.parse(phone, None)
        country_name = geocoder.description_for_number(parsed, "en")
        region = phonenumbers.region_code_for_number(parsed)

        if region:
            base = 127462 - ord("A")
            flag = chr(base + ord(region[0])) + chr(base + ord(region[1]))
        else:
            flag = "🌍"

        return flag, country_name or "Unknown"

    except:
        return "🌍", "Unknown"

# ================= API =================
async def fetch_api(session, api):
    async with session.get(
        api["url"],
        params={"token": api["token"], "records": RECORD_LIMIT},
        timeout=20
    ) as r:
        if "application/json" not in r.headers.get("Content-Type", ""):
            log.error(f"Non-JSON response from {api['id']}")
            return []
        data = await r.json()
        return data.get("data", []) if data.get("status") == "success" else []

# ================= OTP LOOP =================
async def otp_loop():
    sent = set(load_json(CACHE_FILE, []))
    state = load_json(SOURCE_STATE_FILE, {"Source 1": True, "Source 2": True})

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                rows = []
                for api in APIS:
                    if not state.get(api["id"], True):
                        continue
                    for r in await fetch_api(session, api):
                        r["_src"] = api["id"]
                        rows.append(r)

                if rows:
                    latest = max(rows, key=lambda x: x["dt"])
                    uid = f"{latest['dt']}_{latest['num']}"

                    if uid not in sent and is_otp(latest.get("message", "")):
                        phone = extract_phone(latest["message"]) or latest["num"]
                        flag, country = detect_country(phone)

                        text = (
                            "📩 *NEW OTP*\n\n"
                            f"{flag} *Country:* {country}\n"
                            f"📞 *Number:* `{phone}`\n"
                            f"🕒 *Time:* `{latest['dt']}`\n"
                            f"🔗 *Source:* {latest['_src']}\n\n"
                            f"💬 {latest['message']}"
                        )

                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=text,
                            parse_mode="Markdown",
                        )

                        sent.add(uid)
                        save_json(CACHE_FILE, list(sent))

            except Exception as e:
                log.error("OTP loop error", exc_info=e)

            await asyncio.sleep(FETCH_INTERVAL)

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Bot is Alive!*\n/admin – Admin Panel",
        parse_mode="Markdown",
    )

def admin_only(update: Update):
    return update.effective_user.id == ADMIN_ID

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update):
        return

    st = load_json(SOURCE_STATE_FILE, {"Source 1": True, "Source 2": True})
    await update.message.reply_text(
        "🛠 *Admin Panel*\n\n"
        f"Source 1: {'ON ✅' if st['Source 1'] else 'OFF ❌'}\n"
        f"Source 2: {'ON ✅' if st['Source 2'] else 'OFF ❌'}",
        parse_mode="Markdown",
    )

# ================= MAIN =================
def start_otp_background():
    asyncio.run(otp_loop())

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))

    threading.Thread(target=start_otp_background, daemon=True).start()
    application.run_polling()

if __name__ == "__main__":
    main()

