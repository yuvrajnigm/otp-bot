import json, os, hashlib

FILE = "config/seen.json"

def is_seen(text):
    if not os.path.exists(FILE):
        return False
    seen = json.load(open(FILE))
    h = hashlib.md5(text.encode()).hexdigest()
    return h in seen

def mark_seen(text):
    h = hashlib.md5(text.encode()).hexdigest()
    seen = []
    if os.path.exists(FILE):
        seen = json.load(open(FILE))
    if h not in seen:
        seen.append(h)
    json.dump(seen, open(FILE, "w"))
