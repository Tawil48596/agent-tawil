"""系统提示词构建器 — 注入环境信息、工具列表、记忆、技能"""

from datetime import datetime


class PromptBuilder:
    """构建发送给 LLM 的系统提示词"""

    BASE_SYSTEM_PROMPT = """你是一个强大的 AI Agent，具备工具调用、记忆、多智能体协作能力。

## 当前时间
{current_time}

## 核心规则
1. 使用可用工具完成任务，不要编造信息
2. 工具调用的参数必须准确、完整
3. 如果工具返回错误，分析原因并尝试其他方式
4. 回答要简洁准确，代码要有注释
5. 涉及文件操作时，先确认再执行危险命令
"""

    def build_system_prompt(
        self,
        session: dict | None = None,
        memories: list[dict] | None = None,
        rag_context: list[dict] | None = None,
        enabled_tools: list[dict] | None = None,
        skill_files: list[str] | None = None,
    ) -> str:
        """构建完整的系统提示词"""
        parts = [
            self.BASE_SYSTEM_PROMPT.format(
                current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        ]

        # 会话信息
        if session:
            parts.append(self._format_session(session))

        # 工具列表
        if enabled_tools:
            parts.append(self._format_tools(enabled_tools))

        # 记忆注入
        if memories:
            parts.append(self._format_memories(memories))

        # RAG 检索结果
        if rag_context:
            parts.append(self._format_rag(rag_context))

        # 技能文件
        if skill_files:
            parts.append(self._format_skills(skill_files))

        return "\n\n".join(parts)

    # ── 各模块格式化 ──

    def _format_session(self, session: dict) -> str:
        lines = ["## 会话信息"]
        lines.append(f"- 会话 ID: {session.get('id', 'unknown')}")
        if session.get("title"):
            lines.append(f"- 标题: {session['title']}")
        lines.append(f"- 来源: {session.get('source', 'web')}")
        return "\n".join(lines)

    def _format_tools(self, tools: list[dict]) -> str:
        lines = ["## 可用工具"]
        for t in tools:
            name = t["name"]
            desc = t.get("description", "无描述")
            dangerous = "⚠️ 危险工具" if t.get("is_dangerous") else ""
            lines.append(f"- **{name}**: {desc} {dangerous}")
        return "\n".join(lines)

    def _format_memories(self, memories: list[dict]) -> str:
        lines = ["## 用户记忆 (长期记忆召回)"]
        for m in memories[:10]:
            mtype = m.get("type", "fact")
            content = m.get("content", "")
            lines.append(f"- [{mtype}] {content}")
        return "\n".join(lines)

    def _format_rag(self, rag_results: list[dict]) -> str:
        lines = ["## 检索到的相关文档"]
        for i, doc in enumerate(rag_results[:5], 1):
            content = doc.get("content", "")
            source = doc.get("source", "unknown")
            # 截断过长内容
            if len(content) > 2000:
                content = content[:2000] + "..."
            lines.append(f"### 文档 {i} (来源: {source})")
            lines.append(content)
        return "\n".join(lines)

    def _format_skills(self, skill_files: list[str]) -> str:
        lines = ["## 加载的技能"]
        for skill in skill_files:
            lines.append(f"- {skill}")
        return "\n".join(lines)
