# ================= IMPORTS =================
import re
import json
import time
import threading
import requests
import os
from datetime import datetime

from flask import Flask
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext

import phonenumbers
from phonenumbers import geocoder

# ================= CONFIG =================
BOT_TOKEN = "8294446224:AAGqnRG7M6mtjumsWjaG3ZYqSMW7cgfgdbI"
ADMIN_ID = 8449115253
DEFAULT_CHANNEL = -1003406789899

HADI_API = "http://147.135.212.197/crapi/had/viewstats"
HADI_TOKEN = "R1NYQjRSQkF8cm5Dak-QWmFpmHZ0i4ZjQoxzdItykoh4lnVHfXZX"

DGROUP_API = "http://51.77.216.195/crapi/dgroup/viewstats"
DGROUP_TOKEN = "Q1JVQjRSQop9hmhHepdUdUl_hYpblXZ4VHOWQoBTi3pfimxgeG-Q"

HADI_INTERVAL = 10
DGROUP_INTERVAL = 30   # ⬅️ VERY IMPORTANT (slow)

CACHE_FILE = "sent_cache.json"
CHAT_FILE = "chats.json"

START_TIME = time.time()

# ================= GLOBAL =================
bot = Bot(BOT_TOKEN)

# ================= FLASK (PORT) =================
app = Flask(__name__)

@app.route("/")
def home():
    return "BOT ALIVE"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run("0.0.0.0", port)

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
    for p in [r'\d{6}', r'\d{4}', r'\d{3}-\d{3}']:
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
    return "Service", "🔐"

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

# ================= COMMANDS =================
def start_cmd(update: Update, ctx: CallbackContext):
    update.message.reply_text("🤖 OTP Bot ONLINE ✅")

# ================= HADI WORKER =================
def hadi_worker():
    while True:
        try:
            r = requests.get(HADI_API, params={"token": HADI_TOKEN, "records": 5}, timeout=15)
            if not r.text.strip().startswith("{"):
                time.sleep(HADI_INTERVAL)
                continue

            for d in r.json().get("data", []):
                uid = "H" + d["dt"] + d["num"]
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
                    f"⏰ {d['dt']}\n"
                    f"🌍 {country} {flag}\n"
                    f"{semoji} {service}\n"
                    f"📞 {mask_number(d['num'])}\n"
                    f"🔑 OTP: {otp}\n\n"
                    f"{d['message']}"
                )

        except:
            pass

        time.sleep(HADI_INTERVAL)

# ================= DGROUP WORKER (SAFE) =================
def dgroup_worker():
    while True:
        try:
            r = requests.get(
                DGROUP_API,
                params={"token": DGROUP_TOKEN, "records": 5},
                timeout=15
            )

            # ⛔ RATE LIMIT / NON JSON
            if not r.text.strip().startswith("{"):
                time.sleep(6)   # ⬅️ backoff
                continue

            for d in r.json().get("data", []):
                uid = "D" + d["dt"] + d["num"]
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
                    f"⏰ {d['dt']}\n"
                    f"🌍 {country} {flag}\n"
                    f"{semoji} {service}\n"
                    f"📞 {mask_number(d['num'])}\n"
                    f"🔑 OTP: {otp}\n\n"
                    f"{d['message']}"
                )

        except:
            pass

        time.sleep(DGROUP_INTERVAL)

# ================= MAIN =================
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=hadi_worker, daemon=True).start()
    threading.Thread(target=dgroup_worker, daemon=True).start()

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start_cmd))
    updater.start_polling()
    updater.idle()
