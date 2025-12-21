import re

def parse_text(text):
    otp = re.search(r'\b(\d{4,8})\b', text)
    phone = re.search(r'(\+?\d{8,15})', text)

    return {
        "otp": otp.group(1) if otp else "N/A",
        "phone": phone.group(1) if phone else "Unknown",
        "service": "Unknown",
        "emoji": "📩",
        "country": "Unknown",
        "flag": "🌍",
        "text": text
    }
