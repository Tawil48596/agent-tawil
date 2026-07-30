# AI Agent 平台 — 项目架构文档

**目标：** 构建一个具备 GitHub 开源项目浏览/调用能力、多智能体协作、工具市场、MCP 网关、RAG 检索增强、长上下文记忆管理的通用 AI Agent 平台。

**阶段：** 架构设计（本文档）

**参考架构：** Hermes Agent (Nous Research) + LangChain/LlamaIndex 生态

**技术栈：** Python 3.11+, FastAPI, SQLite/PostgreSQL, ChromaDB/Milvus, Redis, asyncio

> **目录结构说明：** 本文档包含两套目录结构——
> - **第三节**为 Phase 1 精简版 (`src/` 单体结构)，快速启动用
> - **第九节 / 第十三节**为最终目标架构 (`core/` + `plugins/` + `extensions/` 插件化结构)
> - 演进策略：Phase 1-3 用单体结构快速迭代，Phase 4 起逐步迁移到插件化架构

---

## 一、系统全景架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                        接入层 (Access Layer)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ Web UI   │  │ Telegram │  │ Discord  │  │  Slack   │  │  API   │ │
│  │ (React)  │  │  (Bot)   │  │  (Bot)   │  │  (Bot)   │  │ (REST) │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘ │
│       └──────────────┴──────────────┴──────────────┴───────────┘     │
│                                  │                                    │
│                       ┌──────────▼──────────┐                        │
│                       │   消息网关 (Gateway)  │                        │
│                       │   路由 · 认证 · 限流   │                        │
│                       └──────────┬──────────┘                        │
└──────────────────────────────────┼───────────────────────────────────┘
                                   │
┌──────────────────────────────────┼───────────────────────────────────┐
│                        核心层 (Core Layer)                             │
│                                   │                                    │
│  ┌────────────────────────────────▼───────────────────────────────┐  │
│  │                    Agent 引擎 (Agent Engine)                     │  │
│  │  ┌─────────┐  ┌──────────┐  ┌───────────┐  ┌───────────────┐  │  │
│  │  │ 推理循环 │  │ 工具调用  │  │ 上下文管理 │  │  技能/指令     │  │  │
│  │  │  Loop   │  │ Dispatch │  │  Context  │  │  加载器       │  │  │
│  │  └─────────┘  └──────────┘  └───────────┘  └───────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   对话管理 (Conversation Manager)               │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │   │
│  │  │ 会话存储 │  │ 消息队列 │  │ 分支/合并 │  │ 标题/摘要    │ │   │
│  │  │ Session  │  │  Queue   │  │ Fork/Merge│  │  Titleizer   │ │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │               记忆系统 (Memory System)                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │   │
│  │  │ 短期记忆 │  │ 长期记忆 │  │ 用户画像 │  │ 上下文压缩   │ │   │
│  │  │ (消息窗) │  │ (向量库) │  │ (Profile)│  │ (Summarizer) │ │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              多智能体协作 (Multi-Agent Orchestration)           │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │   │
│  │  │ 任务委派 │  │ 并行执行 │  │ 结果聚合 │  │ 冲突解决     │ │   │
│  │  │Delegate  │  │ Parallel │  │ Aggregate│  │  Conflict    │ │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼───────────────────────────────────┐
│                       能力层 (Capability Layer)                       │
│                                   │                                    │
│  ┌──────────┐  ┌──────────┐  ┌────▼─────┐  ┌──────────┐  ┌────────┐ │
│  │ 工具市场  │  │GitHub MCP│  │ RAG 引擎 │  │模型路由  │  │使用统计│ │
│  │ Tool     │  │  网关    │  │ 检索增强 │  │Model     │  │Analytics│ │
│  │Marketplace│  │MCP GW   │  │          │  │Router    │  │         │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│                                                                      │
│  ┌──────────┐  ┌──────────┐                                         │
│  │ 安全模块  │  │ 可观测性  │                                         │
│  │ Security │  │Telemetry │                                         │
│  └──────────┘  └──────────┘                                         │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼───────────────────────────────────┐
│                      基础设施层 (Infrastructure)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ LLM 提供 │  │ 向量数据库│  │ 关系数据库│  │  缓存    │  │ 文件   │ │
│  │ Provider │  │ VectorDB │  │   SQL    │  │  Redis   │  │存储    │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 二、模块详细设计

### 2.1 Agent 引擎 (`agent/`)

**核心职责：** LLM 推理循环 + 工具调用调度 + 上下文生命周期管理。

```
agent/
├── engine.py              # 主推理循环 (observe → think → act → observe)
├── prompt_builder.py      # 系统提示词构建 (注入环境信息、工具列表、记忆、技能)
├── tool_dispatch.py       # 工具调用解析与分发 (支持并行执行无依赖调用)
├── context_manager.py     # 上下文窗口监控 & 自动压缩触发
├── compression.py         # 上下文窗口压缩 (滑动窗口 + 关键信息保留)
├── skill_loader.py        # 技能/指令文件加载与注入
├── model_router.py        # 多模型/多Provider路由 (按任务类型选模型)
├── fallback.py            # 模型降级链 (主模型不可用 → 备用)
└── security.py            # 命令审批、代码沙箱、敏感信息过滤
```

**推理循环伪代码：**

```python
class AgentEngine:
    async def run(self, user_message: str, session: Session) -> AgentResponse:
        consecutive_failures = 0
        while self.turns < self.max_turns:
            # 1. 构建上下文 (系统提示词 + 历史消息 + 记忆 + 技能)
            messages = self.prompt_builder.build(session)
            messages.append({"role": "user", "content": user_message})

            # 2. 调用 LLM
            response = await self.model.call(messages, tools=session.enabled_tools)

            # 3. 判断响应类型
            if response.is_text:
                return AgentResponse(text=response.text, stop_reason="complete")
            elif response.is_tool_calls:
                # 无依赖的工具调用并行执行
                results = await self.tool_dispatch.execute_parallel(response.tool_calls)
                if all(r.is_error for r in results):
                    consecutive_failures += 1
                    if consecutive_failures > 3:
                        return AgentResponse(text="工具调用连续失败，请检查配置。",
                                            stop_reason="tool_error")
                else:
                    consecutive_failures = 0
                messages.append({"role": "tool", "content": results})
                # 检查上下文是否超限
                if self.context_manager.needs_compression(messages):
                    messages = await self.compression.compress(messages)
            elif response.is_content_filter:
                return AgentResponse(text="内容被安全策略拦截。",
                                    stop_reason="content_filter")
            self.turns += 1
        return AgentResponse(text="达到最大推理轮次。", stop_reason="max_turns")
```

**关键设计决策：**

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 工具调用格式 | OpenAI Function Calling 兼容 | 几乎所有 LLM 都支持 |
| 工具执行方式 | 无依赖并行，有依赖串行 | 减少延迟 |
| 上下文压缩策略 | 滑动窗口 + LLM 摘要 | 保留近期细节 + 远期摘要 |
| 压缩触发阈值 | 上下文窗口使用率 > 75% | 预留 25% 空间给工具返回 |
| 模型路由 | 按任务类型 (推理/编码/摘要) 自动选择 | 大模型做推理，小模型做摘要降成本 |
| 连续工具失败处理 | >3 次 → 回退纯文本回复 | 避免无限重试 |
| 终止原因追踪 | stop_reason 枚举 (6 种) | 可观测 + 上游决策依据 |

> **与 memory/compression.py 的分工：**
> - `agent/compression.py`：**实时**上下文窗口压缩（滑动窗口 + 增量摘要），在推理过程中触发
> - `memory/compression.py`：**会话结束后**将关键信息提取到长期记忆，离线性

---

### 2.2 对话管理 (`conversation/`)

**核心职责：** 会话 CRUD、消息持久化、分支/合并、标题生成。

```
conversation/
├── session_store.py       # SQLite/PostgreSQL 会话持久化 (SQLite + FTS5 全文搜索)
├── message_store.py       # 消息存储 (按 session_id 分区)
├── session_branch.py      # 会话分支 (从任意对话点 fork)
├── session_merge.py       # 分支合并 (rebase/squash 策略 + 冲突处理)
├── titleizer.py           # LLM 自动生成会话标题
├── export.py              # 导出 JSONL/Markdown
└── search.py              # 全文搜索历史会话
```

**数据模型：**

```sql
-- 会话表
CREATE TABLE sessions (
    id          TEXT PRIMARY KEY,        -- UUID
    title       TEXT,                    -- LLM 自动生成
    source      TEXT DEFAULT 'web',      -- 来源平台
    profile     TEXT,                    -- 所属 Profile
    parent_id   TEXT,                    -- 父会话 (分支来源)
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME,
    metadata    JSON                     -- {tags, model, toolsets, ...}
);

-- 消息表
CREATE TABLE messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    parent_msg_id   INTEGER,              -- 分支点的父消息 ID
    role            TEXT NOT NULL,        -- user / assistant / tool / system
    content         TEXT,
    tool_calls      JSON,                 -- [{name, args, result}]
    token_count     INTEGER,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (parent_msg_id) REFERENCES messages(id)
);

-- FTS5 全文搜索索引
CREATE VIRTUAL TABLE messages_fts USING fts5(
    session_id, role, content, content=messages, content_rowid=id
);
```

**分支模型与合并策略：**

```
session_A ──┬── msg1 ── msg2 ── msg3 (main)
            │
            └── msg2' ── msg3' (branch from msg1)
                          │
                          └── (可合并回 main 或独立发展)

合并策略：
  - rebase:  将分支消息追加到主会话末尾（简单，默认）
  - squash:  压缩分支所有消息为一条 LLM 摘要插入
  - conflict: 分支和主会话同时编辑了同一问题 → LLM 辅助对比 → 人工确认
```

---

### 2.3 记忆系统 (`memory/`)

**核心职责：** 短期上下文窗口管理 + 长期知识持久化 (向量检索) + 用户画像。

```
memory/
├── short_term.py          # 短期记忆 (当前会话消息窗口)
├── long_term.py            # 长期记忆 (ChromaDB/向量库)
├── user_profile.py         # 用户画像 (偏好、环境、习惯)
├── compression.py          # 会话结束后: 长上下文 → 结构化摘要 → 长期记忆
├── consolidation.py        # 会话结束后将关键信息写入长期记忆
├── retrieval.py            # 混合检索 (关键词 + 向量 + 时间衰减)
└── backends/               # 可插拔后端
    ├── builtin.py          # 内置 (SQLite + JSON)
    ├── chromadb.py         # ChromaDB
    ├── milvus.py           # Milvus
    └── mem0.py             # Mem0 集成
```

