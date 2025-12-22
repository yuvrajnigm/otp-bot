# core/detector.py
# ===============================
# OTP Detector Engine
# Country + Service + Emoji
# ===============================

import re, phonenumbers
from phonenumbers import geocoder

# =========================
# COUNTRY FLAGS
# =========================

COUNTRY_FLAGS = {
    "Afghanistan": "🇦🇫", "Albania": "🇦🇱", "Algeria": "🇩🇿", "Andorra": "🇦🇩", "Angola": "🇦🇴",
    "Argentina": "🇦🇷", "Armenia": "🇦🇲", "Australia": "🇦🇺", "Austria": "🇦🇹", "Azerbaijan": "🇦🇿",
    "Bahrain": "🇧🇭", "Bangladesh": "🇧🇩", "Belarus": "🇧🇾", "Belgium": "🇧🇪", "Benin": "🇧🇯",
    "Bhutan": "🇧🇹", "Bolivia": "🇧🇴", "Brazil": "🇧🇷", "Bulgaria": "🇧🇬", "Burkina Faso": "🇧🇫",
    "Cambodia": "🇰🇭", "Cameroon": "🇨🇲", "Canada": "🇨🇦", "Chad": "🇹🇩", "Chile": "🇨🇱",
    "China": "🇨🇳", "Colombia": "🇨🇴", "Congo": "🇨🇬", "Croatia": "🇭🇷", "Cuba": "🇨🇺",
    "Cyprus": "🇨🇾", "Czech Republic": "🇨🇿", "Denmark": "🇩🇰", "Egypt": "🇪🇬",
    "Estonia": "🇪🇪", "Ethiopia": "🇪🇹", "Finland": "🇫🇮", "France": "🇫🇷",
    "Georgia": "🇬🇪", "Germany": "🇩🇪", "Ghana": "🇬🇭", "Greece": "🇬🇷",
    "Hong Kong": "🇭🇰", "Hungary": "🇭🇺", "Iceland": "🇮🇸", "India": "🇮🇳",
    "Indonesia": "🇮🇩", "Iran": "🇮🇷", "Iraq": "🇮🇶", "Ireland": "🇮🇪",
    "Israel": "🇮🇱", "Italy": "🇮🇹", "Ivory Coast": "🇨🇮", "Japan": "🇯🇵",
    "Jordan": "🇯🇴", "Kazakhstan": "🇰🇿", "Kenya": "🇰🇪", "Kuwait": "🇰🇼",
    "Malaysia": "🇲🇾", "Mexico": "🇲🇽", "Morocco": "🇲🇦", "Nepal": "🇳🇵",
    "Netherlands": "🇳🇱", "Nigeria": "🇳🇬", "Pakistan": "🇵🇰",
    "Philippines": "🇵🇭", "Russia": "🇷🇺", "Saudi Arabia": "🇸🇦",
    "Singapore": "🇸🇬", "South Africa": "🇿🇦", "South Korea": "🇰🇷",
    "Spain": "🇪🇸", "Sri Lanka": "🇱🇰", "Sweden": "🇸🇪",
    "Switzerland": "🇨🇭", "Thailand": "🇹🇭", "Turkey": "🇹🇷",
    "Ukraine": "🇺🇦", "United Arab Emirates": "🇦🇪",
    "United Kingdom": "🇬🇧", "United States": "🇺🇸",
    "Vietnam": "🇻🇳", "Unknown Country": "🏴‍☠️"
}

# =========================
# SERVICE KEYWORDS
# =========================

SERVICE_KEYWORDS = {
    "Telegram": ["telegram"],
    "WhatsApp": ["whatsapp"],
    "Facebook": ["facebook"],
    "Instagram": ["instagram"],
    "Google": ["google", "gmail"],
    "Twitter": ["twitter", "x"],
    "TikTok": ["tiktok"],
    "Snapchat": ["snapchat"],
    "Amazon": ["amazon"],
    "Netflix": ["netflix"],
    "Binance": ["binance"],
    "PayPal": ["paypal"],
    "Discord": ["discord"],
    "Steam": ["steam"],
    "Uber": ["uber"],
    "Zomato": ["zomato"],
    "Swiggy": ["swiggy"],
    "Tinder": ["tinder"],
    "Bumble": ["bumble"],
    "Signal": ["signal"],
    "Line": ["line"],
    "WeChat": ["wechat"],
    "OnlyFans": ["onlyfans"],
    "Unknown": []
}

# =========================
# SERVICE EMOJIS
# =========================

SERVICE_EMOJIS = {
    "Telegram": "📩",
    "WhatsApp": "🟢",
    "Facebook": "📘",
    "Instagram": "📸",
    "Google": "🔍",
    "Twitter": "🐦",
    "TikTok": "🎵",
    "Snapchat": "👻",
    "Amazon": "🛒",
    "Netflix": "🎬",
    "Binance": "🪙",
    "PayPal": "💰",
    "Discord": "🗨️",
    "Steam": "🎮",
    "Uber": "🚗",
    "Zomato": "🍽️",
    "Swiggy": "🍔",
    "Tinder": "🔥",
    "Bumble": "🐝",
    "Signal": "🔐",
    "Line": "💬",
    "WeChat": "💬",
    "OnlyFans": "🔞",
    "Unknown": "❓"
}

# =========================
# CORE FUNCTIONS
# =========================

def detect_otp(text: str):
    match = re.search(r"\b(\d{4,8})\b", text)
    return match.group(1) if match else None


def detect_service(text: str):
    lower = text.lower()
    for service, keywords in SERVICE_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return service
    return "Unknown"


def detect_country(text: str):
    for country in COUNTRY_FLAGS:
        if country.lower() in text.lower():
            return country
    return "Unknown Country"


def format_otp_message(text: str):
    otp = detect_otp(text)
    service = detect_service(text)
    country = detect_country(text)

    flag = COUNTRY_FLAGS.get(country, "🏴‍☠️")
    emoji = SERVICE_EMOJIS.get(service, "❓")

    if not otp:
        return None

    return (
        f"{flag} {country}\n"
        f"{emoji} {service}\n\n"
        f"🔐 OTP: `{otp}`"
    )
