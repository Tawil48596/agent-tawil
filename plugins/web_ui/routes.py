"""Registration boundary for versioned Web API routers."""

from fastapi import FastAPI


def register_api_routers(app: FastAPI) -> None:
    from plugins.web_ui.api.agents import router as agents_router
    from plugins.web_ui.api.analytics import router as analytics_router
    from plugins.web_ui.api.auth import router as auth_router
    from plugins.web_ui.api.chat import router as chat_router
    from plugins.web_ui.api.evals import router as evals_router
    from plugins.web_ui.api.genui import router as genui_router
    from plugins.web_ui.api.github import router as github_router
    from plugins.web_ui.api.mcp import router as mcp_router
    from plugins.web_ui.api.memory import router as memory_router
    from plugins.web_ui.api.messaging import router as messaging_router
    from plugins.web_ui.api.rag import router as rag_router
    from plugins.web_ui.api.runtime_config import router as runtime_config_router
    from plugins.web_ui.api.tools import router as tools_router

    for router in (
        chat_router,
        mcp_router,
        rag_router,
        tools_router,
        genui_router,
        agents_router,
        auth_router,
        evals_router,
        memory_router,
        analytics_router,
        github_router,
        runtime_config_router,
        messaging_router,
    ):
        app.include_router(router)
