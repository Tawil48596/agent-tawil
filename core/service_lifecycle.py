"""Ordered shutdown of long-lived runtime resources."""

from typing import Any

import structlog

logger = structlog.get_logger()


async def shutdown_services(
    *,
    plugin_manager: Any,
    task_queue: Any,
    session_store: Any,
    messaging_adapter: Any | None = None,
) -> None:
    """Attempt every shutdown step even when an earlier resource fails."""
    steps = [("plugins", plugin_manager.disable_all), ("task_queue", task_queue.stop)]
    if messaging_adapter is not None and messaging_adapter.is_configured:
        steps.append(("messaging", messaging_adapter.stop))
    for resource, close in steps:
        try:
            await close()
        except Exception:
            logger.exception("Runtime resource shutdown failed", resource=resource)
    try:
        session_store.close()
    except Exception:
        logger.exception("Runtime resource shutdown failed", resource="session_store")
