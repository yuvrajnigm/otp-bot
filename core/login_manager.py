import httpx

_sessions = {}

async def get_session(panel_id, panel):
    if panel_id in _sessions:
        return _sessions[panel_id]

    client = httpx.AsyncClient(base_url=panel["base_url"], timeout=20)

    data = {
        "username": panel.get("username"),
        "email": panel.get("email"),
        "password": panel["password"]
    }

    await client.post(panel["login_url"], data=data)
    _sessions[panel_id] = client
    return client
