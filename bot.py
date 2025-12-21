import asyncio, os, json
from telegram.ext import Application, CommandHandler
from aiohttp import web
import httpx

from core.parser import parse_text
from core.storage import is_seen, mark_seen
from panels.ints_sms import IntsSMSPanel

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PORT = int(os.getenv("PORT", 8080))

PANELS_FILE = "config/panels.json"
ENABLED_PANELS_FILE = "config/enabled_panels.json"
CHATS_FILE = "config/chat_ids.json"

# ---------- KEEP ALIVE ----------
async def health(request):
    return web.Response(text="OK")

async def run_web():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

async def keep_alive():
    while True:
        print("✅ Bot alive")
        await asyncio.sleep(300)

# ---------- HELP ----------
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f)
        return default
    return json.load(open(path))

# ---------- POLLING ----------
async def poll_panels(app):
    while True:
        try:
            panels = load_json(PANELS_FILE, {})
            enabled = load_json(ENABLED_PANELS_FILE, [])
            chats = load_json(CHATS_FILE, [])

            for pname in enabled:
                cfg = panels.get(pname)
                if not cfg:
                    continue

                async with httpx.AsyncClient(timeout=30) as client:
                    panel = IntsSMSPanel(cfg)
                    await panel.login(client)
                    messages = await panel.fetch_items(client)

                    for text in messages:
                        if is_seen(text):
                            continue

                        data = parse_text(text)
                        msg = (
                            "🔔 *New OTP*\n\n"
                            f"{data['emoji']} *Service:* {data['service']}\n"
                            f"📞 *Number:* `{data['phone']}`\n"
                            f"🌍 *Country:* {data['country']} {data['flag']}\n"
                            f"🔑 *OTP:* `{data['otp']}`\n\n"
                            f"```{data['text']}```"
                        )

                        for cid in chats:
                            await app.bot.send_message(cid, msg, parse_mode="Markdown")

                        mark_seen(text)

            await asyncio.sleep(5)
        except Exception as e:
            print("Error:", e)
            await asyncio.sleep(10)

# ---------- TELEGRAM ----------
async def start(update, context):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("🤖 OTP Bot is LIVE")

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    asyncio.create_task(run_web())
    asyncio.create_task(keep_alive())
    asyncio.create_task(poll_panels(app))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