**记忆生命周期：**

```
当前会话消息 ──→ 短期记忆 (上下文窗口)
     │
     │ 会话结束 / 压缩触发
     ▼
关键信息提取 (LLM 摘要) ──→ 长期记忆 (向量库)
     │
     │ 跨会话
     ▼
检索增强注入 ──→ 下次会话的系统提示词
```

**长期记忆存储结构：**

```python
@dataclass
class MemoryEntry:
    id: str
    content: str           # 记忆内容
    embedding: list[float] # 向量嵌入
    type: str              # fact / preference / event / lesson
    importance: float      # 0.0 - 1.0 重要性评分
    source_session: str    # 来源会话 ID
    created_at: datetime
    last_accessed_at: datetime
    access_count: int
    ttl: Optional[int]     # 过期时间 (秒)
```

**记忆衰减公式：**

```
importance_effective = importance × e^(-λ × days_since_last_access)
λ = 0.01  →  半衰期 ≈ 69 天
importance_effective < 0.05 时触发自动清理
```

**长上下文总结策略：**

| 策略 | 触发条件 | 做法 |
|------|---------|------|
| 滑动窗口 | 始终 | 保留最近 N 轮完整消息 |
| 增量摘要 | 上下文窗口 > 50% | 将更早消息压缩为结构化摘要 |
| 分层摘要 | 上下文窗口 > 75% | 二级摘要 (摘要的摘要) |
| 关键事实提取 | 会话结束 | 提取永久性事实写入长期记忆 |

---

### 2.4 GitHub 集成 & MCP 网关 (`mcp/`)

**核心职责：** 提供 MCP (Model Context Protocol) 服务端 + 客户端，连接 GitHub 及其他外部工具源。

```
mcp/
├── gateway.py             # MCP 网关 (统一入口)
├── server.py              # MCP Server (暴露 Agent 能力给外部)
├── client.py              # MCP Client (连接外部 MCP Server)
├── discovery.py           # 服务发现 (自动检测可用 MCP Server)
├── tool_registry.py       # MCP 工具注册表
├── adapters/              # 平台适配器
│   ├── github.py          # GitHub API MCP 适配器 (内置速率限制)
│   ├── gitlab.py          # GitLab 适配器
│   ├── filesystem.py      # 本地文件系统
│   ├── database.py        # 数据库适配器
│   └── custom.py          # 自定义命令适配器
└── security.py            # MCP 权限控制 (工具白名单/黑名单)
```

**GitHub MCP 适配器设计：**

```python
class GitHubMCPAdapter:
    """将 GitHub REST API 映射为 MCP 工具"""

    def __init__(self, token: str):
        self._rate_limiter = GitHubRateLimiter()  # 追踪 remaining/reset

    TOOLS = {
        "github_search_repos": {
            "description": "搜索 GitHub 仓库",
            "parameters": {
                "query": "string - 搜索关键词",
                "language": "string (optional) - 编程语言过滤",
                "sort": "enum[stars, forks, updated]",
                "limit": "int (default: 10)"
            }
        },
        "github_get_repo": {
            "description": "获取仓库详情 + README",
            "parameters": {"owner": "string", "repo": "string"}
        },
        "github_list_files": {
            "description": "列出仓库文件结构",
            "parameters": {
                "owner": "string", "repo": "string",
                "path": "string (default: '')"
            }
        },
        "github_read_file": {
            "description": "读取仓库中的文件内容",
            "parameters": {
                "owner": "string", "repo": "string",
                "path": "string",
                "ref": "string (optional) - branch/tag/commit"
            }
        },
        "github_list_issues": { ... },
        "github_get_issue": { ... },
        "github_search_code": { ... },
        "github_get_releases": { ... },
        "github_clone_repo": {
            "description": "克隆仓库到本地工作区 (需 OAuth)",
            "parameters": {
                "owner": "string", "repo": "string",
                "branch": "string (optional)"
            }
        },
        "github_execute_action": {
            "description": "在克隆的仓库中执行命令 (需 OAuth + 审批)",
            "parameters": {
                "command": "string - shell 命令",
                "workdir": "string - 工作目录 (仓库路径)"
            },
            "is_dangerous": True
        }
    }
```

**GitHub 速率限制：**

```python
class GitHubRateLimiter:
    """追踪 GitHub API 速率限制 (5000 req/h)"""
    def __init__(self):
        self._remaining = 5000
        self._reset_at: datetime | None = None

    async def acquire(self, cost: int = 1) -> bool:
        if self._remaining < cost and datetime.now() < self._reset_at:
            return False  # 触发等待/降级，通知 Agent
        self._remaining -= cost
        return True

    def update_from_headers(self, headers: dict):
        self._remaining = int(headers.get("X-RateLimit-Remaining", 0))
        self._reset_at = datetime.fromtimestamp(
            int(headers.get("X-RateLimit-Reset", 0))
        )
```

**MCP 网关架构：**

```
                    ┌─────────────┐
                    │  MCP 网关    │
                    │  (Gateway)   │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │GitHub MCP   │ │ File MCP    │ │ 自定义 MCP  │
    │  Server     │ │  Server     │ │  Server     │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │ GitHub API  │ │ 本地文件系统 │ │ 用户命令    │
    └─────────────┘ └─────────────┘ └─────────────┘
```

**MCP 协议交互流程：**

```
Client (Agent)                        Server (MCP Gateway)
     │                                        │
     │── list_tools() ────────────────────────→│
     │←── [{name, description, schema}, ...] ──│
     │                                        │
     │── call_tool("github_search_repos",     │
     │    {query: "LLM agent"}) ──────────────→│
     │                                        │── GitHub API
     │←── {results: [...]} ────────────────────│
     │                                        │
     │── call_tool("github_read_file",        │
     │    {owner: "x", repo: "y", path: "z"})─→│
     │←── {content: "..."} ────────────────────│
```

---

### 2.5 RAG 检索增强 (`rag/`)

**核心职责：** 文档索引 + 检索 + 重排序 + 上下文注入。

```
rag/
├── engine.py              # RAG 主引擎
├── indexer.py             # 文档索引器 (分块 + 嵌入 + 存储, 支持增量索引)
├── retriever.py           # 检索器 (稠密向量 + 稀疏 BM25 混合检索)
├── reranker.py            # 重排序器 (Cross-Encoder 精排)
├── query_rewriter.py      # 查询改写 (HyDE / 多角度查询)
├── chunker/               # 文档分块策略
│   ├── fixed_size.py      # 固定大小分块
│   ├── semantic.py        # 语义分块 (按段落/章节)
│   └── code_aware.py      # 代码感知分块 (AST-aware)
├── embeddings.py          # 嵌入模型管理
├── vector_store.py        # 向量库抽象层
├── knowledge_base.py      # 知识库管理 (创建/更新/删除)
├── citation.py            # 引用追踪 — 检索结果附带 source_id，回复中标注来源
└── sources/               # 文档源适配器
    ├── github.py          # GitHub 仓库文档
    ├── web.py             # 网页抓取
    ├── pdf.py             # PDF 解析
    ├── markdown.py        # Markdown 文件
    └── code.py            # 代码仓库
```

**RAG 流程：**

```
                        ┌──────────┐
                        │ 用户查询  │
                        └────┬─────┘
                             │
                    ┌────────▼────────┐
                    │   查询改写       │
                    │ (HyDE / 多角度)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼────────┐ ┌──▼──────────┐ ┌─▼───────────────┐
     │  稠密向量检索    │ │ BM25 关键词 │ │ 元数据过滤      │
     │ (Embedding)     │ │ 检索        │ │ (source/date)   │
     └────────┬────────┘ └──────┬──────┘ └────────┬────────┘
              │                 │                  │
              └─────────────────┼──────────────────┘
                                │
                     ┌──────────▼──────────┐
                     │   融合 & 去重        │
                     │ (RRF / 加权融合)     │
                     └──────────┬──────────┘
                                │
                     ┌──────────▼──────────┐
                     │   重排序             │
                     │ (Cross-Encoder)      │
                     └──────────┬──────────┘
                                │
                     ┌──────────▼──────────┐
                     │   Top-K + 引用标注   │
                     │   → 注入 LLM 上下文  │
                     └─────────────────────┘
```

**查询改写策略：**

- **HyDE (Hypothetical Document Embeddings)：** 用户查询 → LLM 生成假设文档 → 用假设文档的 embedding 检索（适用于短查询）
- **多角度查询：** 用户查询 → LLM 生成 3 个不同角度的查询 → 并行检索 → RRF 融合
- **查询分解：** 复杂问题 → LLM 拆分为多个子问题 → 逐个子问题检索 → 合并结果

**分块策略对比：**

| 策略 | 适用场景 | 块大小 | 重叠 |
|------|---------|--------|------|
| 固定大小 | 通用文本 | 512 tokens | 10% |
| 语义分块 | 文档/教程 | 按段落/标题 | 上下文窗口 |
| 代码感知 | 代码仓库 | 按函数/类 | import 上下文 |

---

### 2.6 工具市场 (`tool_market/`)

**核心职责：** 工具的注册、发现、安装、版本管理 + 社区贡献。

```
tool_market/
├── registry.py            # 工具注册中心 (工具定义 + Schema + Handler)
├── marketplace.py         # 市场 (浏览/搜索/安装/卸载)
├── versioning.py          # 工具版本管理 (语义版本, pip 风格 ^1.2.3)
├── dependency.py          # 依赖解析
├── sandbox.py             # 工具执行沙箱 (Docker / subprocess 隔离)
├── rating.py              # 评分 & 评论
├── builtin/               # 内置工具集
│   ├── web_search.py      # 网络搜索 (Google/Bing/DuckDuckGo)
│   ├── web_extract.py     # 网页内容提取
│   ├── browser.py         # 浏览器自动化 (Playwright)
│   ├── terminal.py        # Shell 命令执行
│   ├── file_ops.py        # 文件读写/搜索/编辑
│   ├── github_tools.py    # GitHub 操作工具集
│   ├── image_gen.py       # AI 图像生成
│   ├── code_exec.py       # 代码沙箱执行
│   └── vision.py          # 图像分析
└── community/             # 社区贡献工具
    └── ...                # 用户安装的工具
```

