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
BOT_TOKEN = "8294446224:AAEWqQTMNzHr88VK8GwcGR_iXBeqNQ7ZIoo"
ADMIN_ID = 8449115253
CHANNEL_ID = -1003406789899

HADI_API = "http://147.135.212.197/crapi/had/viewstats"
HADI_TOKEN = "R1NYQjRSQkF8cm5Dak-QWmFpmHZ0i4ZjQoxzdItykoh4lnVHfXZX"

DGROUP_API = "http://51.77.216.195/crapi/dgroup/viewstats"
DGROUP_TOKEN = "Q1JVQjRSQop9hmhHepdUdUl_hYpblXZ4VHOWQoBTi3pfimxgeG-Q"

RX_API = "http://51.77.216.195/crapi/rx/viewstats"
RX_TOKEN = "QldXSDRSQlaDYWFDSm2DWGSOWHZ8hW9-hlGTe2ptZXxgmIBjaox1"

FETCH_INTERVAL = 10
CACHE_FILE = "sent_cache.json"
START_TIME = time.time()

# ================= STATS =================
TOTAL_OTPS_SENT = 0
LAST_REPORT_DATE = None

# ================= BOT =================
bot = Bot(BOT_TOKEN)
app = Flask(__name__)

# ================= CACHE =================
try:
    sent_cache = set(json.load(open(CACHE_FILE)))
except:
    sent_cache = set()

def save_cache():
    json.dump(list(sent_cache), open(CACHE_FILE, "w"))

# ================= HELPERS =================
def extract_otp(message):
    for pat in [r'\d{3}-\d{3}', r'\d{6}', r'\d{4}']:
        m = re.search(pat, message)
        if m:
            return m.group(0)
    return "N/A"

def get_country_and_flag(number):
    try:
        if not number.startswith("+"):
            number = "+" + number
        parsed = phonenumbers.parse(number)
        country = geocoder.description_for_number(parsed, "en")
        region = phonenumbers.region_code_for_number(parsed)
        if region:
            base = 127462 - ord("A")
            flag = chr(base + ord(region[0])) + chr(base + ord(region[1]))
        else:
            flag = "🌍"
        return country or "Unknown", flag
    except:
        return "Unknown", "🌍"

def mask_number(number):
    if not number.startswith("+"):
        number = "+" + number
    return number[:5] + "*" * (len(number) - 9) + number[-4:]

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

# ================= ALERTS =================
def send_crash_alert(err):
    try:
        bot.send_message(
            ADMIN_ID,
            f"🚨 OTP BOT CRASH ALERT 🚨\n\n"
            f"⏰ {datetime.now()}\n"
            f"❌ Error:\n{err}\n\n"
            f"Bot auto-recovering…"
        )
    except:
        pass

def send_daily_report():
    global TOTAL_OTPS_SENT, LAST_REPORT_DATE
    today = datetime.now().date()
    if LAST_REPORT_DATE == today:
        return
    uptime = int(time.time() - START_TIME)
    h, m = divmod(uptime // 60, 60)
    bot.send_message(
        ADMIN_ID,
        f"📊 DAILY OTP REPORT 📊\n\n"
        f"📅 Date: {today}\n"
        f"📨 OTPs Sent: {TOTAL_OTPS_SENT}\n"
        f"📦 Cache Size: {len(sent_cache)}\n"
        f"⏱ Uptime: {h}h {m}m\n\n"
        f"Powered By 😈 Yuvraj 😈"
    )
    TOTAL_OTPS_SENT = 0
    LAST_REPORT_DATE = today

# ================= OTP WORKER =================
def handle_json_api(api_url, token):
    global TOTAL_OTPS_SENT
    r = requests.get(api_url, params={"token": token, "records": 5}, timeout=15)
    data = r.json().get("data", [])
    for d in data:
        uid = d["dt"] + d["num"]
        if uid in sent_cache:
            continue
        otp = extract_otp(d["message"])
        if otp == "N/A":
            continue
        sent_cache.add(uid)
        save_cache()

        country, flag = get_country_and_flag(d["num"])
        service, emoji = detect_service(d["message"])

        msg = f"""
🔔 {flag} New {country} {service} OTP!

🕰 Time: {d['dt']}
🌍 Country: {country} {flag}
{emoji} Service: {service}
📞 Number: {mask_number(d['num'])}
🔑 OTP: {otp}

📩 Full Message:
{d['message']}

Powered By 😈 Yuvraj 😈
"""
        bot.send_message(CHANNEL_ID, msg)
        TOTAL_OTPS_SENT += 1

def otp_worker():
    while True:
        try:
            handle_json_api(HADI_API, HADI_TOKEN)
            handle_json_api(RX_API, RX_TOKEN)
            send_daily_report()
        except Exception as e:
            print("OTP ERROR:", e)
            send_crash_alert(str(e))
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
    dp.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("🤖 OTP Bot Online ✅")))
    dp.add_handler(CommandHandler("status", lambda u,c: u.message.reply_text(f"Uptime: {int(time.time()-START_TIME)}s")))
    dp.add_handler(CommandHandler("clearcache", lambda u,c: (sent_cache.clear(), save_cache(), u.message.reply_text("Cache cleared"))))

    updater.start_polling()
    updater.idle()
