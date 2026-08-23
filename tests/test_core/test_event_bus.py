import pytest

from core.event_bus import SESSION_UPDATED, Event, EventBus


def test_session_update_event_name_is_stable():
    assert SESSION_UPDATED == "session.updated"


@pytest.mark.asyncio
async def test_event_bus_runs_sync_and_async_subscribers():
    bus = EventBus()
    received = []

    def sync_handler(event):
        received.append(("sync", event.data["value"]))

    async def async_handler(event):
        received.append(("async", event.data["value"]))

    bus.subscribe("demo", sync_handler)
    bus.subscribe("demo", async_handler)
    await bus.publish(Event(type="demo", source="test", data={"value": 7}))

    assert received == [("sync", 7), ("async", 7)]
