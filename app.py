#!/usr/bin/env python
"""
AI Agent Platform — 应用入口

启动顺序:
  1. 加载配置 (config.yaml + 环境变量)
  2. 初始化日志
  3. 初始化微内核 (PluginManager, EventBus, DIContainer)
  4. 发现 & 加载插件
  5. 启用所有插件
  6. 启动 FastAPI 服务
"""

import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
import uvicorn
import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Config loading ──


def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    """加载 YAML 配置，支持 ${ENV_VAR} 环境变量替换"""
    path = Path(config_path)
    if not path.exists():
        return {}

    with open(path, encoding="utf-8") as f:
        raw = f.read()

    # 替换 ${VAR} 为环境变量值
    import re

    def _env_replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    raw = re.sub(r"\$\{(\w+)\}", _env_replacer, raw)
    return yaml.safe_load(raw) or {}


# ── Logging setup ──


def setup_logging(config: dict[str, Any]) -> None:
    """初始化结构化日志"""
    log_cfg = config.get("logging", {})
    level = log_cfg.get("level", "INFO")
    fmt = log_cfg.get("format", "json")

    if fmt == "json":
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    # Also configure stdlib logging to route through structlog
    import logging
    logging.basicConfig(level=level, format="%(message)s")


logger = structlog.get_logger()


# ── App factory ──


def create_app(config: dict[str, Any]) -> FastAPI:
    server_cfg = config.get("server", {})

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用生命周期管理"""
        logger.info("Starting AI Agent Platform...", version="0.1.0")

        # ── 初始化 Agent 引擎 ──
        from plugins.agent_engine.model_router import ModelRouter
        from plugins.agent_engine.engine import AgentEngine
        from plugins.agent_engine.tool_dispatch import ToolDispatcher

        router = ModelRouter(config)
        tool_dispatcher = ToolDispatcher()
        engine = AgentEngine(router, config.get("agent", {}))

        # 注册内置工具
        async def _echo(text: str) -> str:
            return text
        async def _now() -> str:
            import datetime
            return datetime.datetime.now().isoformat()
        tool_dispatcher.register("echo", _echo)
        tool_dispatcher.register("get_current_time", _now)

        # 挂载到 app.state
        app.state.model_router = router
        app.state.tool_dispatcher = tool_dispatcher
        app.state.agent_engine = engine

        available = router.list_available_models()
        logger.info("Agent engine ready",
                     default_model=router._default_model,
                     available_models=len(available),
                     providers=list(router._providers.keys()))

        # TODO: Phase 1 — init_db, init_redis, discover plugins
        # from shared.db import init_db
        # await init_db(config["database"]["url"])

        logger.info("All systems ready.")

        yield  # App runs here

        # ── Graceful shutdown ──
        logger.info("Shutting down...")
        # await plugin_manager.disable_all()
        # from shared.db import close_db
        # await close_db()
        logger.info("Goodbye.")

    app = FastAPI(
        title="AI Agent Platform",
        version="0.1.0",
        description="通用 AI Agent 平台 — 多智能体协作、MCP 网关、RAG 检索增强",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=server_cfg.get("cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register API routers ──
    from plugins.web_ui.api.chat import router as chat_router
    app.include_router(chat_router)

    # ── Health check ──

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": "0.1.0",
            "config_loaded": bool(config),
        }

    # ── Config inspection (dev only) ──

    @app.get("/api/v1/config/summary")
    async def config_summary():
        """返回配置摘要（不含敏感信息）"""
        return {
            "server": {
                "host": server_cfg.get("host"),
                "port": server_cfg.get("port"),
            },
            "database": {
                "url_type": config.get("database", {}).get("url", "").split("://")[0],
            },
            "llm": {
                "default_model": config.get("llm", {}).get("default_model"),
                "providers": list(config.get("llm", {}).get("providers", {}).keys()),
            },
            "vector_store": {
                "backend": config.get("vector_store", {}).get("backend"),
            },
            "auth_enabled": config.get("auth", {}).get("enabled", False),
            "sandbox_mode": config.get("security", {}).get("sandbox", {}).get("mode"),
        }

    return app


# ── Entry point ──


def main():
    config = load_config()

    setup_logging(config)

    app = create_app(config)

    server_cfg = config.get("server", {})
    host = server_cfg.get("host", "0.0.0.0")
    port = server_cfg.get("port", 8000)
    log_level = config.get("logging", {}).get("level", "info").lower()

    logger.info("Starting server", host=host, port=port)

    uvicorn.run(app, host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    main()
