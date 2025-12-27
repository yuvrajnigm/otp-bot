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
PORT = int(os.getenv("PORT", 8080))

# ================= CONFIG =================
FETCH_INTERVAL = 10
RECORD_LIMIT = 5
CACHE_FILE = "sent_cache.json"
SOURCE_FILE = "source_state.json"

APIS = {
    "Source 1": {"url": "http://147.135.212.197/crapi/had/viewstats", "token": API_TOKEN_1},
    "Source 2": {"url": "http://51.77.216.195/crapi/dgroup/viewstats", "token": API_TOKEN_2},
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
    m = re.search(r"\b\d{3}[-\s]?\d{3}\b|\b\d{4,6}\b", msg)
    return m.group() if m else None

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
    return num[:5] + "****" + num[-4:] if len(num) > 8 else num

# ================= API =================
async def fetch_api(session, api):
    async with session.get(
        api["url"],
        params={"token": api["token"], "records": RECORD_LIMIT},
        timeout=20
    ) as r:
        if "json" not in r.headers.get("Content-Type", ""):
            return []
        data = await r.json()
        return data.get("data", []) if data.get("status") == "success" else []

# ================= OTP LOOP =================
async def otp_loop():
    sent = set(load_json(CACHE_FILE, []))
    source_state = load_json(SOURCE_FILE, {"Source 1": True, "Source 2": True})

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                for name, api in APIS.items():
                    if not source_state.get(name, True):
                        continue

                    rows = await fetch_api(session, api)
                    if not rows:
                        continue

                    latest = rows[0]   # 🔥 FIX: no max(dt)
                    uid = f"{latest.get('dt')}_{latest.get('num')}"

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
                log.error(e)

            await asyncio.sleep(FETCH_INTERVAL)

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot is Alive")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    state = load_json(SOURCE_FILE, {"Source 1": True, "Source 2": True})
    await update.message.reply_text(
        "🛠 *Admin Panel*\n\n"
        f"Source 1: {'ON ✅' if state['Source 1'] else 'OFF ❌'}\n"
        f"Source 2: {'ON ✅' if state['Source 2'] else 'OFF ❌'}\n\n"
        "/source1_on  /source1_off\n"
        "/source2_on  /source2_off",
        parse_mode="Markdown"
    )

async def toggle(update, context, src, val):
    if update.effective_user.id != ADMIN_ID:
        return
    state = load_json(SOURCE_FILE, {"Source 1": True, "Source 2": True})
    state[src] = val
    save_json(SOURCE_FILE, state)
    await update.message.reply_text(f"{src} {'ON ✅' if val else 'OFF ❌'}")

async def source1_on(u,c): await toggle(u,c,"Source 1",True)
async def source1_off(u,c): await toggle(u,c,"Source 1",False)
async def source2_on(u,c): await toggle(u,c,"Source 2",True)
async def source2_off(u,c): await toggle(u,c,"Source 2",False)

async def copy_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Copied ✔️")
    otp = q.data.split(":")[1]
    await q.message.reply_text(f"`{otp}`", parse_mode="Markdown")

# ================= MAIN =================
def main():
    app_tg = ApplicationBuilder().token(BOT_TOKEN).build()

    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(CommandHandler("admin", admin))
    app_tg.add_handler(CommandHandler("source1_on", source1_on))
    app_tg.add_handler(CommandHandler("source1_off", source1_off))
    app_tg.add_handler(CommandHandler("source2_on", source2_on))
    app_tg.add_handler(CommandHandler("source2_off", source2_off))
    app_tg.add_handler(CallbackQueryHandler(copy_cb))

    threading.Thread(target=lambda: asyncio.run(otp_loop()), daemon=True).start()
    app_tg.run_polling()

if __name__ == "__main__":
    main()
