# ================= IMPORTS =================
import os, re, json, time, threading, requests
from datetime import datetime
from flask import Flask
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext

import phonenumbers
from phonenumbers import geocoder

# ================= CONFIG =================
BOT_TOKEN = "8294446224:AAEE8Q9Z-B4mIYRnk_59SxsXinXUduOHuF8"
ADMIN_ID = 8449115253
CHANNEL_ID = -1003406789899

HADI_API = "http://147.135.212.197/crapi/had/viewstats"
HADI_TOKEN = "R1NYQjRSQkF8cm5Dak-QWmFpmHZ0i4ZjQoxzdItykoh4lnVHfXZX"

DGROUP_API = "http://51.77.216.195/crapi/dgroup/viewstats"
DGROUP_TOKEN = "Q1JVQjRSQop9hmhHepdUdUl_hYpblXZ4VHOWQoBTi3pfimxgeG-Q"

FETCH_INTERVAL = 10
CACHE_FILE = "sent_cache.json"

START_TIME = time.time()

# ================= COUNTRY FLAGS (FULL MAP) =================
COUNTRY_FLAGS = {
    "Afghanistan": "🇦🇫", "Albania": "🇦🇱", "Algeria": "🇩🇿", "Argentina": "🇦🇷",
    "Australia": "🇦🇺", "Austria": "🇦🇹", "Bangladesh": "🇧🇩", "Belgium": "🇧🇪",
    "Brazil": "🇧🇷", "Canada": "🇨🇦", "China": "🇨🇳", "Colombia": "🇨🇴",
    "Egypt": "🇪🇬", "France": "🇫🇷", "Germany": "🇩🇪", "India": "🇮🇳",
    "Indonesia": "🇮🇩", "Iran": "🇮🇷", "Iraq": "🇮🇶", "Italy": "🇮🇹",
    "Japan": "🇯🇵", "Kenya": "🇰🇪", "Kyrgyzstan": "🇰🇬", "Malaysia": "🇲🇾",
    "Mexico": "🇲🇽", "Nepal": "🇳🇵", "Netherlands": "🇳🇱", "Nigeria": "🇳🇬",
    "Pakistan": "🇵🇰", "Philippines": "🇵🇭", "Qatar": "🇶🇦", "Russia": "🇷🇺",
    "Saudi Arabia": "🇸🇦", "Singapore": "🇸🇬", "South Africa": "🇿🇦",
    "South Korea": "🇰🇷", "Spain": "🇪🇸", "Sri Lanka": "🇱🇰",
    "Thailand": "🇹🇭", "Turkey": "🇹🇷", "United Arab Emirates": "🇦🇪",
    "United Kingdom": "🇬🇧", "United States": "🇺🇸", "Uzbekistan": "🇺🇿",
    "Vietnam": "🇻🇳", "Yemen": "🇾🇪", "Zimbabwe": "🇿🇼",
    "Unknown Country": "🏴‍☠️"
}

# ================= SERVICE KEYWORDS =================
SERVICE_KEYWORDS = {
    "WhatsApp": ["whatsapp"],
    "Telegram": ["telegram"],
    "Facebook": ["facebook"],
    "Google": ["google", "gmail"],
    "Instagram": ["instagram"],
    "Amazon": ["amazon"],
    "Netflix": ["netflix"],
    "LinkedIn": ["linkedin"],
    "Microsoft": ["microsoft", "outlook", "live.com"],
    "Apple": ["apple", "icloud"],
    "Twitter": ["twitter", "x"],
    "Snapchat": ["snapchat"],
    "TikTok": ["tiktok"],
    "Discord": ["discord"],
    "Signal": ["signal"],
    "Viber": ["viber"],
    "IMO": ["imo"],
    "PayPal": ["paypal"],
    "Binance": ["binance"],
    "Uber": ["uber"],
    "Yahoo": ["yahoo"],
    "Unknown": []
}

# ================= SERVICE EMOJIS =================
SERVICE_EMOJIS = {
    "WhatsApp": "🟢", "Telegram": "📩", "Facebook": "📘", "Instagram": "📸",
    "Google": "✉️", "Amazon": "🛒", "Netflix": "🎬", "LinkedIn": "💼",
    "Microsoft": "🪟", "Apple": "🍏", "Twitter": "🐦", "Snapchat": "👻",
    "TikTok": "🎵", "Discord": "🗨️", "Signal": "🔐", "Viber": "📞",
    "IMO": "💬", "PayPal": "💰", "Binance": "🪙", "Uber": "🚗",
    "Yahoo": "🟣", "Unknown": "❓"
}

# ================= INIT =================
bot = Bot(BOT_TOKEN)
app = Flask(__name__)

# ================= CACHE =================
if os.path.exists(CACHE_FILE):
    sent_cache = set(json.load(open(CACHE_FILE)))
else:
    sent_cache = set()

def save_cache():
    json.dump(list(sent_cache), open(CACHE_FILE, "w"))

# ================= HELPERS =================
def get_country_and_flag(number):
    try:
        if not number.startswith("+"):
            number = "+" + number
        parsed = phonenumbers.parse(number, None)
        country = geocoder.description_for_number(parsed, "en")
        flag = COUNTRY_FLAGS.get(country, COUNTRY_FLAGS["Unknown Country"])
        return country, flag
    except:
        return "Unknown Country", COUNTRY_FLAGS["Unknown Country"]

def detect_service(text):
    t = text.lower()
    for service, keys in SERVICE_KEYWORDS.items():
        for k in keys:
            if k in t:
                return service
    return "Unknown"

def mask_number(num):
    return num[:4] + "****" + num[-4:]

# ================= COMMANDS =================
def start_cmd(update: Update, context: CallbackContext):
    update.message.reply_text("🤖 OTP Bot is ONLINE ✅")

def status_cmd(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    up = int(time.time() - START_TIME)
    h, m = divmod(up // 60, 60)
    update.message.reply_text(
        f"✅ Bot Running\n⏱ Uptime: {h}h {m}m\n📦 Cached OTPs: {len(sent_cache)}"
    )

def clearcache_cmd(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    sent_cache.clear()
    save_cache()
    update.message.reply_text("🧹 Cache Cleared")

# ================= OTP WORKER =================
def otp_worker():
    while True:
        try:
            r = requests.get(HADI_API, params={"token": HADI_TOKEN, "records": 5}, timeout=15)
            data = r.json().get("data", [])

            for d in data:
                uid = d["dt"] + d["num"]
                if uid in sent_cache:
                    continue

                otp_match = re.search(r"\d{4,8}", d["message"])
                if not otp_match:
                    continue

                sent_cache.add(uid)
                save_cache()

                number = d["num"]
                country, flag = get_country_and_flag(number)
                service = detect_service(d["message"])
                emoji = SERVICE_EMOJIS.get(service, "❓")

                msg = f"""
🔔 {flag} New {country} {service} OTP!

🕰 Time: {d['dt']}
🌍 Country: {country} {flag}
{emoji} Service: {service}
📞 Number: +{mask_number(number)}
🔑 OTP: {otp_match.group()}

📩 Full Message:
{d['message']}

Powered By 😈 Yuvraj 😈
"""
                bot.send_message(CHANNEL_ID, msg)

        except Exception as e:
            print("OTP ERROR:", e)

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
    updater.start_polling()
    updater.idle()
