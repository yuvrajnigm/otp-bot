
import os
import re
import json
import asyncio
import aiohttp
import logging
import threading
from flask import Flask
from telegram import (
    Bot,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
import phonenumbers
from phonenumbers import geocoder

# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))
API_TOKEN_1 = os.getenv("API_TOKEN_1")
API_TOKEN_2 = os.getenv("API_TOKEN_2")

if not all([BOT_TOKEN, CHAT_ID, ADMIN_ID, API_TOKEN_1, API_TOKEN_2]):
    raise RuntimeError("Missing ENV variables")

# ================= CONFIG =================
FETCH_INTERVAL = 10
RECORD_LIMIT = 5
CACHE_FILE = "sent_cache.json"

APIS = [
    {"id": "Source 1", "url": "http://147.135.212.197/crapi/had/viewstats", "token": API_TOKEN_1},
    {"id": "Source 2", "url": "http://51.77.216.195/crapi/dgroup/viewstats", "token": API_TOKEN_2},
]

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("OTP-BOT")

bot = Bot(token=BOT_TOKEN)

# ================= FLASK (KEEP ALIVE) =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot running"

def run_web():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

threading.Thread(target=run_web, daemon=True).start()

# ================= HELPERS =================
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return set(json.load(f))
    return set()

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(list(data), f)

def extract_otp(message: str):
    m = re.search(r"\b\d{3}[-\s]?\d{3}\b|\b\d{4,6}\b", message)
    return m.group() if m else None

def detect_service(message: str):
    msg = message.lower()
    if "whatsapp" in msg:
        return "WhatsApp 🟢"
    if "telegram" in msg:
        return "Telegram ✈️"
    if "facebook" in msg or "fb" in msg:
        return "Facebook 📘"
    return "Unknown ❓"

def detect_country(phone: str):
    try:
        if not phone.startswith("+"):
            phone = "+" + phone
        parsed = phonenumbers.parse(phone, None)
        country = geocoder.description_for_number(parsed, "en")
        region = phonenumbers.region_code_for_number(parsed)
        if region:
            base = 127462 - ord("A")
            flag = chr(base + ord(region[0])) + chr(base + ord(region[1]))
        else:
            flag = "🌍"
        return flag, country or "Unknown"
    except:
        return "🌍", "Unknown"

def mask_number(num: str):
    return num[:5] + "****" + num[-4:] if len(num) > 8 else num

# ================= API =================
async def fetch_api(session, api):
    async with session.get(
        api["url"],
        params={"token": api["token"], "records": RECORD_LIMIT},
        timeout=20
    ) as r:
        if "application/json" not in r.headers.get("Content-Type", ""):
            return []
        data = await r.json()
        return data.get("data", []) if data.get("status") == "success" else []

# ================= OTP LOOP =================
async def otp_loop():
    sent = load_cache()

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                rows = []
                for api in APIS:
                    for r in await fetch_api(session, api):
                        r["_src"] = api["id"]
                        rows.append(r)

                if rows:
                    latest = max(rows, key=lambda x: x["dt"])
                    uid = f"{latest['dt']}_{latest['num']}"

                    if uid not in sent:
                        msg = latest.get("message", "")
                        otp = extract_otp(msg)
                        if not otp:
                            await asyncio.sleep(FETCH_INTERVAL)
                            continue

                        phone = latest["num"]
                        flag, country = detect_country(phone)
                        service = detect_service(msg)

                        text = (
                            f"{flag} *New {country} OTP!*\n\n"
                            f"🟢 *Service:* {service}\n"
                            f"📞 *Number:* `{mask_number(phone)}`\n"
                            f"🔑 *OTP:* `{otp}`\n"
                            f"🕒 *Time:* `{latest['dt']}`\n\n"
                            f"📩 *Message:*\n{msg}\n\n"
                            f"_Powered by Yuvraj 💗_"
                        )

                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("📋 Copy OTP", callback_data=f"copy:{otp}")]
                        ])

                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=text,
                            parse_mode="Markdown",
                            reply_markup=keyboard
                        )

                        sent.add(uid)
                        save_cache(sent)

            except Exception as e:
                log.error(e)

            await asyncio.sleep(FETCH_INTERVAL)

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot is Alive!\n/admin – Admin Panel"
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("🛠 Admin OK")

async def copy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("OTP copied ✔️")
    otp = q.data.split(":")[1]
    await q.message.reply_text(f"🔑 OTP: `{otp}`", parse_mode="Markdown")

# ================= MAIN =================
def start_background():
    asyncio.run(otp_loop())

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CallbackQueryHandler(copy_handler))

    threading.Thread(target=start_background, daemon=True).start()
    application.run_polling()

if __name__ == "__main__":
    main()