**工具注册规范 (Tool Schema)：**

```python
@dataclass
class ToolDefinition:
    name: str               # 唯一标识 (lowercase, hyphens)
    description: str        # LLM 可读的描述
    toolset: str            # 所属工具集
    parameters: dict        # JSON Schema
    handler: Callable       # 执行函数
    check_fn: Callable      # 可用性检查 (API Key 等)
    requires_env: list[str]     # 需要的环境变量
    requires_packages: list[str] # Python 包依赖 ("PyGithub>=2.0")
    requires_system: list[str]   # 系统工具依赖 ("git", "docker")
    version: str            # 语义版本
    author: str
    tags: list[str]         # 分类标签
    is_dangerous: bool      # 是否需要用户审批
```

**工具市场工作流：**

```
开发者 ──→ 创建工具 (按 Schema) ──→ 发布到市场
                                          │
用户 ──→ 浏览/搜索 ──→ 安装 ──→ 工具可用性检查 ──→ Agent 调用
                                          │
                         ┌────────────────┘
                         ▼
                   沙箱隔离执行 ──→ 返回结果
```

**工具安装方式：**
- **内置工具：** 随平台启动自动注册，无需安装
- **市场安装：** 从工具市场下载到 `community/` 目录
- **本地安装：** 用户放置插件到 `extensions/` 目录，自动发现
- **热加载：** 安装/卸载后动态注册/注销，无需重启 Agent

---

### 2.7 多智能体协作 (`multi_agent/`)

**核心职责：** 任务分解 → 子代理委派 → 并行执行 → 结果聚合。

```
multi_agent/
├── orchestrator.py        # 编排器 (任务分解 & 分配)
├── delegation.py          # 委派引擎 (创建子代理、传递上下文)
├── worker.py              # 工作代理 (隔离上下文 + 受限工具集)
├── aggregator.py          # 结果聚合器 (汇总子代理输出)
├── communication.py       # 代理间通信 (消息传递 / 共享黑板)
├── scheduler.py           # 任务调度 (优先级、依赖图)
├── lifecycle.py           # 生命周期管理 (创建/监控/终止/重试)
└── patterns/              # 协作模式
    ├── chain.py           # 链式 (A → B → C)
    ├── parallel.py        # 并行 (A ‖ B ‖ C)
    ├── debate.py          # 辩论 (多代理讨论达成共识)
    ├── hierarchical.py    # 层级 (主编排器 → 子编排器 → 工作者)
    └── swarm.py           # 群体 (动态角色分配)
```

**多智能体协作模式：**

```
模式 1: 并行委派 (Parallel Delegation)
──────────────────────────────────────
  主 Agent
    │
    ├──→ 子 Agent A: 研究前端框架对比
    ├──→ 子 Agent B: 研究后端框架对比
    └──→ 子 Agent C: 研究数据库方案对比
         │
    ┌────┴────┐
    │ 结果聚合 │ → 最终决策
    └─────────┘

模式 2: 链式协作 (Chain)
──────────────────────────
  子 Agent A (需求分析) → 子 Agent B (架构设计) → 子 Agent C (代码实现)


模式 3: 层级编排 (Hierarchical)
──────────────────────────────
  主编排器 (Orchestrator)
    │
    ├──→ 子编排器 A (后端团队)
    │     ├──→ 工作者 A1: API 开发
    │     └──→ 工作者 A2: 数据库迁移
    │
    └──→ 子编排器 B (前端团队)
          ├──→ 工作者 B1: 组件开发
          └──→ 工作者 B2: 样式/测试
```

**子代理隔离设计：**

```python
@dataclass
class SubAgentConfig:
    goal: str               # 任务目标
    context: str            # 传入的上下文 (文件路径、错误信息、约束等)
    toolsets: list[str]     # 允许使用的工具集 (仅子集)
    model: Optional[str]    # 可指定模型
    max_turns: int = 50     # 最大推理轮次
    role: str = "leaf"      # leaf (不能再委派) / orchestrator (可再委派)
    timeout: int = 300      # 超时 (秒)
    retry_attempts: int = 2 # 失败重试次数
    retry_backoff: str = "exponential"  # 退避策略
```

**代理间通信协议：**

```python
@dataclass
class AgentMessage:
    sender_id: str
    receiver_id: str        # 或 "broadcast"
    type: "request" | "response" | "inform" | "error"
    content: dict
    in_reply_to: str | None # 回复的消息 ID
    timestamp: datetime
```

---

### 2.8 使用量统计 (`analytics/`)

**核心职责：** Token 使用统计、成本追踪、用量仪表板。

```
analytics/
├── collector.py           # 数据采集 (每次 LLM 调用记录)
├── aggregator.py          # 聚合器 (小时/天/月汇总)
├── cost_calculator.py     # 成本计算 (按模型定价)
├── dashboard.py           # 仪表板数据 API
├── exporter.py            # 数据导出 (CSV/JSON)
├── alerts.py              # 用量告警 (超预算通知)
└── models.py              # 数据模型
```

**采集指标：**

```python
@dataclass
class UsageRecord:
    timestamp: datetime
    session_id: str
    trace_id: str           # OpenTelemetry 追踪 ID
    provider: str           # openai / anthropic / deepseek
    model: str              # gpt-4o / claude-sonnet-4
    request_type: str       # chat / tool_call / compression / embedding
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float             # 按模型定价计算
    latency_ms: int         # 响应延迟
    tool_calls_count: int   # 本次请求的工具调用次数
```

**仪表板展示：**
- 今日/本周/本月 Token 使用趋势
- 按模型/Provider 的成本分布饼图
- 按会话/用户的用量排名
- 按工具调用频率统计
- 错误率 & 平均延迟

---

### 2.9 安全模块 (`security/`)

**核心职责：** 内容过滤、工具审批、代码沙箱、密钥管理、审计。

```
security/
├── plugin.py              # 安全插件入口
├── content_filter.py      # 输入/输出内容过滤 (NSFW, PII, 注入检测)
├── tool_approval.py       # 危险工具审批流 (webhook / 交互式确认)
├── code_sandbox.py        # 代码执行沙箱 (subprocess / Docker)
├── secret_manager.py      # API Key 安全存储 (AES 加密 + 环境变量)
└── audit_log.py           # 审计日志 (谁在何时调了什么工具)
```

**工具审批流：**

```
Agent 请求危险工具 ──→ is_dangerous=True?
                          │
                    ┌─────▼─────┐
                    │ 审批队列   │
                    │ (pending) │
                    └─────┬─────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         自动批准      交互式确认    Webhook 通知
       (白名单用户)   (UI 弹窗)    (Slack/Telegram)
              │           │           │
              └───────────┼───────────┘
                          ▼
                   执行 / 拒绝 / 超时
```

---

### 2.10 可观测性 (`observability/`)

**核心职责：** 分布式追踪、结构化日志、健康检查。

```
observability/
├── plugin.py
├── tracing.py             # OpenTelemetry 集成 (trace 跨 Agent→MCP→Tool)
├── logging_setup.py       # 结构化 JSON 日志 (按 session_id/trace_id 关联)
├── health_check.py        # 健康检查 (/health: DB, Redis, LLM Provider)
└── metrics.py             # Prometheus 指标暴露
```

**追踪上下文传递：**

```python
# 每个请求生成 trace_id，贯穿整个调用链
@dataclass
class TraceContext:
    trace_id: str           # 全局唯一
    session_id: str
    user_id: str
    parent_span_id: str | None

# 在 Agent → MCP → Tool → LLM 之间透传
```

---

### 2.11 认证授权 (`auth/`)

**核心职责：** API Key 验证 + JWT 签发 + OAuth 集成。

```
auth/
├── plugin.py
├── api_key.py             # API Key 生成/验证/轮换
├── jwt_handler.py         # JWT 签发/刷新/吊销
├── oauth_providers/       # OAuth 提供商
│   ├── github.py
│   └── google.py
└── rbac.py                # 角色权限 (admin / user / viewer)
```

---

## 三、项目目录结构 (Phase 1 精简版)

> 此为 Phase 1 单体结构，快速启动用。Phase 4 起逐步迁移到第九节插件化架构。

