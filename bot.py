import asyncio
import aiohttp
import re
import hashlib
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
# Telegram Configuration
BOT_TOKEN = '8294446224:AAFi5nLurx1Mu7awo8kj3cSzmtB1XS0XBT0' 
ADMIN_ID = 8449115253
CHANNEL_ID = -1003406789899
OWNER_LINK = "https://t.me/Illuminate786"
CHANNEL_LINK = "https://t.me/YUVRAJNUMBERS"

# [span_3](start_span)[span_4](start_span)[span_5](start_span)API Details from your PDFs[span_3](end_span)[span_4](end_span)[span_5](end_span)
SITES = {
    "Hadi": {
        "url": "http://147.135.212.197/crapi/had/viewstats", 
        "token": "R1NYQjRSQkF8cm5Dak-QWmFpmHZ0i4ZjQoxzdItykoh4lnVHfXZX" 
    },
    "D-Group": {
        "url": "http://51.77.216.195/crapi/dgroup/viewstats", 
        "token": "Q1JVQjRSQlVmU5B8Z5JzZniVk1dEgGhKVVNYalRxc2Bff2CEgoZj" 
    },
    "Roxy": {
        "url": "http://51.77.216.195/crapi/rx/viewstats", 
        "token": "QldXSDRSQlaDYWFDSm2DWGSOWHZ8hW9-hlGTe2ptZXxgmIBjaox1" 
    }
}

