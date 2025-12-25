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
import pycountry

# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))

API_TOKEN_1 = os.getenv("API_TOKEN_1")
API_TOKEN_2 = os.getenv("API_TOKEN_2")

if not BOT_TOKEN or not API_TOKEN_1 or not API_TOKEN_2:
    raise RuntimeError("Missing ENV variables")

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
        "token": API_TOKEN_1
    },
    {
        "id": "Source 2",
        "url": "http://51.77.216.195/crapi/dgroup/viewstats",
        "token": API_TOKEN_2
    }
]

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("OTP-BOT")

bot = Bot(token=BOT_TOKEN)

# ================= KEEP ALIVE =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot running"

def run_web():
    app.run(host="0.0.0.0", port=8080)

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

def is_otp(msg):
    return any(x in msg.lower() for x in ["otp", "code", "verification", "one time"])

def extract_phone(text):
    m = re.search(r"\+?\d{10,15}", text)
    return m.group() if m else None

def detect_country(phone):
    try:
        num = phonenumbers.parse(phone, None)
        reg = phonenumbers.region_code_for_number(num)
        country = pycountry.countries.get(alpha_2=reg)
        flag = "".join(chr(127397 + ord(c)) for c in reg)
        return flag, country.name if country else "Unknown"
    except:
        return "🏳️", "Unknown"

# ================= API =================
async def fetch_api(session, api):
    async with session.get(
        api["url"],
        params={"token": api["token"], "records": RECORD_LIMIT},
        timeout=20
    ) as r:
        return api["id"], await r.json()

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
                        msg = latest["message"]
                        if is_otp(msg):
                            phone = extract_phone(msg) or latest["num"]
                            flag, country = detect_country(phone)

                            text = (
                                "📩 *NEW OTP*\n\n"
                                f"{flag} *Country:* {country}\n"
                                f"📞 *Number:* `{phone}`\n"
                                f"🕒 *Time:* `{latest['dt']}`\n"
                                f"🔗 *Source:* {latest['_src']}\n\n"
                                f"💬 {msg}"
                            )

                            await bot.send_message(
                                chat_id=CHAT_ID,
                                text=text,
                                parse_mode="Markdown"
                            )

                            sent.add(uid)
                            save_json(CACHE_FILE, list(sent))

            except Exception as e:
                log.error(e)

            await asyncio.sleep(FETCH_INTERVAL)

# ================= ADMIN =================
def admin_only(update: Update):
    return update.effective_user.id == ADMIN_ID

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update):
        return

    st = load_json(SOURCE_STATE_FILE, {"Source 1": True, "Source 2": True})
    await update.message.reply_text(
        f"🛠 Admin Panel\n\n"
        f"Source 1: {st['Source 1']}\n"
        f"Source 2: {st['Source 2']}\n\n"
        "/source1_on /source1_off\n"
        "/source2_on /source2_off"
    )

async def toggle(update: Update, src: str, val: bool):
    if not admin_only(update):
        return
    st = load_json(SOURCE_STATE_FILE, {})
    st[src] = val
    save_json(SOURCE_STATE_FILE, st)
    await update.message.reply_text(f"{src} {'ON' if val else 'OFF'}")

# ================= MAIN =================
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("source1_on", lambda u,c: toggle(u,"Source 1",True)))
    application.add_handler(CommandHandler("source1_off", lambda u,c: toggle(u,"Source 1",False)))
    application.add_handler(CommandHandler("source2_on", lambda u,c: toggle(u,"Source 2",True)))
    application.add_handler(CommandHandler("source2_off", lambda u,c: toggle(u,"Source 2",False)))

    # 🔥 start OTP loop safely
    application.job_queue.run_once(lambda ctx: asyncio.create_task(otp_loop()), 0)

    application.run_polling()

if __name__ == "__main__":
    main()
