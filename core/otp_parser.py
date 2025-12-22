import re, phonenumbers
from phonenumbers import geocoder

def extract_otp(text):
    m = re.search(r"\b(\d{4,8})\b", text)
    return m.group(1) if m else "N/A"

def detect_country(number):
    try:
        num = phonenumbers.parse(number, None)
        return geocoder.description_for_number(num, "en")
    except:
        return "Unknown"