```
ai-agent-platform/
├── pyproject.toml              # 项目配置 (uv / poetry)
├── README.md
├── LICENSE
├── .env.example                # 环境变量模板
├── config.yaml                 # 默认配置
│
├── src/
│   ├── agent/                  # Agent 引擎
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── prompt_builder.py
│   │   ├── tool_dispatch.py
│   │   ├── context_manager.py
│   │   ├── compression.py
│   │   ├── skill_loader.py
│   │   ├── model_router.py
│   │   ├── fallback.py
│   │   └── security.py
│   │
│   ├── conversation/           # 对话管理
│   │   ├── __init__.py
│   │   ├── session_store.py
│   │   ├── message_store.py
│   │   ├── session_branch.py
│   │   ├── session_merge.py
│   │   ├── titleizer.py
│   │   ├── export.py
│   │   └── search.py
│   │
│   ├── memory/                 # 记忆系统
│   │   ├── __init__.py
│   │   ├── short_term.py
│   │   ├── long_term.py
│   │   ├── user_profile.py
│   │   ├── compression.py
│   │   ├── consolidation.py
│   │   ├── retrieval.py
│   │   └── backends/
│   │
│   ├── mcp/                    # MCP 网关
│   │   ├── __init__.py
│   │   ├── gateway.py
│   │   ├── server.py
│   │   ├── client.py
│   │   ├── discovery.py
│   │   ├── tool_registry.py
│   │   ├── security.py
│   │   └── adapters/
│   │
│   ├── rag/                    # RAG 检索增强
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── indexer.py
│   │   ├── retriever.py
│   │   ├── reranker.py
│   │   ├── query_rewriter.py
│   │   ├── chunker/
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   ├── knowledge_base.py
│   │   └── sources/
│   │
│   ├── tool_market/            # 工具市场
│   │   ├── __init__.py
│   │   ├── registry.py
│   │   ├── marketplace.py
│   │   ├── versioning.py
│   │   ├── dependency.py
│   │   ├── sandbox.py
│   │   ├── rating.py
│   │   ├── builtin/
│   │   └── community/
│   │
│   ├── multi_agent/            # 多智能体
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   ├── delegation.py
│   │   ├── worker.py
│   │   ├── aggregator.py
│   │   ├── communication.py
│   │   ├── scheduler.py
│   │   ├── lifecycle.py
│   │   └── patterns/
│   │
│   ├── analytics/              # 使用量统计
│   │   ├── __init__.py
│   │   ├── collector.py
│   │   ├── aggregator.py
│   │   ├── cost_calculator.py
│   │   ├── dashboard.py
│   │   ├── exporter.py
│   │   └── alerts.py
│   │
│   ├── security/               # 安全模块
│   │   ├── __init__.py
│   │   ├── content_filter.py
│   │   ├── tool_approval.py
│   │   ├── code_sandbox.py
│   │   └── secret_manager.py
│   │
│   ├── auth/                   # 认证授权
│   │   ├── __init__.py
│   │   ├── api_key.py
│   │   ├── jwt_handler.py
│   │   └── oauth_providers/
│   │
│   ├── observability/          # 可观测性
│   │   ├── __init__.py
│   │   ├── tracing.py
│   │   ├── logging_setup.py
│   │   ├── health_check.py
│   │   └── metrics.py
│   │
│   ├── gateway/                # 消息网关
│   │   ├── __init__.py
│   │   ├── server.py           # FastAPI 主服务
│   │   ├── router.py           # 消息路由
│   │   ├── auth.py             # 认证层
│   │   └── platforms/          # 平台适配器
│   │       ├── web.py          # Web UI
│   │       ├── telegram.py
│   │       ├── discord.py
│   │       ├── slack.py
│   │       └── rest_api.py     # REST API
│   │
│   ├── models/                 # 数据模型
│   │   ├── __init__.py
│   │   ├── session.py
│   │   ├── message.py
│   │   ├── memory.py
│   │   ├── tool.py
│   │   └── agent.py
│   │
│   ├── config/                 # 配置管理
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   ├── schema.py
│   │   └── defaults.py
│   │
│   └── utils/                  # 工具函数
│       ├── __init__.py
│       ├── logging.py
│       ├── async_utils.py
│       ├── json_utils.py
│       └── security.py
│
├── tests/                      # 测试
│   ├── test_agent/
│   ├── test_conversation/
│   ├── test_memory/
│   ├── test_mcp/
│   ├── test_rag/
│   ├── test_tool_market/
│   ├── test_multi_agent/
│   ├── test_security/
│   └── conftest.py
│
├── docs/                       # 文档
│   ├── architecture.md         # 架构文档 (本文档)
│   ├── api/
│   ├── guides/
│   └── examples/
│
├── scripts/                    # 运维脚本
│   ├── setup.sh
│   ├── migrate_db.py
│   └── seed_data.py
│
├── docker/                     # Docker 部署
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
│
└── .github/                    # CI/CD
    ├── workflows/
    │   ├── test.yml
    │   └── deploy.yml
    └── dependabot.yml
```

---

## 四、数据流全景

```
用户输入
   │
   ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│ 消息网关  │───→│ 认证/路由 │───→│ 会话管理  │
└──────────┘    └──────────┘    └────┬─────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
            ┌──────────┐    ┌──────────┐    ┌──────────┐
            │ RAG 检索  │    │ 记忆召回  │    │ 技能注入  │
            │ (相关文档) │    │ (偏好+事实)│   │ (工作流)  │
            └────┬─────┘    └────┬─────┘    └────┬─────┘
                 │               │               │
                 └───────────────┼───────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     系统提示词构建        │
                    │ (RAG上下文 + 记忆 + 技能) │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     Agent 推理循环        │
                    │  LLM ↔ 工具调用          │
                    │  [Tracing span]          │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
      │ GitHub MCP   │  │ 工具市场调用  │  │ 多智能体委派  │
      │ (代码搜索等)  │  │ (搜索/代码等) │  │ (并行子任务)  │
      └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
             │                 │                 │
             └─────────────────┼─────────────────┘
                               │
                  ┌────────────▼────────────┐
                  │     结果 → 上下文注入     │
                  └────────────┬────────────┘
                               │
                  ┌────────────▼────────────┐
                  │     LLM 生成最终回复     │
                  └────────────┬────────────┘
                               │
                  ┌────────────▼────────────┐
                  │     使用量记录 + 记忆更新 │
                  └────────────┬────────────┘
                               │
                  ┌────────────▼────────────┐
                  │     返回用户 (流式)      │
                  └─────────────────────────┘
```

---

## 五、关键设计决策 & 权衡

| 决策 | 选项 A | 选项 B | 建议 | 理由 |
|------|--------|--------|------|------|
| Web 框架 | FastAPI | Flask | **FastAPI** | 原生 async、自动 OpenAPI 文档、WebSocket 支持 |
| 向量数据库 | ChromaDB | Milvus | **先 ChromaDB → 可选 pgvector → Milvus** | 轻量零配置起步，数据量大后迁移 |
| 消息队列 | Redis | RabbitMQ | **Redis** | 同时复用为缓存，降低运维复杂度 |
| 数据库 | SQLite | PostgreSQL | **SQLite 开发，PostgreSQL 生产** | SQLite FTS5 全文搜索好用，但多实例写入需 PG |
| 工具执行隔离 | subprocess | Docker | **subprocess 默认，危险工具 Docker** | subprocess 足够大部分场景 |
| LLM 调用格式 | OpenAI 兼容 | 多 SDK | **OpenAI 兼容 (LiteLLM 优先)** | 几乎所有 Provider 都支持，LiteLLM 已有 100+ 适配 |
| 前端 UI | React+Vite | Next.js | **React+Vite (Vercel AI SDK)** | 轻量、HMR 秒级、AI SDK 原生支持流式 |
| 流式响应 | SSE | WebSocket | **SSE 为主，WS 补充** | SSE 简单够用；WS 用于子代理日志等双向场景 |
| 多智能体通信 | 消息传递 | 共享内存 | **消息传递** | 解耦、可审计、跨进程 |
| LLM Router | LiteLLM | 自研 | **LiteLLM 优先，自研 fallback** | 社区维护、provider 覆盖广 |

---

## 六、实施路线图

### Phase 1: 核心骨架 (4-6 周)

**目标：** 项目初始化 + Agent 引擎核心循环 + 基础对话

| 周次 | 任务 | 交付物 | 验收标准 |
|------|------|--------|---------|
| W1-2 | 项目初始化 | pyproject.toml, 目录结构, CI/CD | `app.py` 启动成功，插件发现/加载正常，CI 全绿 |
| W3-4 | Agent 引擎 | engine.py, prompt_builder.py, model_router.py | CLI 多轮对话正常，支持 OpenAI + Anthropic |
| W5-6 | 对话管理 + 记忆基础 | session_store, message_store, 短期记忆, titleizer | 会话持久化，重启恢复对话 |

**详细清单：**
- [ ] 项目初始化 (pyproject.toml, 目录结构, CI/CD)
- [ ] PluginManager + EventBus + DIContainer 最小实现
- [ ] Agent 引擎核心循环 + 工具调用框架
- [ ] 对话管理 (SQLite session + message store)
- [ ] LLM Provider 接入 (至少 3 个：OpenAI, Anthropic, DeepSeek)
- [ ] 短期记忆 (当前会话消息窗口)
- [ ] 上下文压缩 (滑动窗口 + LLM 摘要)
- [ ] 基础 CLI 入口

### Phase 2: GitHub + MCP (2-3 周)

**目标：** MCP 协议完整实现 + GitHub 集成

- [ ] MCP 协议实现 (Server + Client)
- [ ] GitHub MCP 适配器 (含速率限制)
- [ ] MCP 工具发现 & 注册
- [ ] GitHub OAuth 流程
- [ ] 仓库克隆 + 本地工作区管理

**验收：** Agent 通过 MCP 成功搜索 GitHub、读取仓库文件、克隆仓库

### Phase 3: 记忆 & RAG (3-4 周)

**目标：** 长期记忆 + RAG 检索引擎

- [ ] 长期记忆 (ChromaDB) + 记忆衰减
- [ ] 会话结束自动巩固 (consolidation)
- [ ] RAG 引擎 (索引 + 混合检索 + 重排序)
- [ ] 查询改写 (HyDE + 多角度)
- [ ] 文档源适配器 (GitHub, Web, PDF, Markdown)
- [ ] 引用追踪 (检索结果标注 source_id)

**验收：** 跨会话记忆召回、上传文档后可基于文档问答

### Phase 4: 工具市场 (2-3 周)

**目标：** 工具注册/安装/版本管理

- [ ] 工具注册 Schema + 版本管理
- [ ] 内置工具集 (web_search, terminal, file_ops, code_exec)
- [ ] 工具安装/卸载/热加载
- [ ] 工具依赖解析 (env + packages + system)
- [ ] 危险工具审批流
- [ ] 代码沙箱 (subprocess / Docker)

**验收：** 用户可浏览、安装、卸载工具，Agent 自动调用已安装工具

### Phase 5: 多智能体 (3-4 周)

**目标：** 任务委派 + 并行执行 + 层级编排

- [ ] 子代理委派引擎
- [ ] 并行执行 + 结果聚合
- [ ] 代理间通信 (消息传递)
- [ ] 层级编排模式
- [ ] 子代理错误恢复 (重试 + 退避)
- [ ] 实时子代理日志 (WebSocket)

**验收：** 并发运行 3+ 子代理完成复杂任务，失败自动重试

### Phase 6: 接入 & 统计 (2-3 周)

**目标：** 消息平台接入 + 用量仪表板

- [ ] 消息网关 (Telegram / Discord / Slack)
- [ ] Web UI (React + Vite + Vercel AI SDK)
- [ ] 使用量统计 + 成本追踪 + 预算告警
- [ ] 可观测性 (OpenTelemetry + 结构化日志)
- [ ] 仪表板
- [ ] 认证授权 (API Key + JWT)

**验收：** Telegram Bot 可用，Web UI 完整对话体验，仪表板数据显示正确

### Phase 7: 打磨 & 部署 (2 周)

**目标：** 容器化 + 性能优化 + 文档

- [ ] Docker 化部署 (docker-compose up 一键启动)
- [ ] 性能优化 (TTFT < 2s, 吞吐 > 30 tok/s)
- [ ] API 文档 (OpenAPI/Swagger)
- [ ] 用户指南 + 开发者文档
- [ ] 安全审计 (依赖扫描 + 渗透测试)

