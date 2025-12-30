import asyncio
import re
import requests
import phonenumbers
from phonenumbers import geocoder
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= TELEGRAM CONFIG =================
BOT_TOKEN = "8321758039:AAGHe2vzsEM3G4VfeZtGbOQMq09Qh6vLuMg"
GROUP_ID = -1003406789899
ADMIN_IDS = [8221767181, 8449115253]
NUMBER_CHANNEL_LINK = "https://t.me/YUVRAJNUMBERS"
# ==================================================

# ================= PANELS CONFIG ==================
PANELS = {
    "iVASMS": {
        "login": "https://www.ivasms.com/login",
        "sms": "https://www.ivasms.com/portal/live/my_sms",
        "user": "tgonly712@gmail.com",
        "pass": "Yuvraj2008",
        "session": requests.Session(),
    },
    "PANEL185": {
        "login": "http://185.2.83.39/ints/login",
        "sms": "http://185.2.83.39/ints/agent/SMSCDRStats",
        "user": "Yuvraj2008",
        "pass": "Yuvraj2008",
        "session": requests.Session(),
    },
}
# ==================================================

HEADERS = {"User-Agent": "Mozilla/5.0"}
CHECK_INTERVAL = 10

sent_cache = set()
stats = {"today": 0, "total": 0, "errors": 0}

# ================= HELPERS =================
def extract_otp(text):
    m = re.search(r"\b\d{4,8}\b", text)
    return m.group() if m else None

def extract_number(text):
    m = re.search(r"\+?\d{8,15}", text)
    return m.group() if m else "N/A"

def get_country_from_number(number):
    try:
        if not number.startswith("+"):
            number = "+" + number

        parsed = phonenumbers.parse(number, None)
        country = geocoder.description_for_number(parsed, "en")
        region = phonenumbers.region_code_for_number(parsed)

        if region:
            flag = "".join(chr(127397 + ord(c)) for c in region)
        else:
            flag = "🏳️"

        return country if country else "Unknown", flag

    except Exception:
        return "Unknown", "🏳️"

# ================= PANEL FETCH =================
def fetch_html(cfg):
    s = cfg["session"]
    s.post(
        cfg["login"],
        data={
            "email": cfg["user"],
            "username": cfg["user"],
            "password": cfg["pass"],
        },
        headers=HEADERS,
        timeout=20,
    )
    r = s.get(cfg["sms"], headers=HEADERS, timeout=20)
    return r.text

def parse_html(html):
    soup = BeautifulSoup(html, "lxml")
    for tr in soup.find_all("tr"):
        raw = tr.get_text(" ").strip()
        otp = extract_otp(raw)
        if otp:
            number = extract_number(raw)
            yield otp, number, raw

# ================= SEND OTP =================
async def send_otp(app, panel, otp, number, raw):
    country, flag = get_country_from_number(number)

    text = (
        "🔐 <b>OTP RECEIVED</b>\n\n"
        f"🏷 <b>Panel:</b> {panel}\n"
        f"🌍 <b>Country:</b> {flag} {country}\n"
        f"📞 <b>Number:</b> {number}\n"
        f"🔢 <b>OTP:</b> <code>{otp}</code>\n"
        f"🕒 <b>Time:</b> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
    )

    keyboard = [[InlineKeyboardButton("📢 Number Channel", url=NUMBER_CHANNEL_LINK)]]

    await app.bot.send_message(
        chat_id=GROUP_ID,
        text=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ================= LOOP =================
async def otp_loop(app):
    while True:
        try:
            for name, cfg in PANELS.items():
                html = fetch_html(cfg)
                for otp, number, raw in parse_html(html):
                    key = f"{name}-{otp}-{number}"
                    if key not in sent_cache:
                        await send_otp(app, name, otp, number, raw)
                        sent_cache.add(key)
                        stats["today"] += 1
                        stats["total"] += 1

            await asyncio.sleep(CHECK_INTERVAL)

        except Exception:
            stats["errors"] += 1
            await asyncio.sleep(10)

# ================= COMMANDS =================
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Status: ON\nToday: {stats['today']}\nTotal: {stats['total']}\nErrors: {stats['errors']}"
    )

# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("status", cmd_status))

    asyncio.create_task(otp_loop(app))

    print("✅ OTP BOT STARTED (AUTO COUNTRY DETECT)")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
