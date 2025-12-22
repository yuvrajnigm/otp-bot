from panels.sms_panel import fetch_sms
from panels.call_panel import fetch_call

async def fetch_any(panel):
    try:
        return await fetch_sms(panel)
    except:
        return await fetch_call(panel)
