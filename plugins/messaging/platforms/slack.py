"""Slack Bot 适配器"""

import os


class SlackAdapter:
    def __init__(self, token: str = ""):
        self._token = token or os.environ.get("SLACK_BOT_TOKEN", "")
        self._running = False

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    async def start(self):
        self._running = True

    async def stop(self):
        self._running = False

    async def send_message(self, channel: str, text: str) -> dict:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {self._token}"},
                    json={"channel": channel, "text": text[:4000]},
                )
                return r.json()
        except Exception as e:
            return {"error": str(e)}
