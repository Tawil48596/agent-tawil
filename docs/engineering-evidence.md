# 工程证据与面试说明

本文只记录能够由代码、自动化测试或可复现命令证明的能力。它用于代码审查、技术面试和简历撰写，不把规划中的适配器描述成已完成的生产系统。

## 可验证能力

| 工程能力 | 实现入口 | 验证证据 |
|---|---|---|
| 多 Provider Agent 与工具循环 | `plugins/agent_engine/engine.py`、`model_router.py`、`tool_dispatch.py` | `tests/test_agent/test_engine.py`、`tests/test_evals/test_fake_llm.py` |
| 确定性离线 LLM 评测 | `plugins/evals/fake_llm.py`、`runner.py`、`metrics.py` | 无真实 API Key 即可验证流式响应、工具调用、Token 和工具准确率 |
| 持久评测基线与回归门禁 | `plugins/evals/runner.py`、`scripts/run_offline_eval.py` | 同一测试集跨重启比较通过率；输出 `gate_passed` 并以进程退出码表示结果 |
| 参数、Token 与延迟预算 | `plugins/evals/runner.py`、`metrics.py` | 离线评测同时验证工具参数准确率和资源预算，超预算计入门禁失败 |
| 高风险工具审批 | `plugins/security/tool_approval.py`、`plugins/web_ui/api/tools.py` | `tests/test_tools/test_tool_dispatch.py` 覆盖允许、拒绝、过期和审计路径 |
| 认证与生产启动基线 | `plugins/web_ui/api/auth.py`、`plugins/security/baseline.py` | `tests/test_security/test_auth.py`、`test_production_baseline.py` |
| Web 抓取网络边界 | `plugins/security/network_policy.py`、`plugins/tool_market/builtin/web_search.py` | `tests/test_tools/test_web_extract.py` 覆盖私网、重定向和内容限制 |
| 会话、记忆与 RAG 持久化 | `plugins/conversation/session_store.py`、`plugins/memory/long_term.py`、`plugins/rag_engine/` | 持久化、删除、隔离与重启测试位于 `tests/test_conversation/` 和 `tests/test_rag/` |
| 多智能体恢复与取消 | `plugins/multi_agent/orchestrator.py` | `tests/test_multi_agent/test_orchestrator_persistence.py` |
| 幂等工具重试与检查点回退 | `plugins/checkpoint/execution_ledger.py`、`checkpoint_store.py` | `tests/test_tools/test_tool_dispatch.py`、`tests/test_checkpoint_store.py` |
| 租约与不确定执行恢复 | `plugins/checkpoint/execution_ledger.py`、`plugins/web_ui/api/tools.py` | 活动租约、过期租约、参数冲突和异常后失败关闭测试 |
| 脱敏审计与链路标识 | `plugins/observability/audit.py`、`http_middleware.py` | `tests/test_observability/test_audit.py` 验证递归脱敏和 `trace_id` 传播 |
| 跨重启 Trace 摘要 | `plugins/evals/trace_viewer.py`、`plugins/web_ui/api/evals.py` | 持久化、错误过滤、延迟过滤和输入/输出不落盘测试 |
| 全栈质量门禁 | `.github/workflows/test.yml` | Python 3.11/3.12、覆盖率、前端构建、依赖审查和 CodeQL |
| 浏览器与故障演练 | `scripts/run_browser_smoke.py`、`run_fault_drills.py` | 本地真实浏览器已验证健康、首页和设置；CI 安装 Chromium 后重复执行 |
| 数据版本与备份恢复 | `shared/versioned_store.py`、`data_backup.py` | 旧格式兼容、未知版本拒绝、清单哈希校验、路径穿越拒绝和临时目录恢复测试 |
| 可复现发布证据 | `scripts/run_release_gates.py`、`shared/release_checks.py` | 统一执行测试、评测、演练、备份和构建，凭据扫描不回显值，JSON 结果默认写入忽略目录 |

## 恢复语义

- 会话、消息、Token 用量和缓存命中写入 SQLite，服务重启后可重新加载。
- 多智能体计划采用原子文件写入；重启时将未完成的运行态任务恢复为可继续调度的等待态。
- 取消针对实际后台任务，失败任务可以显式重试；配额和依赖阻塞在调度前检查。
- 中断后的聊天重发复用客户端请求标识，避免重复保存用户消息。
- 成功的工具调用结果按会话、调用 ID、工具和参数摘要持久化；服务重启后重复请求不会再次产生副作用。失败、超时或参数变化仍会重新执行。
- 检查点先写临时文件再原子替换；读取时跳过损坏快照并回退到最近的有效版本。
- 当前不承诺逐 Token 断点续传或分布式 exactly-once。进程在工具执行成功但结果落盘前崩溃时结果仍不确定；跨进程并发写入仍需下游幂等键、条件写入或补偿策略。

## 可复现验证

```powershell
# Python 回归与当前最低覆盖率门禁
python -m pytest --cov-fail-under=35

# 无 API Key、无网络的真实 Agent 工具循环与回归门禁
python scripts/run_offline_eval.py

# 服务启动后执行真实浏览器冒烟；故障演练无需外部服务
python scripts/run_browser_smoke.py
python scripts/run_fault_drills.py

# 创建、校验及恢复本地 data 目录；归档仍可能包含私密会话，不应提交
python -m scripts.backup_data --create backup.zip
python -m scripts.backup_data --verify backup.zip
python -m scripts.backup_data --restore backup.zip --data-root restored-data

# 完整发布候选门禁；证据默认写入 data/release/evidence.json
python -m scripts.run_release_gates

# Web 生产构建
Set-Location web
npm ci
npm run build
```

2026-08-22 的 `v1.3.0` 本地基线为 103 项测试全部通过、总覆盖率 41.63%，Web 生产构建通过。离线 Agent 工具循环连续运行两次均为 100% 通过率、工具准确率 1.0、平均 8 Token，第二次运行正确关联首次基线且回归差值为 0。该数字是当时的验证快照，不是永久性能承诺；推送后的结果仍应以 GitHub Actions 为准。

## 关键取舍

- 使用模块化单体作为组合根，保留 DI、事件总线和插件协议，避免在能力边界尚未稳定时引入分布式复杂度。
- 使用 LiteLLM 统一模型入口，同时在引擎边界注入可脚本化假模型，使工具循环和用量统计能够离线回归。
- 默认本地 SQLite 和内置检索降低启动成本；PostgreSQL、Milvus、Mem0 仅作为待集成能力，不宣称生产可用。
- 审批、SSRF 防护、认证和脱敏审计位于工具与 API 边界，而不是依赖模型自行遵守提示词。

## 简历表述参考

> 设计并实现模块化 AI Agent 平台，支持多模型路由、流式工具调用、会话/记忆/RAG 持久化及多智能体任务恢复；以调用账本和原子检查点实现跨重启幂等重试与损坏快照回退；构建可脚本化离线 LLM 评测，统计 Token、缓存及工具调用准确率；在 API 与工具边界落地认证、审批、SSRF 防护和脱敏审计，并通过 Python/React 全栈 CI、覆盖率门禁和 CodeQL 建立可复现质量基线。

面试时应同时说明边界：这是本地优先的实验平台；多租户授权、托管密钥、外部数据库高可用、负载基准和故障演练仍属于后续生产化工作。
