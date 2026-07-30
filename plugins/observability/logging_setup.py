"""结构化日志设置"""

import logging
import sys
from typing import Any


def setup_logging(config: dict = None, level: str = "INFO", fmt: str = "json") -> None:
    cfg = config or {}
    log_level = cfg.get("logging", {}).get("level", level) if isinstance(cfg, dict) else level
    log_fmt = cfg.get("logging", {}).get("format", fmt) if isinstance(cfg, dict) else fmt

    try:
        import structlog
        if log_fmt == "json":
            structlog.configure(
                processors=[structlog.stdlib.filter_by_level, structlog.stdlib.add_log_level,
                            structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()],
                wrapper_class=structlog.stdlib.BoundLogger, logger_factory=structlog.stdlib.LoggerFactory(),
            )
        else:
            structlog.configure(
                processors=[structlog.stdlib.filter_by_level, structlog.stdlib.add_log_level,
                            structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
                wrapper_class=structlog.stdlib.BoundLogger, logger_factory=structlog.stdlib.LoggerFactory(),
            )
    except ImportError:
        logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(message)s")
