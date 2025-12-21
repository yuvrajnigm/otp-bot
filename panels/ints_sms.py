from bs4 import BeautifulSoup
from .base import BasePanel

class IntsSMSPanel(BasePanel):
    async def login(self, client):
        await client.post(self.cfg["login_url"], data={
            self.cfg["user_field"]: self.cfg["user"],
            self.cfg["pass_field"]: self.cfg["pass"]
        })

    async def fetch_items(self, client):
        r = await client.post(self.cfg["sms_endpoint"])
        soup = BeautifulSoup(r.text, "html.parser")
        return [p.get_text(strip=True) for p in soup.find_all("p")]
