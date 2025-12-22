import httpx

async def fetch_sms(panel):
    async with httpx.AsyncClient() as c:
        r = await c.get(panel["sms_api"], timeout=20)
        return r.text
