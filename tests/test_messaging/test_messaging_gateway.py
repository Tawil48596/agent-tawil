import hashlib
import hmac
import json

import pytest

from plugins.messaging.gateway import MessagingGateway


@pytest.mark.asyncio
async def test_authenticated_message_has_stable_session_and_dedupes(tmp_path):
    gateway = MessagingGateway(
        {"webhook_secrets": {"slack": "secret"}, "allowed_senders": {"slack": ["u1"]}},
        tmp_path / "sessions.json",
    )
    event = {"event_id": "e1", "event": {"channel": "c1", "user": "u1", "text": "hello"}}
    payload = json.dumps(event).encode()
    signature = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()

    async def agent(text, session):
        return f"{session}:{text}"

    result = await gateway.process("slack", event, payload, signature, agent)
    assert result["reply"].endswith(":hello")
    restored = MessagingGateway({}, tmp_path / "sessions.json")
    assert restored.normalize("slack", event).text == "hello"
    assert result["session_id"] in restored._sessions.values()
    with pytest.raises(ValueError, match="Duplicate"):
        await gateway.process("slack", event, payload, signature, agent)


@pytest.mark.asyncio
async def test_rejects_invalid_signature_and_sender(tmp_path):
    event = {"id": "e1", "channel_id": "c", "author": {"id": "blocked"}, "content": "hi"}
    payload = json.dumps(event).encode()
    gateway = MessagingGateway({"webhook_secrets": {"discord": "secret"}}, tmp_path / "one.json")
    with pytest.raises(PermissionError, match="signature"):
        await gateway.process("discord", event, payload, "bad", lambda *_: None)
    gateway = MessagingGateway({"allowed_senders": {"discord": ["allowed"]}}, tmp_path / "two.json")
    with pytest.raises(PermissionError, match="Sender"):
        await gateway.process("discord", event, payload, "", lambda *_: None)
