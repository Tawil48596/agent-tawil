# AI Agent Platform

通用 AI Agent 平台 — 具备 GitHub 开源项目浏览/调用能力、多智能体协作、工具市场、MCP 网关、RAG 检索增强、长上下文记忆管理。

## 核心能力

- **Agent 引擎** — LLM 推理循环 + 工具调用调度 + 上下文生命周期管理
- **多智能体协作** — 任务委派、并行执行、层级编排、代理间通信
- **MCP 网关** — Model Context Protocol 完整实现，连接 GitHub 等外部工具源
- **RAG 检索增强** — 混合检索 + 重排序 + 查询改写 + 引用追踪
- **工具市场** — 工具注册/发现/安装/版本管理/沙箱执行
- **记忆系统** — 短期上下文窗口 + 长期向量记忆 + 用户画像
- **多平台接入** — Web UI、Telegram、Discord、Slack、REST API
- **插件架构** — 微内核 + 插件，所有功能可替换/扩展

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python 3.11+ / FastAPI / asyncio |
| 前端 | React 18 + TypeScript + Vite + Shadcn/ui |
| 数据库 | SQLite (dev) → PostgreSQL (prod) |
| 向量库 | ChromaDB → pgvector / Milvus |
| 缓存 | Redis |
| LLM | LiteLLM (OpenAI / Anthropic / DeepSeek) |
| 部署 | Docker + docker-compose |

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/Tawil48596/ai-agent-platform.git
cd ai-agent-platform

# 安装依赖
pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 启动服务
python app.py
```

## 项目结构

```
ai-agent-platform/
├── core/              # 微内核 (PluginManager, EventBus, DIContainer)
├── plugins/           # 内置插件 (agent_engine, memory, rag, mcp, ...)
├── extensions/        # 第三方插件
├── web/               # 前端项目 (React + Vite)
├── services/          # Service 层
├── shared/            # 共享类型和工具
├── docs/              # 文档
├── tests/             # 测试
└── app.py             # 入口
```

## 架构文档

详见 [docs/architecture.md](docs/architecture.md) — 包含完整模块设计、API 设计、扩展点、实施路线图。

## 开发路线

| Phase | 内容 | 周期 |
|-------|------|------|
| 1 | 核心骨架 (Agent引擎 + 对话管理 + 记忆基础) | 4-6 周 |
| 2 | GitHub + MCP 网关 | 2-3 周 |
| 3 | 记忆 & RAG 检索引擎 | 3-4 周 |
| 4 | 工具市场 | 2-3 周 |
| 5 | 多智能体协作 | 3-4 周 |
| 6 | 消息平台接入 + 用量统计 | 2-3 周 |
| 7 | Docker 部署 + 性能优化 + 文档 | 2 周 |

**总计：约 18-26 周**

## License

MIT
