import pytest

from plugins.resilience.resilience_manager import ResilienceManager


@pytest.mark.asyncio
async def test_degradation_supports_sync_primary_and_async_fallback():
    manager = ResilienceManager()
    calls = []

    def primary():
        calls.append("primary")
        raise RuntimeError("provider unavailable")

    async def fallback():
        calls.append("fallback")
        return "cached"

    result = await manager.call_with_degradation(primary, fallback)

    assert calls == ["primary", "fallback"]
    assert result.degraded is True
    assert result.original_error == "provider unavailable"
