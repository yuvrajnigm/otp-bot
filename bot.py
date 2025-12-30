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

# ================= APIS =================
APIS = [
    {
        "id": "Source 1",
        "url": "http://147.135.212.197/crapi/had/viewstats",
        "token": API_TOKEN_1,
    },
    {
        "id": "Source 2",
        "url": "http://51.77.216.195/crapi/dgroup/viewstats",
        "token": API_TOKEN_2,
    },
]

# ================= LOG =================
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("OTP-BOT")

bot = Bot(token=BOT_TOKEN)

# ================= KEEP ALIVE (RENDER FIX) =================
app = Flask(__name__)

@app.route("/")
def home():
    return "OTP Bot running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# ================= HELPERS =================
def load_sent():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_sent(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(list(data), f)

def is_otp(text: str) -> bool:
    return bool(re.search(r"\b(otp|code|verification|one time)\b", text.lower()))

def extract_phone(text):
    m = re.search(r"\+?\d{10,15}", text)
    return m.group() if m else "Unknown"

def detect_country(phone):
    try:
        num = phonenumbers.parse(phone, None)
        region = phonenumbers.region_code_for_number(num)
        country = geocoder.description_for_number(num, "en")
        flag = "".join(chr(127397 + ord(c)) for c in region)
        return flag, country
    except:
        return "🏳️", "Unknown"

# ================= API FETCH =================
async def fetch_api(session, api):
    try:
        async with session.get(
            api["url"],
            params={"token": api["token"], "records": RECORD_LIMIT},
            timeout=15,
        ) as r:

            if "application/json" not in r.headers.get("Content-Type", ""):
                return []

            data = await r.json()
            if data.get("status") == "success":
                return data.get("data", [])
            return []

    except Exception as e:
        log.error(f"{api['id']} error: {e}")
        return []

# ================= OTP LOOP =================
async def otp_loop():
    sent = load_sent()

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                rows = []
                for api in APIS:
                    rows.extend(await fetch_api(session, api))

                if rows:
                    latest = max(rows, key=lambda x: x["dt"])
                    uid = f"{latest['dt']}_{latest['num']}"

                    if uid not in sent:
                        msg = latest.get("message", "")
                        if is_otp(msg):
                            phone = extract_phone(msg)
                            flag, country = detect_country(phone)

                            text = (
                                "🔔 *OTP RECEIVED*\n\n"
                                f"{flag} *Country:* {country}\n"
                                f"📞 *Number:* `{phone}`\n"
                                f"🕒 *Time:* `{latest['dt']}`\n\n"
                                f"💬 *Message:*\n{msg}\n\n"
                                "_by Yuvraj❤_"
                            )

                            await bot.send_message(
                                chat_id=CHAT_ID,
                                text=text,
                                parse_mode="Markdown",
                            )

                            sent.add(uid)
                            save_sent(sent)

            except Exception as e:
                log.error("OTP loop error", exc_info=e)

            await asyncio.sleep(FETCH_INTERVAL)

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 OTP Bot is running")

# ================= MAIN =================
def start_background():
    asyncio.run(otp_loop())

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    threading.Thread(target=start_background, daemon=True).start()
    application.run_polling()

if __name__ == "__main__":
    main()
