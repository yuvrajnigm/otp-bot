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
SOURCE_STATE_FILE = "source_state.json"

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

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("OTP-BOT")

bot = Bot(token=BOT_TOKEN)

# ================= KEEP ALIVE (PORT FIX) =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot running"

def run_web():
    port = int(os.environ.get("PORT", 10000))  # 🔥 Render FIX
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# ================= HELPERS =================
def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def is_otp(msg: str) -> bool:
    return bool(re.search(r"\b(otp|code|verification|one time)\b", msg.lower()))

def extract_phone(text):
    m = re.search(r"\+?\d{10,15}", text)
    return m.group() if m else None

def detect_country_from_phone(phone):
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
                log.error(f"❌ Non-JSON response from {api['id']}")
                return api["id"], {}

            return api["id"], await r.json()

    except Exception as e:
        log.error(f"API error {api['id']}: {e}")
        return api["id"], {}

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

                    src, data = await fetch_api(session, api)

                    if data.get("status") == "success":
                        for r in data.get("data", []):
                            r["_src"] = src
                            rows.append(r)

                if rows:
                    latest = max(rows, key=lambda x: x["dt"])
                    uid = f"{latest['dt']}_{latest['num']}"

                    if uid not in sent:
                        msg = latest.get("message", "")
                        if is_otp(msg):
                            phone = extract_phone(msg) or latest["num"]
                            flag, country = detect_country_from_phone(phone)

                            text = (
                                "🔔 *NEW OTP RECEIVED*\n\n"
                                f"{flag} *Country:* {country}\n"
                                f"📞 *Number:* `{phone}`\n"
                                f"🕒 *Time:* `{latest['dt']}`\n"
                                f"🔗 *Source:* {latest['_src']}\n\n"
                                f"💬 *Message:*\n{msg}\n\n"
                                "_by Yuvraj❤_"
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
def admin_only(update: Update):
    return update.effective_user.id == ADMIN_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot is running")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update):
        return

    st = load_json(SOURCE_STATE_FILE, {"Source 1": True, "Source 2": True})
    await update.message.reply_text(
        "🛠 Admin Panel\n\n"
        f"Source 1: {'ON ✅' if st['Source 1'] else 'OFF ❌'}\n"
        f"Source 2: {'ON ✅' if st['Source 2'] else 'OFF ❌'}"
    )

async def toggle(update: Update, src: str, val: bool):
    if not admin_only(update):
        return
    st = load_json(SOURCE_STATE_FILE, {})
    st[src] = val
    save_json(SOURCE_STATE_FILE, st)
    await update.message.reply_text(f"{src} {'ON ✅' if val else 'OFF ❌'}")

# ================= MAIN =================
def start_otp_background():
    asyncio.run(otp_loop())

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("source1_on", lambda u, c: toggle(u, "Source 1", True)))
    application.add_handler(CommandHandler("source1_off", lambda u, c: toggle(u, "Source 1", False)))
    application.add_handler(CommandHandler("source2_on", lambda u, c: toggle(u, "Source 2", True)))
    application.add_handler(CommandHandler("source2_off", lambda u, c: toggle(u, "Source 2", False)))

    threading.Thread(target=start_otp_background, daemon=True).start()
    application.run_polling()

if __name__ == "__main__":
    main()
