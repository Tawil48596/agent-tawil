"""Generative UI — 工具 Schema → UI 组件映射引擎"""

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class UIComponent:
    """UI 组件描述"""

    type: str  # 组件类型: RepoCardGrid, CodeViewer, FileTree, ...
    props: dict[str, Any] = field(default_factory=dict)
    title: str = ""
    priority: int = 0  # 渲染优先级
    data_path: str = ""  # JSONPath 到数据字段


class SchemaMapper:
    """工具 Schema → UI 组件自动映射

    规则优先级:
      1. 显式 genui_component (ToolDef 中声明)
      2. Tool name 模式匹配
      3. 返回数据特征推断
    """

    # ── Tool name → 默认组件映射 ──

    NAME_COMPONENT_MAP = {
        # GitHub
        "github_search_repos": "RepoCardGrid",
        "github_get_repo": "RepoDetailCard",
        "github_list_files": "FileTree",
        "github_read_file": "CodeViewer",
        "github_list_issues": "IssueList",
        "github_search_code": "CodeSearchResults",
        "github_get_releases": "ReleaseList",
        "github_clone_repo": "ProgressCard",
        # Web
        "web_search": "SearchResultList",
        "web_extract": "ArticleViewer",
        # File
        "file_read": "CodeViewer",
        "file_list": "FileTree",
        "file_search": "SearchResultList",
        "file_write": "ConfirmationCard",
        # Code
        "code_exec": "TerminalOutput",
        "terminal": "TerminalOutput",
        # Data
        "data_analysis": "ChartRenderer",
        "get_current_time": "StatCard",
        # Error
        "_error": "ErrorCard",
    }

    # ── 数据特征 → 组件推断 ──

    DATA_PATTERNS = [
        # (特征检查函数, 组件类型)
        (lambda d: isinstance(d, dict) and "repos" in d, "RepoCardGrid"),
        (lambda d: isinstance(d, dict) and "issues" in d, "IssueList"),
        (
            lambda d: (
                isinstance(d, dict)
                and "items" in d
                and all(
                    isinstance(i, dict) and "type" in i and i["type"] in ("file", "dir")
                    for i in d.get("items", [])[:3]
                )
            ),
            "FileTree",
        ),
        (lambda d: isinstance(d, dict) and "stdout" in d, "TerminalOutput"),
        (lambda d: isinstance(d, dict) and "results" in d, "SearchResultList"),
        (
            lambda d: isinstance(d, dict) and "content" in d and len(d.get("content", "")) > 500,
            "CodeViewer",
        ),
        (lambda d: isinstance(d, dict) and "diff" in d, "DiffView"),
        (lambda d: isinstance(d, dict) and "chart" in d, "ChartRenderer"),
        (lambda d: isinstance(d, dict) and "progress" in d, "ProgressCard"),
    ]

    def map(self, tool_name: str, tool_data: Any, explicit_component: str = "") -> UIComponent:
        """将工具结果映射为 UI 组件"""
        # 1. 显式指定
        if explicit_component:
            return UIComponent(type=explicit_component, title=tool_name, data_path="")

        # 2. Tool name 匹配
        if tool_name in self.NAME_COMPONENT_MAP:
            return UIComponent(
                type=self.NAME_COMPONENT_MAP[tool_name], title=tool_name, data_path=""
            )

        # 3. 数据特征推断
        for check_fn, component_type in self.DATA_PATTERNS:
            try:
                if isinstance(tool_data, str):
                    import json

                    data = json.loads(tool_data)
                else:
                    data = tool_data
                if check_fn(data):
                    return UIComponent(type=component_type, title=tool_name, data_path="")
            except Exception:
                continue

        # 4. 默认: 文本展示
        is_code = isinstance(tool_data, str) and (
            "def " in tool_data or "import " in tool_data or "{" in tool_data
        )
        if is_code:
            return UIComponent(type="CodeViewer", title=tool_name)
        return UIComponent(type="MarkdownCard", title=tool_name)

    def list_components(self) -> list[dict]:
        """列出所有可用组件"""
        return [
            {
                "type": "RepoCardGrid",
                "description": "仓库卡片网格",
                "props": ["repos", "sortBy", "viewOptions"],
            },
            {
                "type": "RepoDetailCard",
                "description": "仓库详情卡片",
                "props": ["repo", "showReadme"],
            },
            {
                "type": "FileTree",
                "description": "可点击文件树",
                "props": ["items", "onFileClick", "showIcons"],
            },
            {
                "type": "CodeViewer",
                "description": "代码查看器 (Monaco)",
                "props": ["content", "language", "readOnly"],
            },
            {
                "type": "DiffView",
                "description": "代码差异视图",
                "props": ["oldContent", "newContent", "language"],
            },
            {"type": "IssueList", "description": "Issue 列表", "props": ["issues", "statusFilter"]},
            {"type": "ReleaseList", "description": "Release 列表", "props": ["releases"]},
            {
                "type": "SearchResultList",
                "description": "搜索结果列表",
                "props": ["results", "total", "query"],
            },
            {
                "type": "ArticleViewer",
                "description": "文章/文档查看器",
                "props": ["title", "content", "url"],
            },
            {
                "type": "TerminalOutput",
                "description": "终端输出",
                "props": ["stdout", "stderr", "exitCode"],
            },
            {
                "type": "ChartRenderer",
                "description": "数据图表",
                "props": ["data", "chartType", "xAxis", "yAxis"],
            },
            {
                "type": "StatCard",
                "description": "统计卡片",
                "props": ["value", "label", "trend", "icon"],
            },
            {
                "type": "ProgressCard",
                "description": "进度卡片",
                "props": ["title", "progress", "steps", "currentStep"],
            },
            {
                "type": "ConfirmationCard",
                "description": "确认卡片",
                "props": ["message", "onConfirm", "onCancel"],
            },
            {
                "type": "ErrorCard",
                "description": "错误卡片",
                "props": ["message", "code", "suggestion"],
            },
            {"type": "MarkdownCard", "description": "Markdown 渲染", "props": ["content"]},
        ]

    def get_tool_ui_schema(self, tool_name: str) -> dict:
        """为工具生成前端 UI schema"""
        component = self.NAME_COMPONENT_MAP.get(tool_name, "MarkdownCard")
        return {
            "tool": tool_name,
            "component": component,
            "supported_components": [c["type"] for c in self.list_components()[:5]],
        }
