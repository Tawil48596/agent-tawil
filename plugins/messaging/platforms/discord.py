"""Discord Bot 适配器"""

import os


class DiscordAdapter:
    def __init__(self, token: str = ""):
        self._token = token or os.environ.get("DISCORD_BOT_TOKEN", "")
        self._running = False

    @property
    def is_configured(self) -> bool: return bool(self._token)

    async def start(self): self._running = True
    async def stop(self): self._running = False

    async def send_message(self, channel_id: str, text: str) -> dict:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(f"https://discord.com/api/v10/channels/{channel_id}/messages",
                    headers={"Authorization": f"Bot {self._token}"},
                    json={"content": text[:2000]})
                return r.json()
        except Exception as e:
            return {"error": str(e)}
