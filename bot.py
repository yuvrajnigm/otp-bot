# ================= IMPORTS =================
import re
import json
import time
import threading
import requests
from datetime import datetime

from flask import Flask
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext

import phonenumbers
from phonenumbers import geocoder

# ================= CONFIG =================
BOT_TOKEN = "8294446224:AAHutl8UvkTDnXSVyzSWXWzcZamM61T3yPM"
ADMIN_ID = 8449115253
DEFAULT_CHANNEL = -1003406789899

HADI_API = "http://147.135.212.197/crapi/had/viewstats"
HADI_TOKEN = "R1NYQjRSQkF8cm5Dak-QWmFpmHZ0i4ZjQoxzdItykoh4lnVHfXZX"

DGROUP_API = "http://51.77.216.195/crapi/dgroup/viewstats"
DGROUP_TOKEN = "Q1JVQjRSQop9hmhHepdUdUl_hYpblXZ4VHOWQoBTi3pfimxgeG-Q"

FETCH_INTERVAL = 10
CACHE_FILE = "sent_cache.json"
CHAT_FILE = "chats.json"

START_TIME = time.time()

# ================= GLOBAL =================
bot = Bot(BOT_TOKEN)
app = Flask(__name__)

TOTAL_OTPS_SENT = 0
LAST_REPORT_DATE = None

# ================= CACHE =================
try:
    sent_cache = set(json.load(open(CACHE_FILE)))
except:
    sent_cache = set()

def save_cache():
    json.dump(list(sent_cache), open(CACHE_FILE, "w"))

# ================= CHAT LIST =================
try:
    CHAT_IDS = set(json.load(open(CHAT_FILE)))
except:
    CHAT_IDS = {DEFAULT_CHANNEL}

def save_chats():
    json.dump(list(CHAT_IDS), open(CHAT_FILE, "w"))

# ================= HELPERS =================
def extract_otp(text):
    for p in [r'\d{3}-\d{3}', r'\d{6}', r'\d{4}']:
        m = re.search(p, text)
        if m:
            return m.group()
    return None

def detect_service(text):
    t = text.lower()
    if "whatsapp" in t:
        return "WhatsApp", "🟢"
    if "telegram" in t:
        return "Telegram", "📩"
    if "facebook" in t:
        return "Facebook", "📘"
    if "google" in t or "gmail" in t:
        return "Google", "✉️"
    return "Unknown", "❓"

def get_country_flag(number):
    try:
        if not number.startswith("+"):
            number = "+" + number
        p = phonenumbers.parse(number)
        country = geocoder.description_for_number(p, "en")
        region = phonenumbers.region_code_for_number(p)
        if region:
            base = 127462 - ord("A")
            flag = chr(base + ord(region[0])) + chr(base + ord(region[1]))
        else:
            flag = "🌍"
        return country or "Unknown", flag
    except:
        return "Unknown", "🌍"

def mask_number(num):
    num = num.replace("+", "")
    return "+" + num[:3] + "***" + num[-4:]

def send_all(text):
    for cid in CHAT_IDS:
        try:
            bot.send_message(cid, text)
        except:
            pass

# ================= ALERTS =================
def crash_alert(err):
    bot.send_message(
        ADMIN_ID,
        f"🚨 OTP BOT CRASH ALERT 🚨\n\n"
        f"⏰ {datetime.now()}\n"
        f"❌ Error:\n{err}\n\n"
        f"🛠 Auto-recovering…"
    )

