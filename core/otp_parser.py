import re

def extract_otp(text):
    m = re.search(r"\b(\d{4,8})\b", text)
    return m.group(1) if m else None
