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

if not BOT_TOKEN or not CHAT_ID or not ADMIN_ID:
    raise RuntimeError("Missing ENV variables")

# ================= CONFIG =================
FETCH_INTERVAL = 10
RECORD_LIMIT = 5
CACHE_FILE = "sent_cache.json"

APIS = {
    "Source 1": {
        "url": "http://147.135.212.197/crapi/had/viewstats",
        "token": API_TOKEN_1
    },
    "Source 2": {
        "url": "http://51.77.216.195/crapi/dgroup/viewstats",
        "token": API_TOKEN_2
    }
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
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return set(json.load(f))
    return set()

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(list(data), f)

def extract_otp(message: str):
    """
    🔥 FINAL OTP LOGIC:
    - Find ALL numbers (4–8 digit)
    - Return the LAST one (actual OTP)
    """
    if not message:
        return None
    matches = re.findall(r"\b\d{4,8}\b", message)
    return matches[-1] if matches else None

def detect_service(msg):
    msg = msg.lower()
    if "whatsapp" in msg:
        return "WhatsApp 🟢"
    if "telegram" in msg:
        return "Telegram ✈️"
    if "facebook" in msg or "fb" in msg:
        return "Facebook 📘"
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
    return num[:5] + "****" + num[-4:] if num and len(num) > 8 else num

# ================= API =================
async def fetch_api(session, api):
    try:
        async with session.get(
            api["url"],
            params={"token": api["token"], "records": RECORD_LIMIT},
            timeout=20
        ) as r:

            # ❌ HTML response → ignore
            if "json" not in r.headers.get("Content-Type", ""):
                log.warning(f"HTML response ignored: {api['url']}")
                return []

            data = await r.json()

            if isinstance(data, dict) and isinstance(data.get("data"), list):
                return data["data"]

            if isinstance(data, list):
                return data

            return []

    except Exception as e:
        log.error(f"API ERROR ({api['url']}): {e}")
        return []

# ================= OTP LOOP =================
async def otp_loop():
    sent = load_cache()

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                for name, api in APIS.items():
                    if not api.get("token"):
                        continue

                    rows = await fetch_api(session, api)
                    if not rows:
                        continue

                    row = rows[-1]  # latest

                    # Support LIST or DICT
                    if isinstance(row, list) and len(row) >= 4:
                        dt, num, service_raw, msg = row[0], row[1], row[2], row[3]
                    elif isinstance(row, dict):
                        dt = row.get("dt")
                        num = row.get("num")
                        msg = row.get("message")
                    else:
                        continue

                    uid = f"{name}_{dt}_{num}"
                    if uid in sent:
                        continue

                    otp = extract_otp(msg)
                    if not otp:
                        continue

                    flag, country = detect_country(num)
                    service = detect_service(msg)

                    text = (
                        f"{flag} *New {country} OTP!*\n\n"
                        f"📡 *Source:* {name}\n"
                        f"🟢 *Service:* {service}\n"
                        f"📞 *Number:* `{mask(num)}`\n"
                        f"🔑 *OTP:* `{otp}`\n"
                        f"🕒 *Time:* `{dt}`\n\n"
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
                log.error(f"OTP LOOP ERROR: {e}")

            await asyncio.sleep(FETCH_INTERVAL)

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot is Alive")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("🛠 Bot running perfectly")

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