**验收：** 一键部署成功，性能指标达标，文档覆盖所有模块

**总计：约 18-26 周 (4.5-6.5 个月，单人开发)**

---

## 七、技术选型总结

| 层级 | 技术选型 |
|------|---------|
| 语言 | Python 3.11+ |
| Web 框架 | FastAPI + Uvicorn |
| 前端 | React 18 + TypeScript + Vite |
| UI 组件库 | Shadcn/ui (Radix + Tailwind) |
| 状态管理 | Zustand |
| HTTP 客户端 | TanStack Query |
| 流式内容 | SSE + Vercel AI SDK |
| 数据库 | SQLite (开发) → PostgreSQL (生产) |
| 向量数据库 | ChromaDB → pgvector → Milvus (按规模升级) |
| 缓存 | Redis |
| LLM Provider | LiteLLM (优先) / 自研 Router |
| MCP 协议 | 自研 (参考 mcp-python SDK) |
| 嵌入模型 | text-embedding-3-small / bge-m3 |
| 重排序 | bge-reranker-v2-m3 |
| 浏览器自动化 | Playwright |
| 代码沙箱 | subprocess / Docker |
| 包管理 | uv (快速替代 pip) |
| 测试 | pytest + pytest-asyncio |
| CI/CD | GitHub Actions |
| 部署 | Docker + docker-compose |
| 可观测性 | OpenTelemetry + Prometheus |
| 日志 | structlog (JSON 格式) |

---

## 八、参考项目

