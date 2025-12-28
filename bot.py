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
PORT = int(os.getenv("PORT", 8080))

if not BOT_TOKEN or not CHAT_ID or not ADMIN_ID:
    raise RuntimeError("Missing ENV variables")

# ================= FILES =================
CACHE_FILE = "sent_cache.json"
SOURCE_FILE = "sources.json"

# ================= CONFIG =================
FETCH_INTERVAL = 10
RECORD_LIMIT = 5

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

# ================= UTIL =================
def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def load_json(file, default):
    if not os.path.exists(file):
        return default

    with open(file) as f:
        data = json.load(f)

    # 🔥 AUTO-FIX old LIST format
    if isinstance(data, list):
        fixed = {}
        for i, item in enumerate(data, start=1):
            fixed[f"Source{i}"] = {
                "url": item.get("url"),
                "token": item.get("token"),
                "enabled": True
            }
        save_json(file, fixed)
        return fixed

    return data

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
async def fetch_api(session, src):
    async with session.get(
        src["url"],
        params={"token": src["token"], "records": RECORD_LIMIT},
        timeout=20
    ) as r:
        if "json" not in r.headers.get("Content-Type", ""):
            return []
        data = await r.json()
        return data.get("data", []) if data.get("status") == "success" else []

# ================= OTP LOOP =================
async def otp_loop():
    sent = set(load_json(CACHE_FILE, []))

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                sources = load_json(SOURCE_FILE, {})

                for name, src in sources.items():
                    if not src.get("enabled", True):
                        continue

                    rows = await fetch_api(session, src)
                    if not rows:
                        continue

                    latest = rows[0]
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
                log.error(e)

            await asyncio.sleep(FETCH_INTERVAL)

# ================= COMMANDS =================
def admin_only(update):
    return update.effective_user.id == ADMIN_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot is Alive")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update): return
    sources = load_json(SOURCE_FILE, {})
    msg = "🛠 *Admin Panel*\n\n"
    if not sources:
        msg += "No sources added\n"
    else:
        for s, v in sources.items():
            msg += f"{s}: {'ON ✅' if v.get('enabled',True) else 'OFF ❌'}\n"
    msg += "\n/addsource\n/removesource\n/listsources"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def addsource(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update): return
    if len(context.args) < 3:
        await update.message.reply_text("Usage:\n/addsource Name URL TOKEN")
        return

    name, url, token = context.args[0], context.args[1], context.args[2]
    sources = load_json(SOURCE_FILE, {})
    sources[name] = {"url": url, "token": token, "enabled": True}
    save_json(SOURCE_FILE, sources)
    await update.message.reply_text(f"✅ Source `{name}` added", parse_mode="Markdown")

async def removesource(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update): return
    if not context.args:
        await update.message.reply_text("Usage: /removesource Name")
        return
    name = context.args[0]
    sources = load_json(SOURCE_FILE, {})
    if name in sources:
        del sources[name]
        save_json(SOURCE_FILE, sources)
        await update.message.reply_text(f"❌ Source `{name}` removed", parse_mode="Markdown")
    else:
        await update.message.reply_text("Source not found")

async def listsources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update): return
    sources = load_json(SOURCE_FILE, {})
    if not sources:
        await update.message.reply_text("No sources")
        return
    msg = "📡 *Sources*\n\n"
    for s, v in sources.items():
        msg += f"{s} → {'ON' if v.get('enabled') else 'OFF'}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

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
    app_tg.add_handler(CommandHandler("addsource", addsource))
    app_tg.add_handler(CommandHandler("removesource", removesource))
    app_tg.add_handler(CommandHandler("listsources", listsources))
    app_tg.add_handler(CallbackQueryHandler(copy_cb))

    threading.Thread(target=lambda: asyncio.run(otp_loop()), daemon=True).start()
    app_tg.run_polling()

if __name__ == "__main__":
    main()

