import asyncio
from core.panel_manager import load_panels
from core.chat_manager import load_chats
from core.otp_parser import extract_otp
from core.detector import extract_phone, detect_country, detect_service
from panels.sms_panel import fetch_sms
from panels.call_panel import fetch_call
from panels.hybrid_panel import fetch_any

async def poll_panels(app):
    while True:
        panels = load_panels()
        chats = load_chats()

        for pid, panel in panels.items():
            if not panel.get("enabled"):
                continue

            try:
                if panel["mode"] == "sms":
                    text = await fetch_sms(pid, panel)
                elif panel["mode"] == "call":
                    text = await fetch_call(pid, panel)
                else:
                    text = await fetch_any(pid, panel)

                otp = extract_otp(text)
                if not otp:
                    continue

                phone = extract_phone(text)
                country = detect_country(phone)
                service, emoji = detect_service(text)

                msg = (
                    f"{emoji} {service}\n"
                    f"🌍 {country}\n"
                    f"📱 {phone}\n"
                    f"🔐 OTP: {otp}\n"
                    f"🧩 Panel: {panel['name']}"
                )

                for chat in chats:
                    await app.bot.send_message(chat, msg)

            except Exception as e:
                print("Poll error:", e)

        await asyncio.sleep(10)
