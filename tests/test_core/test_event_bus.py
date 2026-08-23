import pytest

from core.event_bus import Event, EventBus


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
