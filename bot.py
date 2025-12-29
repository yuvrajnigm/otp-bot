import os, re, json, asyncio, aiohttp, logging, threading
from flask import Flask
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import phonenumbers
from phonenumbers import geocoder

# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))
API_TOKEN_1 = os.getenv("API_TOKEN_1")
API_TOKEN_2 = os.getenv("API_TOKEN_2")
API_TOKEN_3 = os.getenv("API_TOKEN_3")
PORT = int(os.getenv("PORT", 8080))

if not all([BOT_TOKEN, CHAT_ID, ADMIN_ID]):
    raise RuntimeError("Missing ENV variables")

# ================= CONFIG =================
FETCH_INTERVAL = 10
RECORD_LIMIT = 5
CACHE_FILE = "sent_cache.json"
SOURCE_FILE = "source_state.json"

APIS = {
    "Source 1": {"url": "http://147.135.212.197/crapi/had/viewstats", "token": API_TOKEN_1},
    "Source 2": {"url": "http://51.77.216.195/crapi/dgroup/viewstats", "token": API_TOKEN_2},
    "Source 3": {"url": "http://147.135.212.197/crapi/st/viewstats", "token": API_TOKEN_3},
}

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("OTP-BOT")

bot = Bot(token=BOT_TOKEN)

# ================= FLASK =================
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot running"

threading.Thread(
    target=lambda: app.run(host="0.0.0.0", port=PORT),
    daemon=True
).start()

# ================= HELPERS =================
def load_json(file, default):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def extract_otp(msg):
    if not msg:
        return None
    patterns = [
        r"\b\d{3}[-\s]\d{3}\b",
        r"\b\d{6}\b",
        r"\b\d{5}\b",
        r"\b\d{4}\b",
        r"(?:otp|code)[:\s]*([0-9\- ]{4,8})",
        r"#\d{4,6}"
    ]
    for p in patterns:
        m = re.search(p, msg, re.IGNORECASE)
        if m:
            return m.group(1) if m.groups() else m.group()
    return None

def detect_service(msg):
    m = msg.lower()
    if "whatsapp" in m: return "WhatsApp 🟢"
    if "telegram" in m: return "Telegram ✈️"
    if "facebook" in m or "fb" in m: return "Facebook 📘"
    return "Unknown ❓"

def detect_country(phone):
    try:
        if not phone.startswith("+"):
            phone = "+" + phone
        p = phonenumbers.parse(phone, None)
        country = geocoder.description_for_number(p, "en")
        region = phonenumbers.region_code_for_number(p)
        if region:
            base = 127462 - ord("A")
            flag = chr(base + ord(region[0])) + chr(base + ord(region[1]))
        else:
            flag = "🌍"
        return flag, country or "Unknown"
    except:
        return "🌍", "Unknown"

def mask(num):
    if not num:
        return "Unknown"
    return num[:5] + "****" + num[-4:] if len(num) > 8 else num

# ================= API (FIXED) =================
async def fetch_api(session, api):
    try:
        async with session.get(
            api["url"],
            params={"token": api["token"], "records": RECORD_LIMIT},
            timeout=20
        ) as r:
            if "json" not in r.headers.get("Content-Type", ""):
                return []

            data = await r.json()

            # CASE 1: API returns list
            if isinstance(data, list):
                return data

            # CASE 2: API returns dict
            if isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list):
                    return data["data"]

            return []
    except Exception as e:
        log.error(f"API error: {e}")
        return []

# ================= OTP LOOP =================
async def otp_loop():
    sent = set(load_json(CACHE_FILE, []))
    state = load_json(
        SOURCE_FILE,
        {"Source 1": True, "Source 2": True, "Source 3": True}
    )

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                for name, api in APIS.items():
                    if not state.get(name, True):
                        continue
                    if not api.get("token"):
                        continue

                    rows = await fetch_api(session, api)
                    if not rows:
                        continue

                    latest = rows[-1]  # safest
                    uid = f"{name}_{latest.get('dt')}_{latest.get('num')}"
                    if uid in sent:
                        continue

                    msg = latest.get("message", "")
                    otp = extract_otp(msg)
                    if not otp:
                        continue

                    phone = latest.get("num", "")
                    flag, country = detect_country(phone)
                    service = detect_service(msg)

                    text = (
                        f"{flag} *New {country} OTP!*\n\n"
                        f"📡 *Source:* {name}\n"
                        f"🟢 *Service:* {service}\n"
                        f"📞 *Number:* `{mask(phone)}`\n"
                        f"🔑 *OTP:* `{otp}`\n"
                        f"🕒 *Time:* `{latest.get('dt')}`\n\n"
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
                    save_json(CACHE_FILE, list(sent))

            except Exception as e:
                log.error(f"OTP LOOP ERROR: {e}")

            await asyncio.sleep(FETCH_INTERVAL)

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot is Alive")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    state = load_json(
        SOURCE_FILE,
        {"Source 1": True, "Source 2": True, "Source 3": True}
    )

    await update.message.reply_text(
        "🛠 *Admin Panel*\n\n"
        f"Source 1: {'ON ✅' if state.get('Source 1') else 'OFF ❌'}\n"
        f"Source 2: {'ON ✅' if state.get('Source 2') else 'OFF ❌'}\n"
        f"Source 3: {'ON ✅' if state.get('Source 3') else 'OFF ❌'}",
        parse_mode="Markdown"
    )

async def copy_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Copied ✔️")
    await q.message.reply_text(f"`{q.data.split(':')[1]}`", parse_mode="Markdown")

# ================= MAIN =================
def main():
    app_tg = ApplicationBuilder().token(BOT_TOKEN).build()

    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(CommandHandler("admin", admin))
    app_tg.add_handler(CallbackQueryHandler(copy_cb))

    threading.Thread(target=lambda: asyncio.run(otp_loop()), daemon=True).start()
    app_tg.run_polling()

if __name__ == "__main__":
    main()

