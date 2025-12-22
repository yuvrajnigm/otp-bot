# core/detector.py

import re

# ==============================
# COUNTRY FLAGS
# ==============================
COUNTRY_FLAGS = {
    "Afghanistan": "🇦🇫", "Albania": "🇦🇱", "Algeria": "🇩🇿", "Andorra": "🇦🇩", "Angola": "🇦🇴",
    "Argentina": "🇦🇷", "Armenia": "🇦🇲", "Australia": "🇦🇺", "Austria": "🇦🇹", "Azerbaijan": "🇦🇿",
    "Bahrain": "🇧🇭", "Bangladesh": "🇧🇩", "Belarus": "🇧🇾", "Belgium": "🇧🇪", "Benin": "🇧🇯",
    "Bhutan": "🇧🇹", "Bolivia": "🇧🇴", "Brazil": "🇧🇷", "Bulgaria": "🇧🇬", "Burkina Faso": "🇧🇫",
    "Cambodia": "🇰🇭", "Cameroon": "🇨🇲", "Canada": "🇨🇦", "Chad": "🇹🇩", "Chile": "🇨🇱",
    "China": "🇨🇳", "Colombia": "🇨🇴", "Congo": "🇨🇬", "Croatia": "🇭🇷", "Cuba": "🇨🇺",
    "Cyprus": "🇨🇾", "Czech Republic": "🇨🇿", "Denmark": "🇩🇰", "Egypt": "🇪🇬",
    "Estonia": "🇪🇪", "Ethiopia": "🇪🇹", "Finland": "🇫🇮", "France": "🇫🇷",
    "Germany": "🇩🇪", "Ghana": "🇬🇭", "Greece": "🇬🇷", "Hong Kong": "🇭🇰",
    "Hungary": "🇭🇺", "Iceland": "🇮🇸", "India": "🇮🇳", "Indonesia": "🇮🇩",
    "Iran": "🇮🇷", "Iraq": "🇮🇶", "Ireland": "🇮🇪", "Israel": "🇮🇱",
    "Italy": "🇮🇹", "Japan": "🇯🇵", "Kenya": "🇰🇪", "Kuwait": "🇰🇼",
    "Malaysia": "🇲🇾", "Mexico": "🇲🇽", "Netherlands": "🇳🇱", "Nigeria": "🇳🇬",
    "Norway": "🇳🇴", "Pakistan": "🇵🇰", "Philippines": "🇵🇭", "Poland": "🇵🇱",
    "Portugal": "🇵🇹", "Qatar": "🇶🇦", "Romania": "🇷🇴", "Russia": "🇷🇺",
    "Saudi Arabia": "🇸🇦", "Singapore": "🇸🇬", "South Africa": "🇿🇦",
    "South Korea": "🇰🇷", "Spain": "🇪🇸", "Sri Lanka": "🇱🇰",
    "Sweden": "🇸🇪", "Switzerland": "🇨🇭", "Thailand": "🇹🇭",
    "Turkey": "🇹🇷", "Ukraine": "🇺🇦", "United Kingdom": "🇬🇧",
    "United States": "🇺🇸", "Vietnam": "🇻🇳",
    "Unknown Country": "🏴‍☠️"
}

# ==============================
# SERVICE KEYWORDS
# ==============================
SERVICE_KEYWORDS = {
    "Telegram": ["telegram"],
    "WhatsApp": ["whatsapp"],
    "Facebook": ["facebook"],
    "Instagram": ["instagram"],
    "Google": ["google", "gmail"],
    "Amazon": ["amazon"],
    "Netflix": ["netflix"],
    "Twitter": ["twitter", "x"],
    "Snapchat": ["snapchat"],
    "TikTok": ["tiktok"],
    "Discord": ["discord"],
    "PayPal": ["paypal"],
    "Binance": ["binance"],
    "Uber": ["uber"],
    "LinkedIn": ["linkedin"],
    "Microsoft": ["microsoft", "outlook"],
    "Apple": ["apple", "icloud"],
    "Spotify": ["spotify"],
    "Zomato": ["zomato"],
    "Swiggy": ["swiggy"],
    "Flipkart": ["flipkart"],
    "OnlyFans": ["onlyfans"],
    "Tinder": ["tinder"],
    "Bumble": ["bumble"],
    "Unknown": []
}

# ==============================
# SERVICE EMOJIS
# ==============================
SERVICE_EMOJIS = {
    "Telegram": "📩",
    "WhatsApp": "🟢",
    "Facebook": "📘",
    "Instagram": "📸",
    "Google": "🔍",
    "Amazon": "🛒",
    "Netflix": "🎬",
    "Twitter": "🐦",
    "Snapchat": "👻",
    "TikTok": "🎵",
    "Discord": "💬",
    "PayPal": "💰",
    "Binance": "🪙",
    "Uber": "🚗",
    "LinkedIn": "💼",
    "Microsoft": "🪟",
    "Apple": "🍏",
    "Spotify": "🎶",
    "Zomato": "🍽️",
    "Swiggy": "🍔",
    "Flipkart": "📦",
    "OnlyFans": "🔞",
    "Tinder": "🔥",
    "Bumble": "🐝",
    "Unknown": "❓"
}

# ==============================
# OTP EXTRACTOR
# ==============================
OTP_REGEX = re.compile(r"\b(\d{4,8})\b")

def extract_otp(text: str):
    match = OTP_REGEX.search(text)
    return match.group(1) if match else None


def detect_service(text: str):
    text_lower = text.lower()
    for service, keywords in SERVICE_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return service
    return "Unknown"


def detect_country(text: str):
    for country in COUNTRY_FLAGS:
        if country.lower() in text.lower():
            return country
    return "Unknown Country"


def analyze_message(text: str):
    otp = extract_otp(text)
    service = detect_service(text)
    country = detect_country(text)

    return {
        "otp": otp,
        "service": service,
        "service_emoji": SERVICE_EMOJIS.get(service, "❓"),
        "country": country,
        "country_flag": COUNTRY_FLAGS.get(country, "🏴‍☠️")
    }
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
