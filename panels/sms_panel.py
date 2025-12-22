from core.login_manager import get_session

async def fetch_sms(panel_id, panel):
    session = await get_session(panel_id, panel)
    r = await session.get(panel["sms_api"])
    return r.text
