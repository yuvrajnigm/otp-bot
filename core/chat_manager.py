import json, os

CHAT_FILE = "config/chats.json"

def load_chats():
    if not os.path.exists(CHAT_FILE):
        return []
    with open(CHAT_FILE) as f:
        return json.load(f)

def save_chats(chats):
    with open(CHAT_FILE, "w") as f:
        json.dump(chats, f, indent=2)

def add_chat(chat_id):
    chats = load_chats()
    if chat_id not in chats:
        chats.append(chat_id)
        save_chats(chats)

def remove_chat(chat_id):
    chats = load_chats()
    if chat_id in chats:
        chats.remove(chat_id)
        save_chats(chats)
