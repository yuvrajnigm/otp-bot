import asyncio
import aiohttp
import json
import os
import re
import time
from datetime import datetime
import threading

from telegram import Bot
from flask import Flask, jsonify

import phonenumbers
import pycountry
from bs4 import BeautifulSoup

# ================= CONFIG (HARD CODED) =================
BOT_TOKEN = "8294446224:AAEE8Q9Z-B4mIYRnk_59SxsXinXUduOHuF8"
ADMIN_ID = 8449115253
CHANNEL_ID = -1003406789899

HADI_API_TOKEN = "R1NYQjRSQkF8cm5Dak-QWmFpmHZ0i4ZjQoxzdItykoh4lnVHfXZX"
DGROUP_API_TOKEN = "Q1JVQjRSQop9hmhHepdUdUl_hYpblXZ4VHOWQoBTi3pfimxgeG-Q"

FETCH_INTERVAL = 10
CACHE_FILE = "sent_cache.json"

# ======================================================
bot = Bot(BOT_TOKEN)
START_TIME = time.time()
sent_cache = set()

# ================= CACHE =================
if os.path.exists(CACHE_FILE):
    try:
        sent_cache = set(json.load(open(CACHE_FILE)))
    except:
        sent_cache = set()

def save_cache():
    json.dump(list(sent_cache), open(CACHE_FILE, "w"))

# ================= COUNTRY + FLAG =================
def country_flag(number):
    try:
        p = phonenumbers.parse(number, None)
        region = phonenumbers.region_code_for_number(p)
        country = pycountry.countries.get(alpha_2=region)
        flag = "".join(chr(127397 + ord(c)) for c in region)
        return country.name, flag
    except:
        return "Unknown", "🏳️"

# ================= MASK NUMBER =================
def mask_number(num):
    if len(num) < 6:
        return num
    return num[:4] + "****" + num[-4:]

# ================= SERVICE DETECT =================
def detect_service(text):
    t = text.lower()
    if "whatsapp" in t:
        return "WhatsApp", "🟢"
    if "telegram" in t:
        return "Telegram", "🔵"
    if "facebook" in t:
        return "Facebook", "🔵"
    if "google" in t or "gmail" in t:
        return "Google", "🟡"
    return "Unknown", "⚪"

# ================= DGROUP PARSER =================
def parse_dgroup(raw):
    otp = re.search(r"\b\d{4,8}\b", raw)
    num = re.search(r"\+?\d{8,15}", raw)
    service, emoji = detect_service(raw)
    return (
        otp.group() if otp else None,
        num.group() if num else None,
        service,
        emoji
    )

# ================= FLASK KEEP ALIVE =================
app = Flask(__name__)

@app.route("/")
def home():
    return "OTP BOT IS ALIVE"

@app.route("/health")
def health():
    return jsonify({"status": "ok", "cache": len(sent_cache)})

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# ================= COMMAND LISTENER =================
async def command_listener():
    offset = None
    while True:
        updates = bot.get_updates(offset=offset, timeout=30)
        for u in updates:
            offset = u.update_id + 1

            if not u.message or not u.message.text:
                continue

            chat_id = u.message.chat.id
            text = u.message.text.strip()

            if text == "/start":
                await bot.send_message(chat_id, "🤖 OTP Bot is running ✅")
                continue

            if chat_id != ADMIN_ID:
                continue

            if text == "/status":
                uptime = int(time.time() - START_TIME)
                h, m = divmod(uptime // 60, 60)
                await bot.send_message(
                    ADMIN_ID,
                    f"✅ OTP Bot Online\n"
                    f"⏱ Uptime: {h}h {m}m\n"
                    f"📦 Cached OTPs: {len(sent_cache)}"
                )

            if text == "/clearcache":
                sent_cache.clear()
                save_cache()
                await bot.send_message(ADMIN_ID, "🧹 Cache cleared")

        await asyncio.sleep(1)

# ================= OTP WORKER =================
async def otp_worker():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # ---------- HADI ----------
                url = f"http://147.135.212.197/crapi/had/viewstats?token={HADI_API_TOKEN}&records=5"
                async with session.get(url, timeout=15) as r:
                    if "json" in r.headers.get("content-type", ""):
                        data = await r.json()
                        for d in data.get("data", []):
                            uid = d["dt"] + d["num"]
                            if uid in sent_cache:
                                continue
                            sent_cache.add(uid)
                            save_cache()

                            otp = re.search(r"\d{4,8}", d["message"])
                            if not otp:
                                continue

                            number = "+" + d["num"]
                            country, flag = country_flag(number)
                            service, emoji = detect_service(d["message"])

                            await bot.send_message(
                                CHANNEL_ID,
                                f"🔔 {flag} New {country} {service} OTP!\n"
                                f"🕰 Time: {d['dt']}\n"
                                f"📞 Number: {mask_number(number)}\n"
                                f"🔑 OTP: {otp.group()}\n"
                                f"Powered By 😈 Yuvraj 😈"
                            )

                # ---------- DGROUP ----------
                durl = f"http://51.77.216.195/crapi/dgroup/viewstats?token={DGROUP_API_TOKEN}&records=1"
                async with session.get(durl, timeout=15) as r:
                    raw = await r.text()
                    otp, num, service, emoji = parse_dgroup(raw)
                    if otp and num:
                        uid = num + otp
                        if uid not in sent_cache:
                            sent_cache.add(uid)
                            save_cache()

                            country, flag = country_flag(num)

                            await bot.send_message(
                                CHANNEL_ID,
                                f"🔔 {flag} New {country} {service} OTP!\n"
                                f"🕰 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                f"📞 Number: {mask_number(num)}\n"
                                f"🔑 OTP: {otp}\n"
                                f"Powered By 😈 Yuvraj 😈"
                            )

            except Exception as e:
                print("OTP ERROR:", e)

            await asyncio.sleep(FETCH_INTERVAL)

# ================= MAIN =================
async def main():
    await asyncio.gather(
        command_listener(),
        otp_worker()
    )

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