def daily_report():
    global TOTAL_OTPS_SENT, LAST_REPORT_DATE
    today = datetime.now().date()
    if LAST_REPORT_DATE == today:
        return

    uptime = int(time.time() - START_TIME)
    h, m = divmod(uptime // 60, 60)

    bot.send_message(
        ADMIN_ID,
        f"📊 DAILY REPORT\n\n"
        f"📨 OTPs Sent: {TOTAL_OTPS_SENT}\n"
        f"📦 Cache: {len(sent_cache)}\n"
        f"⏱ Uptime: {h}h {m}m\n\n"
        f"Powered By 😈 Yuvraj 😈"
    )
    TOTAL_OTPS_SENT = 0
    LAST_REPORT_DATE = today

# ================= COMMANDS =================
def start_cmd(update: Update, ctx: CallbackContext):
    if update.effective_user.id == ADMIN_ID:
        update.message.reply_text(
            "👋 Welcome Admin!\n\n"
            "/status\n/apistatus\n/clearcache\n"
            "/add_chat <id>\n/remove_chat <id>\n/list_chats"
        )
    else:
        update.message.reply_text("🤖 OTP Bot is ONLINE ✅")

def status_cmd(update: Update, ctx: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    up = int(time.time() - START_TIME)
    h, m = divmod(up // 60, 60)
    update.message.reply_text(
        f"✅ Bot Online\n⏱ {h}h {m}m\n📦 Cache: {len(sent_cache)}"
    )

def clearcache_cmd(update: Update, ctx: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    sent_cache.clear()
    save_cache()
    update.message.reply_text("🧹 Cache cleared")

def apistatus_cmd(update: Update, ctx: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = "📡 API STATUS\n\n"
    try:
        requests.get(HADI_API, params={"token": HADI_TOKEN}, timeout=5)
        msg += "🟢 HADI API: ONLINE\n"
    except:
        msg += "🔴 HADI API: OFFLINE\n"
    try:
        requests.get(DGROUP_API, params={"token": DGROUP_TOKEN}, timeout=5)
        msg += "🟢 DGROUP API: ONLINE\n"
    except:
        msg += "🔴 DGROUP API: OFFLINE\n"
    update.message.reply_text(msg)

def add_chat_cmd(update, ctx):
    if update.effective_user.id != ADMIN_ID:
        return
    cid = int(ctx.args[0])
    CHAT_IDS.add(cid)
    save_chats()
    update.message.reply_text(f"✅ Added {cid}")

def remove_chat_cmd(update, ctx):
    if update.effective_user.id != ADMIN_ID:
        return
    cid = int(ctx.args[0])
    CHAT_IDS.discard(cid)
    save_chats()
    update.message.reply_text(f"🗑 Removed {cid}")

def list_chats_cmd(update, ctx):
    if update.effective_user.id != ADMIN_ID:
        return
    update.message.reply_text("📋 Chats:\n" + "\n".join(map(str, CHAT_IDS)))

# ================= OTP WORKER =================
def otp_worker():
    global TOTAL_OTPS_SENT
    while True:
        try:
            # HADI
            r = requests.get(HADI_API, params={"token": HADI_TOKEN, "records": 5}, timeout=15)
            for d in r.json().get("data", []):
                uid = d["dt"] + d["num"]
                if uid in sent_cache:
                    continue
                otp = extract_otp(d["message"])
                if not otp:
                    continue
                sent_cache.add(uid)
                save_cache()

                country, flag = get_country_flag(d["num"])
                service, semoji = detect_service(d["message"])

                send_all(
                    f"⏰ Time: {d['dt']}\n"
                    f"🌍 Country: {country} {flag}\n"
                    f"{semoji} Service: {service}\n"
                    f"📞 Number: {mask_number(d['num'])}\n"
                    f"🔑 OTP: {otp}\n\n"
                    f"📩 Full Message:\n{d['message']}\n\n"
                    f"Powered By 😈 Yuvraj 😈"
                )
                TOTAL_OTPS_SENT += 1

            daily_report()

        except Exception as e:
            crash_alert(str(e))

        time.sleep(FETCH_INTERVAL)

# ================= FLASK =================
@app.route("/")
def home():
    return "BOT ALIVE"

def run_flask():
    app.run("0.0.0.0", 10000)

# ================= MAIN =================
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=otp_worker, daemon=True).start()

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start_cmd))
    dp.add_handler(CommandHandler("status", status_cmd))
    dp.add_handler(CommandHandler("clearcache", clearcache_cmd))
    dp.add_handler(CommandHandler("apistatus", apistatus_cmd))
    dp.add_handler(CommandHandler("add_chat", add_chat_cmd))
    dp.add_handler(CommandHandler("remove_chat", remove_chat_cmd))
    dp.add_handler(CommandHandler("list_chats", list_chats_cmd))

    updater.start_polling()
    updater.idle()