| 项目 | 核心价值 | 可参考模块 |
|------|---------|-----------|
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | 成熟的开源 Agent 框架 | Agent 引擎、工具集、技能系统、多平台网关 |
| [LangChain](https://github.com/langchain-ai/langchain) | Agent 抽象的业界标准 | Chain/Agent/Tool 抽象、RAG 管道 |
| [LlamaIndex](https://github.com/run-llama/llama_index) | 数据索引框架 | RAG 检索增强、文档索引 |
| [CrewAI](https://github.com/crewAIInc/crewAI) | 多智能体协作 | 角色定义、任务委派、流程编排 |
| [Open Interpreter](https://github.com/OpenInterpreter/open-interpreter) | 代码执行 Agent | 代码沙箱、系统交互 |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | MCP 协议实现 | MCP Server/Client 参考 |
| [Dify](https://github.com/langgenius/dify) | LLM 应用平台 | 工具市场 UI、工作流编排 |
| [LiteLLM](https://github.com/BerriAI/litellm) | LLM Provider 统一代理 | 多模型路由、降级、成本追踪 |

---

## 九、模块化插件架构

### 9.1 核心理念：微内核 + 插件

```
┌────────────────────────────────────────────────────────────────┐
│                        微内核 (Core)                            │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ 插件管理器│  │ 事件总线   │  │ 依赖注入  │  │ 配置注册表   │ │
│  │ Plugin   │  │ Event Bus │  │   DI     │  │  Config     │ │
│  │ Manager  │  │           │  │ Container│  │  Registry   │ │
│  └────┬─────┘  └─────┬─────┘  └────┬─────┘  └──────┬───────┘ │
└───────┼──────────────┼─────────────┼────────────────┼─────────┘
        │              │             │                │
   ┌────▼──────────────▼─────────────▼────────────────▼─────────┐
   │                     插件层 (Plugin Layer)                   │
   │                                                            │
   │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐  │
   │  │Agent   │ │Memory  │ │RAG     │ │Tool    │ │Gateway  │  │
   │  │Plugin  │ │Plugin  │ │Plugin  │ │Plugin  │ │Plugin   │  │
   │  └────────┘ └────────┘ └────────┘ └────────┘ └─────────┘  │
   │                                                            │
   │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────────────┐  │
   │  │Security│ │Telemetry│ │Auth   │ │  任何第三方插件     │  │
   │  │Plugin  │ │Plugin  │ │Plugin │ │  (用户自定义)       │  │
   │  └────────┘ └────────┘ └────────┘ └────────────────────┘  │
   └────────────────────────────────────────────────────────────┘
```

每个功能模块都是独立插件，通过统一的 PluginProtocol 接入核心。核心不依赖任何具体插件，插件之间通过事件总线通信，不直接耦合。

### 9.2 插件协议 (PluginProtocol)

```python
from abc import ABC, abstractmethod
from typing import Any

class PluginProtocol(ABC):
    """所有插件必须实现此协议"""

    # ── 元信息 ──
    @property
    @abstractmethod
    def name(self) -> str:
        """唯一标识，如 'rag-engine', 'github-mcp' """
        ...

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def dependencies(self) -> list[str]:
        """依赖的其他插件名"""
        return []

    # ── 生命周期 ──
    async def on_load(self, container: "DIContainer") -> None:
        """插件加载时调用，获取依赖"""

    async def on_enable(self) -> None:
        """插件启用：注册事件监听、启动后台任务"""

    async def on_disable(self) -> None:
        """插件禁用：清理资源、取消监听"""

    # ── 扩展点暴露 ──
    def get_extensions(self) -> dict[str, Any]:
        """暴露给外部的扩展点接口。
        返回 {'extension_name': callable_or_object, ...}
        """
        return {}

    def get_commands(self) -> list["CommandDef"]:
        """暴露 CLI / slash 命令"""
        return []

    def get_api_routes(self) -> list["APIRouteDef"]:
        """暴露 REST API 路由"""
        return []
```

### 9.3 插件管理器

```python
class PluginManager:
    """负责插件的发现、加载、生命周期管理、依赖解析"""

    def __init__(self, plugin_dirs: list[str]):
        self._plugins: dict[str, PluginProtocol] = {}
        self._load_order: list[str] = []       # 拓扑排序后的加载顺序
        self._extensions: dict[str, Any] = {}  # 汇总所有插件暴露的扩展点
        self._event_bus: EventBus

    async def discover(self):
        """扫描 plugin_dirs 下的所有 Python 包，自动发现插件"""

    async def resolve_dependencies(self) -> list[str]:
        """拓扑排序依赖，检测循环依赖，返回加载顺序"""

    async def load_all(self, container: DIContainer):
        """按依赖顺序加载所有插件"""

    async def enable_all(self):
        """按顺序启用所有插件"""

    async def disable_all(self):
        """反向顺序禁用所有插件"""

    def get_extension(self, name: str):
        """按名称获取扩展点接口"""
```

### 9.4 目录结构（插件化终态）

```
ai-agent-platform/
├── core/                          # 微内核（零第三方插件依赖）
│   ├── plugin_manager.py          # 插件管理器
│   ├── event_bus.py               # 事件总线 (发布/订阅)
│   ├── di_container.py            # 依赖注入容器
│   ├── config_registry.py         # 配置注册表
│   └── protocols.py               # 所有抽象协议定义
│
├── plugins/                       # 内置插件（每个都是独立 Python 包）
│   ├── agent_engine/              # Agent 引擎插件
│   │   ├── __init__.py
│   │   ├── plugin.py              # PluginProtocol 实现
│   │   ├── engine.py
│   │   ├── compression.py
│   │   └── setup.py               # 插件依赖声明
│   │
│   ├── conversation/              # 对话管理插件
│   │   ├── plugin.py
│   │   ├── session_store.py
│   │   └── message_store.py
│   │
│   ├── memory/                    # 记忆系统插件
│   │   ├── plugin.py
│   │   ├── short_term.py
│   │   ├── long_term.py
│   │   └── backends/
│   │
│   ├── mcp_gateway/               # MCP 网关插件
│   │   ├── plugin.py
│   │   ├── gateway.py
│   │   └── adapters/
│   │
│   ├── rag_engine/                # RAG 插件
│   │   ├── plugin.py
│   │   ├── indexer.py
│   │   └── retriever.py
│   │
│   ├── tool_market/               # 工具市场插件
│   │   ├── plugin.py
│   │   ├── registry.py
│   │   └── builtin/
│   │
│   ├── multi_agent/               # 多智能体插件
│   │   ├── plugin.py
│   │   ├── orchestrator.py
│   │   └── delegation.py
│   │
│   ├── security/                  # 安全插件
│   │   ├── plugin.py
│   │   ├── content_filter.py
│   │   ├── tool_approval.py
│   │   └── code_sandbox.py
│   │
│   ├── analytics/                 # 统计插件
│   │   ├── plugin.py
│   │   └── collector.py
│   │
│   ├── observability/             # 可观测性插件
│   │   ├── plugin.py
│   │   ├── tracing.py
│   │   └── health_check.py
│   │
│   ├── web_ui/                    # Web UI 插件
│   │   ├── plugin.py
│   │   ├── api/                   # FastAPI 路由
│   │   └── static/                # 前端构建产物
│   │
│   └── messaging/                 # 消息平台插件
│       ├── plugin.py
│       └── platforms/
│
├── extensions/                    # 第三方/用户自定义插件目录
│   └── my_custom_tool/            # 示例：用户自定义工具
│       ├── plugin.py
│       └── tools/
│
├── shared/                        # 共享类型和工具
│   ├── models.py
│   ├── db.py
│   └── utils.py
│
└── app.py                         # 入口：加载核心 → 发现插件 → 启动
```

### 9.5 事件总线设计

插件之间不直接 import，通过事件总线异步通信：

```python
class EventBus:
    """发布/订阅事件总线"""

    async def publish(self, event: "Event"):
        """发布事件到所有订阅者"""

    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件类型"""

    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅"""

# ── 核心事件类型 ──
class Event:
    type: str           # 事件类型标识
    source: str         # 来源插件名
    trace_id: str       # 追踪 ID
    timestamp: datetime
    data: dict          # 事件数据


# 预定义事件（各插件可使用）
AGENT_TURN_START    = "agent.turn.start"     # 推理轮次开始
AGENT_TURN_END      = "agent.turn.end"       # 推理轮次结束
TOOL_CALL_BEFORE    = "tool.call.before"     # 工具调用前 (审批检查)
TOOL_CALL_AFTER     = "tool.call.after"      # 工具调用后 (审计日志)
SESSION_CREATED     = "session.created"      # 新会话创建
SESSION_DELETED     = "session.deleted"      # 会话删除
MEMORY_SAVED        = "memory.saved"         # 记忆写入
MEMORY_RETRIEVED    = "memory.retrieved"     # 记忆召回
RAG_INDEXED         = "rag.indexed"          # 文档索引完成
LLM_REQUEST         = "llm.request"          # LLM 请求（统计用）
LLM_RESPONSE        = "llm.response"         # LLM 响应（统计用）

# 示例：Analytics 插件订阅 LLM 事件来统计用量
# 示例：Memory 插件订阅 SESSION_DELETED 来清理关联记忆
# 示例：Security 插件订阅 TOOL_CALL_BEFORE 来拦截危险调用
```

---

## 十、扩展点设计

系统在多个层面提供标准化的扩展接口，允许第三方插件替换/增强核心行为。

### 10.1 扩展点全景

| 扩展点名称 | 位置 | 替换/增强什么 |
|-----------|------|-------------|
| LLM Provider | agent/engine | 替换底层 LLM 接入 |
| Memory Backend | memory/backends | 替换记忆存储引擎 |
| Vector Store | rag/vector_store | 替换向量数据库 |
| Embedding Model | rag/embeddings | 替换嵌入模型 |
| MCP Adapter | mcp/adapters | 新增外部工具源 |
| Tool Handler | tool_market/ | 新增 Agent 可调用工具 |
| Gateway Platform | gateway/ | 新增消息平台 |
| Auth Provider | auth/ | 替换认证方式 |
| Session Store | conversation/ | 替换会话存储 |
| RAG Chunker | rag/chunker | 新增文档分块策略 |
| RAG Reranker | rag/reranker | 替换重排序模型 |
| Multi-Agent Pattern | multi_agent/ | 新增协作模式 |
| Analytics Backend | analytics/ | 替换统计存储 |
| UI Component | web_ui/ | 新增前端面板/组件 |
| System Prompt | agent/prompt | 增强提示词模板 |
| Secret Manager | security/ | 替换密钥存储 |
| Health Checker | observability/ | 新增健康检查项 |

### 10.2 LLM Provider 扩展点

```python
class LLMProviderProtocol(ABC):
    """接入新的 LLM 提供商"""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs
    ) -> "LLMResponse": ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs
    ) -> AsyncIterator[str]: ...

    @property
    @abstractmethod
    def context_length(self) -> int: ...

    @property
    @abstractmethod
    def supports_vision(self) -> bool: ...
```

注册方式： 创建 `plugins/my_provider/`，实现 `LLMProviderProtocol`，在 `plugin.py` 的 `get_extensions()` 中暴露。

### 10.3 Memory Backend 扩展点

```python
class MemoryBackendProtocol(ABC):
    """接入新的记忆存储引擎"""

    @abstractmethod
    async def save(self, entry: MemoryEntry) -> str: ...

    @abstractmethod
    async def search(
        self, query: str, limit: int = 10, **filters
    ) -> list[MemoryEntry]: ...

    @abstractmethod
    async def get(self, entry_id: str) -> MemoryEntry | None: ...

    @abstractmethod
    async def delete(self, entry_id: str) -> bool: ...

    @abstractmethod
    async def clear(self) -> None: ...
```

内置实现：
- `BuiltinBackend` — SQLite + JSON（默认，零依赖）
- `ChromaBackend` — ChromaDB 向量检索
- `MilvusBackend` — Milvus 大规模检索
- `Mem0Backend` — Mem0 SaaS 集成

### 10.4 Tool 扩展点

```python
class ToolProtocol(ABC):
    """Agent 可调用的工具"""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition: ...

    @abstractmethod
    async def execute(self, **params) -> str:
        """执行工具，返回 JSON 字符串"""
        ...

    @abstractmethod
    async def check_availability(self) -> bool:
        """检查工具是否可用（API Key、依赖等）"""
        ...

# 也支持函数式注册（零代码侵入）
def register_tool(
    name: str,
    description: str,
    parameters: dict,
    handler: Callable,
    *,
    toolset: str = "custom",
    requires_env: list[str] | None = None,
    requires_packages: list[str] | None = None,
    requires_system: list[str] | None = None,
    is_dangerous: bool = False,
):
    """函数式注册工具——第三方插件最常用的扩展方式"""

# 示例
register_tool(
    name="weather_query",
    description="查询指定城市的天气",
    parameters={
        "city": {"type": "string", "description": "城市名"}
    },
    handler=lambda city: json.dumps(get_weather(city)),
    toolset="custom",
)
```

### 10.5 Gateway Platform 扩展点

```python
class PlatformAdapterProtocol(ABC):
    """接入新的消息平台"""

    @abstractmethod
    async def start(self): ...

    @abstractmethod
    async def stop(self): ...

    @abstractmethod
    async def send_message(
        self, chat_id: str, text: str, **options
    ) -> str: ...

    @abstractmethod
    async def on_message(
        self, handler: Callable[[IncomingMessage], None]
    ): ...
```

内置适配器： Telegram, Discord, Slack, REST API, WebSocket, Web UI

### 10.6 依赖注入容器

```python
class DIContainer:
    """轻量级 DI 容器——所有扩展点通过容器获取"""

    def register(self, interface: type, implementation: Any, *, name: str = "default"):
        """注册实现"""

    def register_factory(self, interface: type, factory: Callable, *, name: str = "default"):
        """注册工厂函数（延迟创建）"""

    def resolve(self, interface: type, name: str = "default") -> Any:
        """获取实现"""

    def resolve_all(self, interface: type) -> list[Any]:
        """获取某接口的所有注册实现（用于链式调用）"""

# 使用示例
container = DIContainer()

# 内置注册（core 初始化时）
container.register(LLMProviderProtocol, OpenAIProvider(), name="openai")
container.register(LLMProviderProtocol, AnthropicProvider(), name="anthropic")
container.register(MemoryBackendProtocol, BuiltinBackend(), name="builtin")

# 第三方插件注册（on_load 时）
container.register(MemoryBackendProtocol, ChromaBackend(), name="chromadb")

# 获取具体实现
memory = container.resolve(MemoryBackendProtocol, name="chromadb")

# 获取所有实现（链式调用：尝试 builtin → chromadb → milvus）
all_memories = container.resolve_all(MemoryBackendProtocol)
```

---

## 十一、前端设计

### 11.1 技术选型

| 层 | 技术 | 理由 |
|----|------|------|
| 框架 | **React 18 + TypeScript** | 生态最大、组件库丰富 |
| 构建工具 | **Vite** | 秒级 HMR、ESBuild 打包 |
| 状态管理 | **Zustand** | 轻量 (2KB)、无 boilerplate、TS 友好 |
| UI 组件库 | **Shadcn/ui** (Radix + Tailwind) | 可定制、无 vendor lock-in、暗色主题内置 |
| HTTP 客户端 | **TanStack Query** (React Query) | 缓存/重试/轮询/乐观更新 开箱即用 |
| 路由 | **TanStack Router** | 类型安全的路由 |
| 流式内容 | **Server-Sent Events (SSE) + Vercel AI SDK** | 原生支持 LLM 流式输出 |
| 代码编辑器 | **Monaco Editor** (VS Code 内核) | 代码查看/编辑 |
| 图表 | **Recharts** | React 原生图表 |
| Markdown | **react-markdown + rehype-highlight** | Agent 回复渲染 |
| 文件树 | 自研虚拟滚动树 | 大仓库浏览 |

### 11.2 应用路由结构

```
/                               → 主页 / 新建对话
/chat/:sessionId                → 对话界面（核心页面）
/chat/:sessionId?fork=:msgId    → 从指定消息 fork 分支
/sessions                       → 历史会话列表
/sessions/:sessionId            → 会话详情（只读）
/tools                          → 工具市场（浏览/安装）
/tools/:toolName                → 工具详情
/knowledge                      → 知识库管理
/knowledge/:kbId                → 知识库详情 (文档列表)
/agents                         → 多智能体任务列表
/agents/:taskId                 → 任务详情（子代理状态）
/settings                       → 系统设置
/settings/profile               → 用户偏好
/settings/models                → 模型配置
/settings/memory                → 记忆管理
/analytics                      → 使用量仪表板
```

### 11.3 核心组件树

```
<App>
├── <Layout>
│   ├── <Sidebar>                         # 左侧导航栏
│   │   ├── <Logo />
│   │   ├── <NewChatButton />
│   │   ├── <SessionList>                 # 会话列表（虚拟滚动）
│   │   │   └── <SessionItem /> × N       # 会话项（标题、时间、预览）
│   │   ├── <SidebarNav>                  # 导航链接
│   │   │   ├── <NavItem to="/tools" />
│   │   │   ├── <NavItem to="/knowledge" />
│   │   │   ├── <NavItem to="/agents" />
│   │   │   └── <NavItem to="/analytics" />
│   │   └── <UserMenu />                  # 设置/登出
│   │
│   └── <MainContent>
│       └── <Routes>
│           ├── <ChatView>                # ★核心页面：对话界面
│           │   ├── <ChatHeader>          # 会话标题、模型选择、分支按钮
│           │   ├── <MessageList>         # 消息列表（虚拟滚动）
│           │   │   ├── <UserMessage /> × N
│           │   │   ├── <AssistantMessage /> × N
│           │   │   │   ├── <MarkdownRenderer />
│           │   │   │   ├── <ToolCallCard />     # 工具调用卡片
│           │   │   │   ├── <CodeBlock />        # 代码块（Monaco）
│           │   │   │   └── <ThinkingBlock />    # 思考过程（可折叠）
│           │   │   └── <BranchIndicator />      # 分支标记
│           │   ├── <InputArea>                  # 底部输入区
│           │   │   ├── <MessageInput />         # 多行输入框
│           │   │   ├── <AttachmentBar />        # 附件预览
│           │   │   ├── <ModelSelector />        # 快捷模型切换
│           │   │   └── <SendButton />
│           │   └── <ContextPanel>               # 右侧上下文面板
│           │       ├── <MemoryPreview />        # 已召回的记忆
│           │       ├── <RagSources />           # RAG 检索来源
│           │       └── <ActiveTools />          # 当前可用工具
│           │
│           ├── <ToolMarket>                     # 工具市场
│           │   ├── <SearchBar />
│           │   ├── <CategoryFilter />
│           │   ├── <ToolGrid>
│           │   │   └── <ToolCard /> × N
│           │   └── <InstalledTools />
│           │
│           ├── <KnowledgeBase>                  # 知识库管理
│           │   ├── <KBList />
│           │   ├── <KBCreateWizard />           # 创建向导
│           │   └── <DocumentUploader />         # 拖拽上传
│           │
│           ├── <MultiAgentView>                 # 多智能体监控
│           │   ├── <TaskBoard />                # 任务看板
│           │   ├── <AgentTree />                # 代理层级树
│           │   └── <TaskDetail>
│           │       ├── <AgentLog />             # 子代理日志流
│           │       └── <ResultPreview />
│           │
│           ├── <AnalyticsDashboard>             # 用量仪表板
│           │   ├── <TokenUsageChart />          # Token 趋势图
│           │   ├── <CostBreakdown />            # 成本饼图
│           │   ├── <ModelUsageRank />           # 模型用量排行
│           │   └── <LatencyStats />             # 延迟统计
│           │
│           └── <Settings>                       # 设置页
│               ├── <ProfileSettings />
│               ├── <ModelSettings />
│               └── <MemorySettings />
│
├── <Toaster />                          # 全局通知
├── <CommandPalette />                   # Ctrl+K 命令面板
└── <KeyboardShortcuts />                # 快捷键绑定
```

### 11.4 关键组件设计

**ChatView — 对话界面（核心页面）：**

```
┌──────────────────────────────────────────────────────────────────────┐
│  [≡] 会话标题 ····························· [模型: GPT-4o ▾] [⚙]  │ Header
├───────────────────────────────────┬──────────────────────────────────┤
│                                   │                                  │
│  ┌─────────────────────────────┐ │  ┌─────────────────────────────┐ │
│  │ 用户: 帮我搜索 GitHub 上     │ │  │ 上下文面板                   │ │
│  │ 最好的 LLM Agent 框架        │ │  │                             │ │
│  └─────────────────────────────┘ │  │ 📋 记忆召回:                 │ │
│                                   │  │  · 用户偏好 Python 项目      │ │
│  ┌─────────────────────────────┐ │  │  · 常用 GitHub org: langchain│ │
│  │ 🤖 Agent:                    │ │  │                             │ │
│  │                              │ │  │ 📚 RAG 来源:                 │ │
│  │ 正在搜索 GitHub...           │ │  │  · agent-frameworks.md       │ │
│  │ ┌─────────────────────┐     │ │  │  · comparison-2025.md        │ │
│  │ │ 🔧 github_search     │     │ │  │                             │ │
│  │ │ query: "LLM agent"   │     │ │  │ 🔧 已加载工具:              │ │
│  │ │ results: 15 repos    │     │ │  │  · github_search             │ │
│  │ └─────────────────────┘     │ │  │  · github_read_file          │ │
│  │                              │ │  │  · web_search                │ │
│  │ 找到以下项目：               │ │  │                             │ │
│  │ 1. LangChain (⭐95k)        │ │  └─────────────────────────────┘ │
│  │ 2. CrewAI (⭐22k)           │ │                                  │
│  │ 3. AutoGPT (⭐170k)         │ │                                  │
│  │ ...                          │ │                                  │
│  └─────────────────────────────┘ │                                  │
│                                   │                                  │
├───────────────────────────────────┴──────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 输入你的问题...                                     [📎] [➤] │   │ Input
│  └──────────────────────────────────────────────────────────────┘   │
│  [GPT-4o ▾] [🌐 网络搜索] | 12.5K tokens used | 会话 #abc123      │ Footer
└──────────────────────────────────────────────────────────────────────┘
```

**状态管理 (Zustand)：**

```typescript
// stores/chatStore.ts
interface ChatStore {
  // 会话
  sessions: Session[];
  activeSessionId: string | null;
  messages: Map<string, Message[]>; // sessionId → messages

  // 输入
  inputText: string;
  attachments: Attachment[];
  selectedModel: string;

  // 流式状态
  isStreaming: boolean;
  streamingContent: string;
  streamingToolCalls: ToolCall[];

  // 上下文面板
  contextMemory: MemoryEntry[];
  contextRagSources: RagSource[];
  activeTools: ToolDefinition[];

  // Actions
  createSession: () => Promise<string>;
  switchSession: (id: string) => void;
  sendMessage: (text: string) => Promise<void>;
  stopGeneration: () => void;
  forkSession: (atMessageId: string) => Promise<string>;
  mergeBranch: (branchId: string) => Promise<void>;
}
```

**流式消息处理：**

```typescript
// 使用 Vercel AI SDK 处理 SSE 流
import { useChat } from "ai/react";

function ChatView({ sessionId }: { sessionId: string }) {
  const { messages, input, handleSubmit, isLoading, stop } = useChat({
    api: `/api/v1/chat/sessions/${sessionId}/messages`,
    // 支持工具调用的流式展示
    onToolCall: ({ toolCall }) => {
      // 在消息列表中实时展示工具调用卡片
    },
  });

  return (
    <div className="flex flex-col h-full">
      <MessageList
        messages={messages}
        isStreaming={isLoading}
      />
      <InputArea
        value={input}
        onSubmit={handleSubmit}
        onStop={stop}
        isStreaming={isLoading}
      />
    </div>
  );
}
```

### 11.5 前端工程化

```
web/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── index.html
│
├── public/
│   └── favicon.svg
│
└── src/
    ├── main.tsx                    # 入口
    ├── App.tsx                     # 路由 + Layout
    │
    ├── pages/                      # 页面组件
    │   ├── ChatView.tsx
    │   ├── SessionsPage.tsx
    │   ├── ToolMarket.tsx
    │   ├── KnowledgeBase.tsx
    │   ├── MultiAgentView.tsx
    │   ├── AnalyticsDashboard.tsx
    │   └── Settings.tsx
    │
    ├── components/                 # 通用组件
    │   ├── ui/                     # Shadcn/ui 组件
    │   ├── chat/                   # 对话相关组件
    │   │   ├── MessageList.tsx
    │   │   ├── UserMessage.tsx
    │   │   ├── AssistantMessage.tsx
    │   │   ├── ToolCallCard.tsx
    │   │   ├── CodeBlock.tsx
    │   │   ├── ThinkingBlock.tsx
    │   │   └── InputArea.tsx
    │   ├── layout/                 # 布局组件
    │   │   ├── Sidebar.tsx
    │   │   ├── SessionList.tsx
    │   │   └── ContextPanel.tsx
    │   └── shared/                 # 共享组件
    │       ├── MarkdownRenderer.tsx
    │       ├── FileTree.tsx
    │       └── CommandPalette.tsx
    │
    ├── stores/                     # Zustand 状态
    │   ├── chatStore.ts
    │   ├── sessionStore.ts
    │   ├── toolStore.ts
    │   ├── settingsStore.ts
    │   └── uiStore.ts
    │
    ├── hooks/                      # 自定义 hooks
    │   ├── useSSE.ts               # SSE 流式接收
    │   ├── useMemory.ts            # 记忆查询
    │   └── useKeyboard.ts          # 快捷键
    │
    ├── lib/                        # 工具函数
    │   ├── api.ts                  # API 客户端
    │   ├── utils.ts
    │   └── constants.ts
    │
    └── types/                      # TypeScript 类型
        ├── chat.ts
        ├── session.ts
        ├── tool.ts
        └── agent.ts
```

---

## 十二、后端 API 设计

### 12.1 技术架构

```
                        ┌──────────────────┐
      浏览器 / 客户端 ──→│   Nginx (反向代理) │
                        └────────┬─────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    FastAPI Application   │
                    │                          │
                    │  ┌────────────────────┐ │
                    │  │ Middleware Chain    │ │
                    │  │ CORS → Auth →      │ │
                    │  │ RateLimit → Logger  │ │
                    │  │ → Tracing           │ │
                    │  └────────┬───────────┘ │
                    │           │             │
                    │  ┌────────▼───────────┐ │
                    │  │ API Router          │ │
                    │  │ /api/v1/chat/*      │ │
                    │  │ /api/v1/sessions/*  │ │
                    │  │ /api/v1/tools/*     │ │
                    │  │ /api/v1/rag/*       │ │
                    │  │ /api/v1/agents/*    │ │
                    │  │ /api/v1/analytics/* │ │
                    │  └────────┬───────────┘ │
                    │           │             │
                    │  ┌────────▼───────────┐ │
                    │  │ Service Layer       │ │
                    │  │ ChatService         │ │
                    │  │ SessionService      │ │
                    │  │ MemoryService       │ │
                    │  │ RAGService          │ │
                    │  │ ...                 │ │
                    │  └────────┬───────────┘ │
                    │           │             │
                    │  ┌────────▼───────────┐ │
                    │  │ Plugin Container    │ │
                    │  │ (DI / EventBus)     │ │
                    │  └────────────────────┘ │
                    └─────────────────────────┘
```

### 12.2 中间件链

```python
# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Agent Platform", version="1.0.0")

# 1. CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)

# 2. 请求日志 + Tracing
@app.middleware("http")
async def request_logger(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id", str(uuid4()))
    request.state.trace_id = trace_id
    start = time.time()
    response = await call_next(request)
    logger.info(
        f"{request.method} {request.url.path} {response.status_code}",
        extra={"trace_id": trace_id, "latency_ms": (time.time()-start)*1000}
    )
    response.headers["X-Trace-Id"] = trace_id
    return response

# 3. 认证 (API Key / JWT)
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/v1") and not request.url.path.startswith("/api/v1/health"):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            raise HTTPException(401, "Missing API key")
        request.state.user = await verify_token(token)
    return await call_next(request)

# 4. 限流 (Redis sliding window)
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    key = f"ratelimit:{request.state.user.id}:{request.url.path}"
    if not await rate_limiter.check(key, limit=100, window=60):
        raise HTTPException(429, "Too many requests")
    return await call_next(request)
```

### 12.3 REST API 完整设计

#### 12.3.1 Chat API

```
POST   /api/v1/chat/sessions                   创建新会话
GET    /api/v1/chat/sessions                   会话列表 (分页)
GET    /api/v1/chat/sessions/{id}              会话详情
PATCH  /api/v1/chat/sessions/{id}              更新会话 (标题)
DELETE /api/v1/chat/sessions/{id}              删除会话

POST   /api/v1/chat/sessions/{id}/messages     发送消息 (SSE 流式响应)
GET    /api/v1/chat/sessions/{id}/messages     消息列表 (分页)

POST   /api/v1/chat/sessions/{id}/fork         从指定消息 fork 分支
POST   /api/v1/chat/sessions/{id}/merge        合并分支到主会话

POST   /api/v1/chat/sessions/{id}/compress     手动触发上下文压缩
```

**SSE 流式响应格式：**

```
POST /api/v1/chat/sessions/{id}/messages
Content-Type: application/json
{
  "content": "搜索 GitHub 上的 LLM Agent 框架",
  "attachments": [],
  "model": "gpt-4o"        // 可选：覆盖默认模型
}

→
200 OK
Content-Type: text/event-stream

data: {"type": "thinking", "content": "正在分析用户需求..."}

data: {"type": "tool_call", "name": "github_search_repos", "args": {"query": "LLM agent"}, "status": "pending"}

data: {"type": "tool_call", "name": "github_search_repos", "status": "running"}

data: {"type": "tool_result", "name": "github_search_repos", "result": {...}}

data: {"type": "text", "content": "找到"}

data: {"type": "text", "content": "以下项目："}

data: {"type": "done", "usage": {"prompt_tokens": 1500, "completion_tokens": 300}, "session_id": "abc123"}
```

#### 12.3.2 Session API

```
GET    /api/v1/sessions                       会话列表
GET    /api/v1/sessions/{id}                  会话详情
PATCH  /api/v1/sessions/{id}                  更新标题/标签
DELETE /api/v1/sessions/{id}                  软删除
POST   /api/v1/sessions/search                全文搜索 (FTS5)
GET    /api/v1/sessions/{id}/export           导出 JSONL/Markdown
```

#### 12.3.3 Memory API

```
GET    /api/v1/memory                         用户记忆列表
POST   /api/v1/memory                         手动写入记忆
DELETE /api/v1/memory/{id}                    删除单条记忆
POST   /api/v1/memory/search                  搜索记忆
POST   /api/v1/memory/consolidate             手动触发记忆巩固
PUT    /api/v1/memory/settings                记忆设置 (TTL, 重要性阈值)
```

#### 12.3.4 RAG API

```
POST   /api/v1/rag/knowledge-bases            创建知识库
GET    /api/v1/rag/knowledge-bases            知识库列表
GET    /api/v1/rag/knowledge-bases/{id}       知识库详情
DELETE /api/v1/rag/knowledge-bases/{id}       删除知识库

POST   /api/v1/rag/knowledge-bases/{id}/documents  添加文档 (multipart)
GET    /api/v1/rag/knowledge-bases/{id}/documents  文档列表
DELETE /api/v1/rag/knowledge-bases/{id}/documents/{doc_id}

POST   /api/v1/rag/query                      检索查询 (不经过 Agent)
{
  "query": "...",
  "knowledge_bases": ["kb-1", "kb-2"],
  "top_k": 5
}
```

#### 12.3.5 Tool Market API

```
GET    /api/v1/tools                          工具列表 (内置 + 已安装)
GET    /api/v1/tools/{name}                   工具详情
POST   /api/v1/tools/{name}/install           安装工具
POST   /api/v1/tools/{name}/uninstall         卸载工具
PUT    /api/v1/tools/{name}/settings          工具配置 (API Key 等)
POST   /api/v1/tools/{name}/test              测试工具

GET    /api/v1/tools/marketplace              市场浏览
GET    /api/v1/tools/marketplace/search?q=    市场搜索
```

#### 12.3.6 MCP Gateway API

```
GET    /api/v1/mcp/servers                    MCP Server 列表
POST   /api/v1/mcp/servers                    添加 MCP Server
DELETE /api/v1/mcp/servers/{id}               移除
POST   /api/v1/mcp/servers/{id}/test          测试连接
GET    /api/v1/mcp/servers/{id}/tools         查看暴露的工具
```

#### 12.3.7 Multi-Agent API

```
POST   /api/v1/agents/tasks                   创建多智能体任务
GET    /api/v1/agents/tasks                   任务列表
GET    /api/v1/agents/tasks/{id}              任务详情
POST   /api/v1/agents/tasks/{id}/cancel       取消任务
GET    /api/v1/agents/tasks/{id}/subagents    子代理状态
POST   /api/v1/agents/tasks/{id}/retry       重试失败子任务
```

#### 12.3.8 Analytics API

```
GET    /api/v1/analytics/overview             总览 (今日 Token/成本)
GET    /api/v1/analytics/tokens               Token 使用趋势 (按天)
GET    /api/v1/analytics/costs                成本分布 (按模型)
GET    /api/v1/analytics/latency              延迟统计
GET    /api/v1/analytics/tools                工具使用频率
GET    /api/v1/analytics/export               导出 CSV
```

#### 12.3.9 GitHub Integration API

```
GET    /api/v1/github/search/repos?q=...      搜索仓库
GET    /api/v1/github/repos/{owner}/{repo}    仓库详情
GET    /api/v1/github/repos/{owner}/{repo}/tree  文件树
GET    /api/v1/github/repos/{owner}/{repo}/contents/{path}  读取文件
POST   /api/v1/github/repos/{owner}/{repo}/clone    克隆到工作区
GET    /api/v1/github/workspaces              工作区列表 (已克隆的仓库)
```

#### 12.3.10 通用规范

**错误码规范：**

| 状态码 | 含义 | 响应格式 |
|--------|------|---------|
| 400 | 请求参数错误 | `{"error": "bad_request", "message": "...", "details": [...]}` |
| 401 | 未认证 | `{"error": "unauthorized", "message": "Missing or invalid API key"}` |
| 403 | 无权限 | `{"error": "forbidden", "message": "Insufficient permissions"}` |
| 404 | 资源不存在 | `{"error": "not_found", "message": "Session not found"}` |
| 429 | 限流 | `{"error": "rate_limited", "message": "Too many requests", "retry_after": 30}` |
| 500 | 服务器错误 | `{"error": "internal_error", "message": "...", "trace_id": "..."}` |

### 12.4 WebSocket 端点

```
WS /ws/chat/{session_id}          实时对话 (替代 SSE)
WS /ws/agents/{task_id}           子代理实时日志流
WS /ws/system                     系统通知 (后台任务完成等)
```

**WebSocket 消息协议：**

```json
// → 客户端发送
{"type": "message", "content": "...", "model": "gpt-4o"}

// ← 服务端推送
{"type": "thinking", "content": "..."}
{"type": "tool_call", "name": "...", "args": {...}, "status": "pending|running|done"}
{"type": "text", "content": "..."}
{"type": "done", "usage": {...}, "stop_reason": "complete"}
{"type": "error", "message": "...", "code": "tool_error"}
{"type": "system", "event": "memory_updated|task_completed"}
```

### 12.5 Service 层设计

```python
# services/chat_service.py
class ChatService:
    def __init__(self, container: DIContainer):
        self.agent = container.resolve(AgentEngineProtocol)
        self.sessions = container.resolve(SessionStoreProtocol)
        self.memory = container.resolve(MemoryBackendProtocol)
        self.rag = container.resolve(RAGEngineProtocol)

    async def handle_message(
        self, session_id: str, content: str, model: str | None
    ) -> AsyncIterator[SSEEvent]:
        """处理用户消息，返回 SSE 事件流"""

        session = await self.sessions.get(session_id)

        # 1. 保存用户消息
        await self.sessions.add_message(session_id, role="user", content=content)

        # 2. 召回记忆 & RAG
        memories = await self.memory.search(content, limit=5)
        rag_docs = await self.rag.query(content, session.knowledge_bases)

        # 3. 运行 Agent 推理
        async for event in self.agent.run_stream(
            user_message=content,
            session=session,
            memories=memories,
            rag_context=rag_docs,
            model=model,
        ):
            yield event

        # 4. 后台：更新记忆 + 统计
        await self.event_bus.publish(Event(
            type=SESSION_UPDATED,
            data={"session_id": session_id}
        ))
```

---

## 十三、更新后的目录结构（完整版：插件化终态）

```
ai-agent-platform/
├── core/                          # 微内核
│   ├── __init__.py
│   ├── plugin_manager.py
│   ├── event_bus.py
│   ├── di_container.py
│   ├── config_registry.py
│   └── protocols.py
│
├── plugins/                       # 内置插件
│   ├── agent_engine/
│   ├── conversation/
│   ├── memory/
│   ├── mcp_gateway/
│   ├── rag_engine/
│   ├── tool_market/
│   ├── multi_agent/
│   ├── security/
│   ├── observability/
│   ├── analytics/
│   ├── web_ui/
│   │   ├── plugin.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py
│   │   │   ├── sessions.py
│   │   │   ├── memory.py
│   │   │   ├── rag.py
│   │   │   ├── tools.py
│   │   │   ├── mcp.py
│   │   │   ├── agents.py
│   │   │   ├── analytics.py
│   │   │   └── github.py
│   │   └── static/               # 前端构建产物
│   │
│   └── messaging/
│       ├── plugin.py
│       └── platforms/
│           ├── telegram.py
│           ├── discord.py
│           └── slack.py
│
├── extensions/                    # 第三方插件
├── shared/                        # 共享代码
├── services/                      # Service 层
│   ├── __init__.py
│   ├── chat_service.py
│   ├── session_service.py
│   ├── memory_service.py
│   ├── rag_service.py
│   └── analytics_service.py
│
├── web/                           # ★前端项目
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── pages/
│   │   ├── components/
│   │   ├── stores/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── types/
│   └── ...
│
├── app.py                         # FastAPI 入口
├── config.yaml
├── pyproject.toml
├── docker/
├── tests/
└── docs/
```

---

## 十四、关键性能指标

| 指标 | 目标值 | 测量方式 |
|------|--------|---------|
| 首条 Token 延迟 (TTFT) | < 2s | 发送消息到收到第一个 SSE 事件 |
| 流式吞吐 | > 30 tokens/s | SSE 事件间隔统计 |
| API 并发 | 支持 100+ WebSocket 连接 | 压测 (Locust/k6) |
| 工具调用延迟 | < 500ms (本地), < 5s (远程 API) | per-tool 计时 |
| 记忆检索延迟 | < 200ms (Top-10) | ChromaDB query 计时 |
| RAG 检索延迟 | < 1s (索引+检索+重排) | Pipeline 计时 |
| 前端首屏加载 | < 3s (LCP) | Lighthouse |
| 上下文压缩 | < 3s (100K tokens → 20K) | LLM 摘要耗时 |
| Docker 冷启动 | < 30s | docker-compose up 计时 |