# Full Country List from your uploaded bot.py
COUNTRY_CODES = {
    '1': ('USA/Canada', '🇺🇸'), '7': ('Russia/Kazakhstan', '🇷🇺'), '20': ('Egypt', '🇪🇬'), '27': ('South Africa', '🇿🇦'),
    '30': ('Greece', '🇬🇷'), '31': ('Netherlands', '🇳🇱'), '32': ('Belgium', '🇧🇪'), '33': ('France', '🇫🇷'),
    '34': ('Spain', '🇪🇸'), '36': ('Hungary', '🇭🇺'), '39': ('Italy', '🇮🇹'), '40': ('Romania', '🇷🇴'),
    '41': ('Switzerland', '🇨🇭'), '43': ('Austria', '🇦🇹'), '44': ('United Kingdom', '🇬🇧'), '45': ('Denmark', '🇩🇰'),
    '46': ('Sweden', '🇸🇪'), '47': ('Norway', '🇳🇴'), '48': ('Poland', '🇵🇱'), '49': ('Germany', '🇩🇪'),
    '51': ('Peru', '🇵🇪'), '52': ('Mexico', '🇲🇽'), '53': ('Cuba', '🇨🇺'), '54': ('Argentina', '🇦🇷'),
    '55': ('Brazil', '🇧🇷'), '56': ('Chile', '🇨🇱'), '57': ('Colombia', '🇨🇴'), '58': ('Venezuela', '🇻🇪'),
    '60': ('Malaysia', '🇲🇾'), '61': ('Australia', '🇦🇺'), '62': ('Indonesia', '🇮🇩'), '63': ('Philippines', '🇵🇭'),
    '64': ('New Zealand', '🇳🇿'), '65': ('Singapore', '🇸🇬'), '66': ('Thailand', '🇹🇭'), '81': ('Japan', '🇯🇵'),
    '82': ('South Korea', '🇰🇷'), '84': ('Viet Nam', '🇻🇳'), '86': ('China', '🇨🇳'), '90': ('Turkey', '🇹🇷'),
    '91': ('India', '🇮🇳'), '92': ('Pakistan', '🇵🇰'), '93': ('Afghanistan', '🇦🇫'), '94': ('Sri Lanka', '🇱🇰'),
    '95': ('Myanmar', '🇲🇲'), '98': ('Iran', '🇮🇷'), '211': ('South Sudan', '🇸🇸'), '212': ('Morocco', '🇲🇦'),
    '213': ('Algeria', '🇩🇿'), '216': ('Tunisia', '🇹🇳'), '218': ('Libya', '🇱🇾'), '220': ('Gambia', '🇬🇲'),
    '221': ('Senegal', '🇸🇳'), '222': ('Mauritania', '🇲🇷'), '223': ('Mali', '🇲🇱'), '224': ('Guinea', '🇬🇳'),
    '225': ("Côte d'Ivoire", '🇨🇮'), '226': ('Burkina Faso', '🇧🇫'), '227': ('Niger', '🇳🇪'), '228': ('Togo', '🇹🇬'),
    '229': ('Benin', '🇧🇯'), '230': ('Mauritius', '🇲🇺'), '231': ('Liberia', '🇱🇷'), '232': ('Sierra Leone', '🇸🇱'),
    '233': ('Ghana', '🇬🇭'), '234': ('Nigeria', '🇳🇬'), '235': ('Chad', '🇹🇩'), '236': ('Central African Republic', '🇨🇫'),
    '237': ('Cameroon', '🇨🇲'), '238': ('Cape Verde', '🇨🇻'), '239': ('Sao Tome and Principe', '🇸🇹'),
    '240': ('Equatorial Guinea', '🇬🇶'), '241': ('Gabon', '🇬🇦'), '242': ('Congo', '🇨🇬'),
    '243': ('DR Congo', '🇨🇩'), '244': ('Angola', '🇦🇴'), '245': ('Guinea-Bissau', '🇬🇼'), '248': ('Seychelles', '🇸🇨'),
    '249': ('Sudan', '🇸🇩'), '250': ('Rwanda', '🇷🇼'), '251': ('Ethiopia', '🇪🇹'), '252': ('Somalia', '🇸🇴'),
    '253': ('Djibouti', '🇩🇯'), '254': ('Kenya', '🇰🇪'), '255': ('Tanzania', '🇹🇿'), '256': ('Uganda', '🇺🇬'),
    '257': ('Burundi', '🇧🇮'), '258': ('Mozambique', '🇲🇿'), '260': ('Zambia', '🇿🇲'), '261': ('Madagascar', '🇲🇬'),
    '263': ('Zimbabwe', '🇿🇼'), '264': ('Namibia', '🇳🇦'), '265': ('Malawi', '🇲🇼'), '266': ('Lesotho', '🇱🇸'),
    '267': ('Botswana', '🇧🇼'), '268': ('Eswatini', '🇸🇿'), '269': ('Comoros', '🇰🇲'), '290': ('Saint Helena', '🇸🇭'),
    '291': ('Eritrea', '🇪🇷'), '297': ('Aruba', '🇦🇼'), '298': ('Faroe Islands', '🇫🇴'), '299': ('Greenland', '🇬🇱'),
    '350': ('Gibraltar', '🇬🇮'), '351': ('Portugal', '🇵🇹'), '352': ('Luxembourg', '🇱🇺'), '353': ('Ireland', '🇮🇪'),
    '354': ('Iceland', '🇮🇸'), '355': ('Albania', '🇦🇱'), '356': ('Malta', '🇲🇹'), '357': ('Cyprus', '🇨🇾'),
    '358': ('Finland', '🇫🇮'), '359': ('Bulgaria', '🇧🇬'), '370': ('Lithuania', '🇱🇹'), '371': ('Latvia', '🇱🇻'),
    '372': ('Estonia', '🇪🇪'), '373': ('Moldova', '🇲🇩'), '374': ('Armenia', '🇦🇲'), '375': ('Belarus', '🇧🇾'),
    '376': ('Andorra', '🇦🇩'), '377': ('Monaco', '🇲🇨'), '378': ('San Marino', '🇸🇲'), '380': ('Ukraine', '🇺🇦'),
    '381': ('Serbia', '🇷🇸'), '382': ('Montenegro', '🇲🇪'), '385': ('Croatia', '🇭🇷'), '386': ('Slovenia', '🇸🇮'),
    '387': ('Bosnia and Herzegovina', '🇧🇦'), '389': ('North Macedonia', '🇲🇰'), '420': ('Czech Republic', '🇨🇿'),
    '421': ('Slovakia', '🇸🇰'), '423': ('Liechtenstein', '🇱🇮'), '501': ('Belize', '🇧🇿'), '502': ('Guatemala', '🇬🇹'),
    '503': ('El Salvador', '🇸🇻'), '504': ('Honduras', '🇭🇳'), '505': ('Nicaragua', '🇳🇮'), '506': ('Costa Rica', '🇨🇷'),
    '507': ('Panama', '🇵🇦'), '509': ('Haiti', '🇭🇹'), '590': ('Guadeloupe', '🇬🇵'), '591': ('Bolivia', '🇧🇴'),
    '592': ('Guyana', '🇬🇾'), '593': ('Ecuador', '🇪🇨'), '595': ('Paraguay', '🇵🇾'), '597': ('Suriname', '🇸🇷'),
    '598': ('Uruguay', '🇺🇾'), '673': ('Brunei', '🇧🇳'), '675': ('Papua New Guinea', '🇵🇬'), '676': ('Tonga', '🇹🇴'),
    '677': ('Solomon Islands', '🇸🇧'), '678': ('Vanuatu', '🇻🇺'), '679': ('Fiji', '🇫🇯'), '685': ('Samoa', '🇼🇸'),
    '689': ('French Polynesia', '🇵🇫'), '852': ('Hong Kong', '🇭🇰'), '853': ('Macau', '🇲🇴'), '855': ('Cambodia', '🇰🇭'),
    '856': ('Laos', '🇱🇦'), '880': ('Bangladesh', '🇧🇩'), '886': ('Taiwan', '🇹🇼'), '960': ('Maldives', '🇲🇻'),
    '961': ('Lebanon', '🇱🇧'), '962': ('Jordan', '🇯🇴'), '963': ('Syria', '🇸🇾'), '964': ('Iraq', '🇮🇶'),
    '965': ('Kuwait', '🇰🇼'), '966': ('Saudi Arabia', '🇸🇦'), '967': ('Yemen', '🇾🇪'), '968': ('Oman', '🇴🇲'),
    '970': ('Palestine', '🇵🇸'), '971': ('United Arab Emirates', '🇦🇪'), '972': ('Israel', '🇮🇱'),
    '973': ('Bahrain', '🇧🇭'), '974': ('Qatar', '🇶🇦'), '975': ('Bhutan', '🇧🇹'), '976': ('Mongolia', '🇲🇳'),
    '977': ('Nepal', '🇳🇵'), '992': ('Tajikistan', '🇹🇯'), '993': ('Turkmenistan', '🇹🇲'), '994': ('Azerbaijan', '🇦🇿'),
    '995': ('Georgia', '🇬🇪'), '996': ('Kyrgyzstan', '🇰🇬'), '998': ('Uzbekistan', '🇺🇿'),
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
reported_hashes = set()

# Functions for detection and formatting
def get_country_info(phone):
    for i in range(4, 0, -1):
        prefix = phone[:i]
        if prefix in COUNTRY_CODES: return COUNTRY_CODES[prefix]
    return ('Unknown', '🌐')

def detect_service(msg):
    msg = msg.lower()
    services = ['whatsapp', 'google', 'facebook', 'telegram', 'instagram', 'snapchat', 'tiktok', 'apple', 'amazon', 'viber', 'imo']
    for s in services:
        if s in msg: return s.upper()
    return "OTP SERVICE"

def create_markup():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Number Channel 🚀", url=CHANNEL_LINK))
    builder.row(types.InlineKeyboardButton(text="Owner 👑", url=OWNER_LINK))
    return builder.as_markup()

# Admin Commands
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("<b>Welcome Admin! 👑</b>\nMonitoring started for 3 sites.\n/status - Check Health", parse_mode="HTML")
    else:
        await message.answer("Bot is online. Join channel for updates.")

# Core Monitoring Loop
async def fetch_updates():
    async with aiohttp.ClientSession() as session:
        while True:
            for site_name, config in SITES.items():
                try:
                    params = {'token': config['token'], 'records': 5}
                    async with session.get(config['url'], params=params, timeout=15) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("status") == "success":
                                for item in reversed(data.get("data", [])):
                                    msg_hash = hashlib.md5(f"{item['num']}{item['message']}".encode()).hexdigest()
                                    if msg_hash not in reported_hashes:
                                        reported_hashes.add(msg_hash)
                                        
                                        country_name, flag = get_country_info(item['num'])
                                        service = detect_service(item['message'])
                                        otp_match = re.search(r'\b\d{4,8}\b', item['message'])
                                        otp = otp_match.group(0) if otp_match else "N/A"

                                        text = (
                                            f"✅ {flag} <b>{country_name} {service} OTP Received!</b>\n"
                                            f"━━━━━━━━━━━━━━━━━━━━\n"
                                            f"📱 <b>Number:</b> <code>{item['num']}</code>\n"
                                            f"🌍 <b>Country:</b> {flag} {country_name}\n"
                                            f"⚙️ <b>Service:</b> {service}\n"
                                            f"🔒 <b>OTP Code:</b> <code>{otp}</code>\n"
                                            f"⏳ <b>Time:</b> <code>{item['dt']}</code>\n"
                                            f"━━━━━━━━━━━━━━━━━━━━\n"
                                            f"💬 <b>Message:</b>\n<code>{item['message']}</code>\n"
                                            f"━━━━━━━━━━━━━━━━━━━━\n"
                                            f"👤 <b>By:</b> <a href='{OWNER_LINK}'>Illuminate786</a>"
                                        )
                                        await bot.send_message(CHANNEL_ID, text, parse_mode="HTML", reply_markup=create_markup(), disable_web_page_preview=True)
                except Exception as e:
                    print(f"Error at {site_name}: {e}")
            await asyncio.sleep(20)

# Render Keep-Alive Server
app = Flask('')
@app.route('/')
def home(): return "Bot is Online"
def run_web(): app.run(host='0.0.0.0', port=8080)

async def main():
    Thread(target=run_web).start()
    asyncio.create_task(fetch_updates())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
