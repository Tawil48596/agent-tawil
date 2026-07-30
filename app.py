#!/usr/bin/env python
"""
AI Agent Platform — 应用入口

启动顺序:
  1. 加载配置 (config.yaml + 环境变量)
  2. 初始化微内核 (PluginManager, EventBus, DIContainer)
  3. 发现 & 加载插件
  4. 启用所有插件
  5. 启动 FastAPI 服务
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Agent Platform",
        version="0.1.0",
        description="通用 AI Agent 平台 — 多智能体协作、MCP 网关、RAG 检索增强",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()


def main():
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
