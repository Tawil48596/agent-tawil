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

import json
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

        # ── Phase 1: Agent 引擎 ──
        from plugins.agent_engine.model_router import ModelRouter
        from plugins.agent_engine.engine import AgentEngine
        from plugins.agent_engine.tool_dispatch import ToolDispatcher

        router = ModelRouter(config)
        tool_dispatcher = ToolDispatcher()
        engine = AgentEngine(router, config.get("agent", {}))

        async def _echo(text: str) -> str:
            return text
        async def _now() -> str:
            import datetime
            return datetime.datetime.now().isoformat()
        tool_dispatcher.register("echo", _echo)
        tool_dispatcher.register("get_current_time", _now)

        app.state.model_router = router
        app.state.tool_dispatcher = tool_dispatcher
        app.state.agent_engine = engine

        available = router.list_available_models()
        logger.info("Agent engine ready",
                     default_model=router._default_model,
                     available_models=len(available))

        # ── Phase 1: 三级安全网 ──
        from plugins.security.content_filter import ContentFilter
        from plugins.security.execution_guard import ExecutionGuard
        from plugins.security.output_guard import OutputGuard
        from plugins.security.tool_approval import ToolApproval

        app.state.content_filter = ContentFilter()
        app.state.execution_guard = ExecutionGuard(config.get("security", {}))
        app.state.output_guard = OutputGuard()
        app.state.tool_approval = ToolApproval(config.get("security", {}))

        logger.info("Security: L1+L2+L3 filters ready")

        # ── Phase 1: 沙箱 ──
        from plugins.security.sandbox import Sandbox, SandboxConfig
        sandbox_cfg = config.get("security", {}).get("sandbox", {})
        sandbox = Sandbox(SandboxConfig(
            mode=sandbox_cfg.get("mode", "subprocess"),
            memory_limit=sandbox_cfg.get("memory_limit", "512m"),
            cpu_limit=sandbox_cfg.get("cpu_limit", 1.0),
            timeout=sandbox_cfg.get("timeout", 30),
            network_enabled=not sandbox_cfg.get("network_disabled", True),
            read_only_root=sandbox_cfg.get("read_only_root", True),
        ))
        app.state.sandbox = sandbox
        logger.info("Sandbox ready", mode=sandbox.mode)

        # ── Phase 1: 分布式锁 ──
        from plugins.locks.lock_manager import LockManager
        redis_url = config.get("redis", {}).get("url", "")
        lock_manager = LockManager(redis_url if redis_url else None)
        app.state.lock_manager = lock_manager
        logger.info("Lock manager ready", mode="redis" if redis_url else "optimistic")

        # ── Phase 1: 降级链 ──
        from plugins.resilience.resilience_manager import ResilienceManager
        app.state.resilience = ResilienceManager(config)
        logger.info("Resilience manager ready (L1/L2/L3 degradation)")

        # ── Phase 1: 任务队列 ──
        from plugins.worker.task_queue import TaskQueue, task_sandbox_exec, task_repo_clone
        task_queue = TaskQueue(max_workers=4)
        task_queue.register_handler("sandbox_exec", task_sandbox_exec)
        task_queue.register_handler("repo_clone", task_repo_clone)
        await task_queue.start()
        app.state.task_queue = task_queue
        logger.info("Task queue ready", workers=4)

        # ── Phase 2: MCP 网关 + GitHub ──
        from plugins.mcp_gateway.gateway import MCPGateway, MCPServerInfo
        from plugins.mcp_gateway.adapters.github import GitHubMCPAdapter

        mcp_gateway = MCPGateway(config)

        # GitHub 适配器
        github_token = config.get("llm", {}).get("providers", {}).get("github", {}).get("api_key", "")
        if not github_token:
            github_token = os.environ.get("GITHUB_TOKEN", "")
        github_adapter = GitHubMCPAdapter(token=github_token)
        if github_adapter.is_configured:
            await mcp_gateway.register_server(
                MCPServerInfo(id="github", name="GitHub", type="github", endpoint="builtin://github"),
                adapter=github_adapter,
            )
            logger.info("MCP: GitHub adapter connected")
        else:
            logger.info("MCP: GitHub adapter registered (no token)")

        # 自动发现其他适配器
        await mcp_gateway.discover()
        app.state.mcp_gateway = mcp_gateway
        mcp_tools = mcp_gateway.list_all_tools()
        logger.info("MCP gateway ready", servers=len(mcp_gateway.list_servers()),
                     tools=len(mcp_tools))

        # ── Phase 2: 对话持久化 ──
        from plugins.conversation.session_store import SessionStore
        db_url = config.get("database", {}).get("url", "sqlite:///data/agent.db")
        db_path = db_url.replace("sqlite:///", "")
        session_store = SessionStore(db_path)
        session_store.connect()
        app.state.session_store = session_store
        logger.info("Session store ready", db=db_path)

        # ── Phase 2: 长期记忆 ──
        from plugins.memory.long_term import LongTermMemory
        from plugins.memory.consolidation import MemoryConsolidator

        long_term = LongTermMemory(config)
        consolidator = MemoryConsolidator(long_term, router)
        app.state.long_term_memory = long_term
        app.state.memory_consolidator = consolidator
        logger.info("Long-term memory ready", backend=long_term._backend)

        # ── Phase 3: RAG 引擎 ──
        from plugins.rag_engine.engine import RAGEngine
        rag_engine = RAGEngine(config)
        app.state.rag_engine = rag_engine

        # 注册工具: expand_history_node (Agent 主动解压缩上下文)
        async def _expand_history_node(node_id: str, depth: int = 1) -> str:
            return json.dumps({"node_id": node_id, "depth": depth, "action": "expanded"})
        tool_dispatcher.register("expand_history_node", _expand_history_node)

        logger.info("RAG engine ready")

        # ── Phase 3: 分层上下文树 ──
        from plugins.context_tree.tree_builder import ContextTree
        context_tree = ContextTree(max_total_tokens=128000)
        context_tree.set_environment(
            "你是一个强大的 AI Agent。使用工具完成任务，保持回答准确。\n"
            "对危险操作必须先获得审批。"
        )
        app.state.context_tree = context_tree
        logger.info("Context tree ready")

        # ── Phase 3: 宏工具 ──
        from plugins.macro_tools.macro_registry import MacroRegistry
        macro_registry = MacroRegistry()
        app.state.macro_registry = macro_registry
        logger.info("Macro tools ready")

        # ── Phase 4: 工具市场 ──
        from plugins.tool_market.registry import ToolRegistry, ToolDef
        from plugins.tool_market.marketplace import Marketplace, MarketplaceEntry
        from plugins.generative_ui.schema_mapper import SchemaMapper

        tool_registry = ToolRegistry()
        marketplace = Marketplace(tool_registry)
        schema_mapper = SchemaMapper()

        app.state.tool_registry = tool_registry
        app.state.marketplace = marketplace
        app.state.schema_mapper = schema_mapper

        # 注册内置工具
        from plugins.tool_market.builtin.web_search import web_search, web_extract
        from plugins.tool_market.builtin.file_ops import file_read, file_write, file_list, file_search
        from plugins.tool_market.builtin.browser import browser_navigate, browser_screenshot

        tool_registry.register(ToolDef(
            name="web_search", description="搜索网络", toolset="builtin",
            parameters={"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}}, "required": ["query"]},
            handler=web_search, tags=["search", "web"], genui_component="SearchResultList",
        ))
        tool_registry.register(ToolDef(
            name="web_extract", description="提取网页内容", toolset="builtin",
            parameters={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
            handler=web_extract, tags=["web", "extract"], genui_component="ArticleViewer",
        ))
        tool_registry.register(ToolDef(
            name="file_read", description="读取文件", toolset="builtin",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            handler=file_read, tags=["file"], genui_component="CodeViewer",
        ))
        tool_registry.register(ToolDef(
            name="file_write", description="写入文件", toolset="builtin",
            parameters={"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
            handler=file_write, is_dangerous=True, tags=["file"], genui_component="ConfirmationCard",
        ))
        tool_registry.register(ToolDef(
            name="file_list", description="列出文件", toolset="builtin",
            parameters={"type": "object", "properties": {"path": {"type": "string", "default": "."}, "recursive": {"type": "boolean", "default": False}}, "required": []},
            handler=file_list, tags=["file"], genui_component="FileTree",
        ))
        tool_registry.register(ToolDef(
            name="file_search", description="搜索文件内容", toolset="builtin",
            parameters={"type": "object", "properties": {"path": {"type": "string"}, "query": {"type": "string"}}, "required": ["path", "query"]},
            handler=file_search, tags=["file", "search"], genui_component="SearchResultList",
        ))
        tool_registry.register(ToolDef(
            name="browser_navigate", description="浏览器导航", toolset="builtin",
            parameters={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
            handler=browser_navigate, tags=["browser"], genui_component="ArticleViewer",
            requires_packages=["playwright"],
        ))
        tool_registry.register(ToolDef(
            name="browser_screenshot", description="浏览器截图", toolset="builtin",
            parameters={"type": "object", "properties": {"url": {"type": "string"}, "selector": {"type": "string", "default": "body"}}, "required": ["url"]},
            handler=browser_screenshot, tags=["browser"], genui_component="StatCard",
            requires_packages=["playwright"],
        ))

        # 种子市场数据
        marketplace.publish(MarketplaceEntry(
            name="web_search", description="DuckDuckGo 搜索", version="0.1.0",
            author="builtin", tags=["search", "builtin"], downloads=1000,
        ))
        marketplace.publish(MarketplaceEntry(
            name="file_read", description="文件读取", version="0.1.0",
            author="builtin", tags=["file", "builtin"], downloads=800,
        ))

        # 同步 tool_dispatcher
        for tool in tool_registry.list_installed():
            if tool.handler:
                tool_dispatcher.register(tool.name, tool.handler)

        logger.info("Tool market ready", builtin=len(tool_registry.list_installed()),
                     market=marketplace.get_stats()["market_size"])

        # ── Phase 4: Generative UI 引擎 ──
        logger.info("Generative UI ready", components=len(schema_mapper.list_components()))

        # ── Phase 5: 多智能体编排 ──
        from plugins.multi_agent.orchestrator import Orchestrator
        from plugins.multi_agent.communication import MessageBus, Blackboard
        from plugins.checkpoint.checkpoint_store import CheckpointStore, RecoveryManager
        from plugins.hitl.hitl_manager import HITLManager

        orchestrator = Orchestrator(agent_engine=engine, max_workers=5)
        message_bus = MessageBus()
        blackboard = Blackboard()
        checkpoint_store = CheckpointStore(config)
        recovery_manager = RecoveryManager(checkpoint_store, blackboard)
        hitl_manager = HITLManager(config)

        app.state.orchestrator = orchestrator
        app.state.message_bus = message_bus
        app.state.blackboard = blackboard
        app.state.checkpoint_store = checkpoint_store
        app.state.recovery_manager = recovery_manager
        app.state.hitl_manager = hitl_manager

        # 注册代理通信工具
        async def _agent_send_message(receiver: str, content: str) -> str:
            from plugins.multi_agent.communication import AgentMessage, MessageType
            msg = AgentMessage(sender_id="main", receiver_id=receiver,
                                type=MessageType.INFORM, content={"text": content})
            await message_bus.send(msg)
            return json.dumps({"sent": True, "receiver": receiver})
        async def _blackboard_write(key: str, value: str) -> str:
            blackboard.write(key, value)
            return json.dumps({"written": True, "key": key})
        async def _blackboard_read(key: str) -> str:
            val = blackboard.read(key)
            return json.dumps({"key": key, "value": val})
        async def _save_checkpoint(task_id: str, stage: str, state: str = "") -> str:
            from plugins.checkpoint.checkpoint_store import Checkpoint
            cp = Checkpoint(task_id=task_id, stage=stage,
                            state={"content": state} if state else {})
            await checkpoint_store.save(cp)
            return json.dumps({"saved": True, "checkpoint_id": cp.id})
        tool_dispatcher.register("agent_send_message", _agent_send_message)
        tool_dispatcher.register("blackboard_write", _blackboard_write)
        tool_dispatcher.register("blackboard_read", _blackboard_read)
        tool_dispatcher.register("save_checkpoint", _save_checkpoint)

        logger.info("Multi-agent orchestration ready",
                     max_workers=5, modes="parallel+chain+hierarchical")
        logger.info("Checkpoint + HITL ready")

        # ── Phase 6+7: 评测 + Trace + 消息平台 ──
        from plugins.evals.runner import EvalRunner
        from plugins.evals.trace_viewer import TraceCollector
        from plugins.messaging.platforms.telegram import TelegramAdapter

        eval_runner = EvalRunner()
        trace_collector = TraceCollector()
        telegram_bot = TelegramAdapter()

        app.state.eval_runner = eval_runner
        app.state.trace_collector = trace_collector
        app.state.telegram_bot = telegram_bot

        if telegram_bot.is_configured:
            await telegram_bot.start()

        logger.info("Evals + Trace + Messaging ready",
                     suites=len(eval_runner.list_suites()),
                     telegram=telegram_bot.is_configured)

        logger.info("All systems ready.",
                     phase1="security+sandbox+lock+degradation+workers",
                     phase2="mcp+github+session_store+long_term_memory",
                     phase3="rag+context_tree+macro_tools",
                     phase4="tool_market+builtin_tools+generative_ui",
                     phase5="orchestrator+blackboard+checkpoint+hitl",
                     phase6="evals+trace_viewer+auth+messaging",
                     mcp_tools=len(mcp_tools),
                     builtin_tools=len(tool_registry.list_installed()))

        yield  # App runs here

        # ── Graceful shutdown ──
        logger.info("Shutting down...")
        await task_queue.stop()
        session_store.close()
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
    from plugins.web_ui.api.mcp import router as mcp_router
    from plugins.web_ui.api.rag import router as rag_router
    from plugins.web_ui.api.tools import router as tools_router
    from plugins.web_ui.api.genui import router as genui_router
    from plugins.web_ui.api.agents import router as agents_router
    from plugins.web_ui.api.auth import router as auth_router
    from plugins.web_ui.api.evals import router as evals_router
    app.include_router(chat_router)
    app.include_router(mcp_router)
    app.include_router(rag_router)
    app.include_router(tools_router)
    app.include_router(genui_router)
    app.include_router(agents_router)
    app.include_router(auth_router)
    app.include_router(evals_router)

    # ── Health check ──

    @app.get("/health")
    async def health(request: Any = None):
        sandbox = getattr(request.app.state, "sandbox", None) if request else None
        resilience = getattr(request.app.state, "resilience", None) if request else None
        return {
            "status": "ok",
            "version": "0.1.0",
            "config_loaded": bool(config),
            "phase1_components": {
                "security": "L1+L2+L3",
                "sandbox": sandbox.mode if sandbox else "not_loaded",
                "resilience": "L1+L2+L3" if resilience else "not_loaded",
                "locks": "available",
                "task_queue": "available",
            },
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
            "degradation_levels": ["L1_model", "L2_tool", "L3_retrieval"],
        }

    # ── Security test endpoints (Phase 1) ──

    @app.post("/api/v1/security/check-input")
    async def check_input(body: dict):
        """L1: 检测用户输入"""
        text = body.get("text", "")
        cf = app.state.content_filter
        result = cf.check_input(text)
        return {
            "passed": result.passed,
            "risk_level": result.risk_level,
            "warnings": result.warnings,
        }

    @app.post("/api/v1/security/check-command")
    async def check_command(body: dict):
        """L2: 检测命令安全性"""
        command = body.get("command", "")
        eg = app.state.execution_guard
        decision = eg.check(command)
        return {
            "allowed": decision.allowed,
            "requires_approval": decision.requires_approval,
            "reason": decision.reason,
            "resource_limits": decision.resource_limits,
        }

    @app.post("/api/v1/security/filter-output")
    async def filter_output(body: dict):
        """L3: 过滤输出内容"""
        text = body.get("text", "")
        og = app.state.output_guard
        result = og.filter(text)
        return {
            "redacted": result.text != text,
            "text": result.text[:500],  # 返回前 500 字符
            "redactions": result.redactions,
            "blocked": result.blocked,
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
