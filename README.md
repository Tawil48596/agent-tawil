# AI Agent Platform

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-1.0.0-6c8cff)](CHANGELOG.md)
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
| MCP 与 GitHub | 可用 | 参数校验、审批、超时、刷新及 GitHub 分支/提交/PR 工作流 |
| 多智能体 | 可用 | 持久计划、并行/链式编排、取消、恢复、重试、配额和进度 |
| 工具市场 | 可用（本地） | 工具注册、依赖检查、签名校验、版本隔离和回滚 |
| Telegram / Slack / Discord | 可用（需配置） | 统一 Webhook、签名鉴权、允许列表、去重和会话映射 |
| PostgreSQL / Milvus / Mem0 | 规划中 | 配置或接口已预留，尚未形成可验证的生产实现 |
| 运行时插件化 | 可用（基础） | DI、事件总线、依赖排序、生命周期、故障状态和健康快照 |

## v1.0.0 更新

- GitHub MCP 支持安全的分支、文件提交和 Pull Request 工作流。
- 工具包支持校验、签名、版本隔离安装和回滚。
- 多平台消息统一接入 Agent，并具备鉴权、去重和会话恢复。
- 微内核生命周期、生产安全基线、追踪 ID、指标与就绪检查落地。
- 完整保留 0.1–0.9 的对话、记忆、RAG、工具和多智能体能力。

## v0.4.0 更新

- MCP 工具调用增加参数校验、统一错误、超时、健康检查与动态刷新。
- GitHub 克隆等写入操作需要显式批准，避免模型越权执行。
- 多智能体计划持久化到本地，服务重启后可恢复未完成计划。
- 任务支持后台执行、真实取消、失败重试、配额和准确进度。

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

## 1.x 后续路线

1. 增加 PostgreSQL、Redis、Milvus 和 Mem0 的真实集成环境测试。
2. 增加反向代理、限流、密钥托管和多租户授权参考部署。
3. 扩充 GitHub Actions 端到端测试、故障演练与性能基准。
4. 根据实际使用反馈继续改进 Web UI、无障碍和移动端体验。

详细边界与架构见 [docs/architecture.md](docs/architecture.md)。
配置与生产边界见 [docs/configuration.md](docs/configuration.md)，发布流程见 [docs/release-checklist.md](docs/release-checklist.md)。

## License

MIT
