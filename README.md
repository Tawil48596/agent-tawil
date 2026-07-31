# AI Agent Platform

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-0.2.0-6c8cff)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

一个面向本地开发和能力验证的 AI Agent 实验平台，提供 Web 对话、模型路由、工具调用、会话持久化、记忆、RAG、MCP 和多智能体编排等模块。

> 当前版本是实验性版本，不建议直接用于多用户生产环境。下表会明确区分可用能力、实验性能力和规划能力。

## 当前能力

| 能力 | 状态 | 当前范围 |
|---|---|---|
| Web UI 与 REST API | 可用 | 对话、会话历史、设置、知识库、工具和分析页面 |
| Agent 引擎 | 可用 | LiteLLM 模型路由、流式响应、工具调用、上下文管理和跨 Provider 降级 |
| 会话与用量 | 可用 | SQLite 持久化、会话删除、自动标题、Token 与缓存命中统计 |
| 本地长期记忆 | 可用 | 持久化、来源追踪、用户/项目隔离、搜索、编辑和作用域清理 |
| RAG | 可用（本地） | 知识库与文档持久化、混合检索、引用、文档删除和索引清理 |
| MCP 与 GitHub | 实验性 | MCP 服务与工具调用、GitHub 仓库读取和工作区接口 |
| 多智能体 | 实验性 | 任务计划、并行/层级编排、取消、重试、HITL 和检查点接口 |
| 工具市场 | 原型 | 内置工具注册、启用、依赖检查和内存市场 |
| Telegram | 原型 | 基础发送、轮询和消息处理适配器 |
| Discord / Slack | 规划中 | 当前只有基础发送适配器，不具备完整对话闭环 |
| PostgreSQL / Milvus / Mem0 | 规划中 | 配置或接口已预留，尚未形成可验证的生产实现 |
| 运行时插件化 | 规划中 | 已有微内核组件，默认启动仍采用显式模块装配 |

## v0.2.0 更新

- 知识库、文档元数据和内置检索索引可跨服务重启保存。
- 为文档和分块生成稳定 ID，检索结果返回可追踪引用。
- 删除文档时同时清理向量数据和关键词检索索引。
- 长期记忆增加来源、会话、用户、项目、标签和可信度信息。
- 支持按用户和项目搜索、更新及清理长期记忆。
- 知识库页面可查看和删除已持久化文档。

完整记录见 [CHANGELOG.md](CHANGELOG.md)。

## 快速开始

### Windows

1. 双击仓库根目录的 `启动.bat`。
2. 首次运行时，启动器会创建本地环境并安装依赖。
3. 浏览器打开 `http://127.0.0.1:8010`。
4. 在“设置”页面配置模型服务，或提前设置环境变量。

### 命令行

```bash
git clone https://github.com/Tawil48596/agent-tawil.git
cd agent-tawil
python -m pip install -e ".[dev]"
python launcher.py
```

默认启动地址为 `http://127.0.0.1:8010`。也可以使用底层入口：

```bash
python app.py
```

### 模型配置

至少配置一个模型服务：

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
DEEPSEEK_API_KEY
```

本地密钥、数据库、日志、记忆文件和 `.env` 已加入 `.gitignore`，不应提交到 GitHub。

## 项目结构

```text
agent-tawil/
├── core/              # 微内核基础组件
├── plugins/           # Agent、会话、记忆、RAG、MCP 等模块
├── services/          # 服务编排层
├── shared/            # 共享模型、数据库与工具
├── web/               # React + TypeScript 前端
├── tests/             # 自动测试
├── docs/              # 架构文档
├── launcher.py        # 本地启动器
├── 启动.bat           # Windows 双击启动
└── app.py             # FastAPI 底层入口
```

## 开发与验证

```bash
python -m pytest
cd web
npm ci
npm run build
```

## 后续路线

1. 完成记忆与 RAG 的端到端持久化、引用和评估。
2. 打通 MCP/GitHub 的读取、修改、测试和 PR 工作流。
3. 持久化多智能体任务、消息和检查点。
4. 实现可信工具包的下载、校验、隔离安装与回滚。
5. 完成 Telegram、Slack、Discord 的接收、鉴权和会话闭环。
6. 落地插件生命周期、生产认证、PostgreSQL、Redis 和可观测性。

详细边界与架构见 [docs/architecture.md](docs/architecture.md)。

## License

MIT
