"""Telegram Bot 适配器"""

import os
from collections.abc import Callable

import structlog

logger = structlog.get_logger()


class TelegramAdapter:
    """Telegram Bot 消息平台适配器"""

    BASE_URL = "https://api.telegram.org"

    def __init__(self, token: str = None):
        self._token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self._message_handler: Callable | None = None
        self._running = False
        self._offset = 0

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    async def start(self):
        """启动 polling"""
        if not self._token:
            logger.warning("Telegram token not configured")
            return
        self._running = True
        logger.info("Telegram bot started")
        # Polling loop (简化版: 由外部调用者驱动)

    async def stop(self):
        self._running = False

    async def send_message(self, chat_id: str, text: str, parse_mode: str = "Markdown") -> dict:
        """发送消息"""
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/bot{self._token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text[:4000],  # Telegram 限制
                    "parse_mode": parse_mode,
                },
            )
            return resp.json()

    async def poll_updates(self) -> list[dict]:
        """获取新消息"""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/bot{self._token}/getUpdates",
                params={"offset": self._offset + 1, "timeout": 30},
            )
            data = resp.json()
            updates = data.get("result", [])
            if updates:
                self._offset = updates[-1]["update_id"]
            return updates

    def on_message(self, handler: Callable):
        self._message_handler = handler

    async def handle_update(self, update: dict, agent_fn: Callable):
        """处理单条更新"""
        msg = update.get("message", {})
        chat_id = msg.get("chat", {}).get("id", "")
        text = msg.get("text", "")

        if text and chat_id:
            if text.startswith("/"):
                await self._handle_command(chat_id, text)
            elif self._message_handler:
                await self._message_handler(chat_id, text)
            else:
                # 默认: 转发给 Agent
                try:
                    response = await agent_fn(text)
                    await self.send_message(chat_id, response)
                except Exception as e:
                    await self.send_message(chat_id, f"Error: {str(e)}")

    async def _handle_command(self, chat_id: str, command: str):
        """处理 Telegram 命令"""
        cmd = command.split()[0].lower()
        handlers = {
            "/start": lambda: "Welcome to AI Agent Platform! Send me a message to get started.",
            "/help": lambda: "Commands:\n/start - Welcome\n/help - Help\n/models - List models",
            "/models": lambda: "Available models: GPT-4o, Claude Sonnet 4, DeepSeek V4",
        }
        handler = handlers.get(cmd, lambda: f"Unknown command: {cmd}")
        await self.send_message(chat_id, handler())
