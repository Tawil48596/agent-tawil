"""Authenticated, deduplicated messaging-to-agent gateway."""

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable


@dataclass(frozen=True)
class InboundMessage:
    provider: str
    event_id: str
    channel_id: str
    user_id: str
    text: str


class MessagingGateway:
    def __init__(self, config: dict | None = None,
                 state_path: str | Path = "data/messaging/sessions.json"):
        cfg = config or {}
        self._secrets = cfg.get("webhook_secrets", {})
        self._allowed = {name: set(values) for name, values in cfg.get("allowed_senders", {}).items()}
        self._state_path = Path(state_path)
        self._sessions: dict[str, str] = {}
        self._seen: dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        if self._state_path.exists():
            try:
                self._sessions = json.loads(self._state_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._sessions = {}

    def _save(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(self._sessions, indent=2), encoding="utf-8")
        temp.replace(self._state_path)

    def verify_signature(self, provider: str, payload: bytes, signature: str) -> bool:
        secret = self._secrets.get(provider, "")
        if not secret:
            return True
        supplied = signature.removeprefix("sha256=")
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, supplied)

    def normalize(self, provider: str, event: dict[str, Any]) -> InboundMessage:
        if provider == "telegram":
            message = event.get("message", {})
            return InboundMessage(provider, str(event.get("update_id", "")),
                str(message.get("chat", {}).get("id", "")), str(message.get("from", {}).get("id", "")),
                message.get("text", ""))
        if provider == "slack":
            message = event.get("event", event)
            return InboundMessage(provider, event.get("event_id", message.get("client_msg_id", "")),
                str(message.get("channel", "")), str(message.get("user", "")), message.get("text", ""))
        if provider == "discord":
            return InboundMessage(provider, str(event.get("id", "")), str(event.get("channel_id", "")),
                str(event.get("author", {}).get("id", "")), event.get("content", ""))
        raise ValueError(f"Unsupported messaging provider: {provider}")

    def _authorize(self, message: InboundMessage) -> None:
        if not all((message.event_id, message.channel_id, message.user_id, message.text.strip())):
            raise ValueError("Incomplete message event")
        allowed = self._allowed.get(message.provider, set())
        if allowed and message.user_id not in allowed:
            raise PermissionError("Sender is not allowed")
        dedupe_key = f"{message.provider}:{message.event_id}"
        if dedupe_key in self._seen:
            raise ValueError("Duplicate message event")
        self._seen[dedupe_key] = time.time()
        if len(self._seen) > 5000:
            cutoff = time.time() - 86400
            self._seen = {key: value for key, value in self._seen.items() if value >= cutoff}

    def session_for(self, message: InboundMessage) -> str:
        key = f"{message.provider}:{message.channel_id}:{message.user_id}"
        if key not in self._sessions:
            self._sessions[key] = uuid.uuid5(uuid.NAMESPACE_URL, key).hex
            self._save()
        return self._sessions[key]

    async def process(self, provider: str, event: dict[str, Any], payload: bytes,
                      signature: str, agent_fn: Callable[[str, str], Awaitable[str]]) -> dict:
        if not self.verify_signature(provider, payload, signature):
            raise PermissionError("Invalid webhook signature")
        message = self.normalize(provider, event)
        self._authorize(message)
        session_id = self.session_for(message)
        reply = await agent_fn(message.text, session_id)
        return {"ok": True, "provider": provider, "session_id": session_id,
                "channel_id": message.channel_id, "reply": reply}
