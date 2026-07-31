#!/usr/bin/env python
"""
AI Agent Platform — CLI 交互入口

支持:
  - 流式多轮对话
  - /model <name> — 自由切换模型 (per-message / 全局)
  - /models — 列出所有可用模型
  - /task <type> — 切换任务类型 (reasoning/coding/summarization)
  - /tools — 列出已注册工具
  - /help — 查看帮助
  - /clear — 清除对话历史
  - /exit — 退出
"""

import asyncio
import cmd
import os
import sys
from typing import Optional

# 确保项目根在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugins.agent_engine.model_router import ModelRouter, RouteRequest, TaskType
from plugins.agent_engine.engine import AgentEngine
from plugins.agent_engine.tool_dispatch import ToolDispatcher
from app import load_config

# ── 颜色 ──
C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
    "white": "\033[37m",
}


def color(text: str, c: str) -> str:
    return f"{C.get(c, '')}{text}{C['reset']}"


# ── CLI ──

class AgentCLI(cmd.Cmd):
    intro = color("""
╔══════════════════════════════════════════════╗
║          AI Agent Platform  v0.1.1          ║
║  输入 /help 查看命令  |  /models 查看模型    ║
╚══════════════════════════════════════════════╝
""", "cyan")
    prompt = color("\n▸ ", "green")

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.router = ModelRouter(self.config)
        self.tool_dispatcher = ToolDispatcher()
        self.engine = AgentEngine(self.router, self.config.get("agent", {}))

        # 对话状态
        self.history: list[dict] = []
        self.current_model: Optional[str] = None   # None = 使用默认路由
        self.current_task: TaskType = TaskType.REASONING

        # 注册内置工具
        self._register_builtin_tools()

        # 显示默认模型信息
        default = self.router.list_available_models()
        if default:
            print(color(f"  默认模型: {self.router._default_model}", "dim"))
            print(color(f"  可用 Provider: {', '.join(self.router._providers.keys())}", "dim"))
            print(color(f"  输入 /models 查看全部  |  /model <name> 切换模型", "dim"))

    def _register_builtin_tools(self):
        """注册基础内置工具"""
        async def echo(text: str) -> str:
            return text

        async def now() -> str:
            import datetime
            return datetime.datetime.now().isoformat()

        self.tool_dispatcher.register("echo", echo)
        self.tool_dispatcher.register("get_current_time", now)

    # ── 命令处理 ──

    def default(self, line: str):
        """处理用户输入（非 / 开头 = 发送给 Agent）"""
        if line.startswith("/"):
            print(color(f"未知命令: {line}。输入 /help 查看可用命令。", "red"))
            return

        asyncio.run(self._chat(line))

    # ── / 命令 ──

    def do_model(self, arg: str):
        """/model <name> — 切换模型 (e.g. /model claude-sonnet-4)"""
        arg = arg.strip()
        available = self.router.list_available_models()
        all_models = {m["name"]: m for m in self.router.list_models()}

        if not arg:
            # 显示当前模型和可用列表
            current = self.current_model or f"自动路由 (任务: {self.current_task.value})"
            print(color(f"当前模型: {current}", "yellow"))
            print(color("可用模型:", "dim"))
            self._print_model_list()
            return

        if arg == "auto":
            self.current_model = None
            print(color("✓ 已切换为自动路由模式", "green"))
            return

        if arg in all_models:
            info = all_models[arg]
            if info["available"]:
                self.current_model = arg
                print(color(f"✓ 已切换模型为: {arg}", "green"))
                print(color(f"  Provider: {info['provider']} | 上下文: {info['context_length']//1000}K | "
                           f"视觉: {'✅' if info['supports_vision'] else '❌'}", "dim"))
            else:
                print(color(f"✗ 模型 {arg} 存在但 {info['provider']} 未配置 API Key", "red"))
        else:
            print(color(f"✗ 未知模型: {arg}。输入 /models 查看可用模型。", "red"))

    def do_models(self, arg: str):
        """/models — 列出所有模型"""
        self._print_model_list()

    def do_task(self, arg: str):
        """/task <type> — 切换任务类型 (reasoning/coding/summarization)"""
        arg = arg.strip().lower()
        task_map = {
            "reasoning": TaskType.REASONING,
            "coding": TaskType.CODING,
            "summarization": TaskType.SUMMARIZATION,
            "vision": TaskType.VISION,
            "fast": TaskType.FAST,
        }
        if arg in task_map:
            self.current_task = task_map[arg]
            routed = self.router.get_model_for_task(self.current_task)
            print(color(f"✓ 任务类型: {arg} → 默认模型: {routed}", "green"))
        else:
            print(color(f"可用任务类型: {', '.join(task_map.keys())}", "yellow"))

    def do_tools(self, arg: str):
        """/tools — 列出已注册工具"""
        tools = self.tool_dispatcher.list_tools()
        if tools:
            print(color("已注册工具:", "cyan"))
            for t in tools:
                print(f"  🔧 {t}")
        else:
            print(color("(无已注册工具)", "dim"))

    def do_clear(self, arg: str):
        """/clear — 清除对话历史"""
        self.history = []
        print(color("✓ 对话历史已清除", "green"))

    def do_history(self, arg: str):
        """/history — 显示对话历史摘要"""
        if not self.history:
            print(color("(空历史)", "dim"))
            return
        for i, msg in enumerate(self.history):
            role = msg["role"]
            content = msg.get("content", "") or "(tool calls)"
            preview = content[:100] + "..." if len(content) > 100 else content
            role_color = "blue" if role == "user" else "green" if role == "assistant" else "dim"
            print(f"  {i+1}. {color(role, role_color)}: {preview}")

    def do_help(self, arg: str):
        """/help — 显示帮助"""
        print(color("""
命令列表:
  /model [name]   切换模型 (/model claude-sonnet-4, /model auto)
  /models         列出所有可用模型及价格
  /task <type>    切换任务类型 (reasoning/coding/summarization)
  /tools          列出已注册工具
  /clear          清除对话历史
  /history        显示对话历史摘要
  /help           显示此帮助
  /exit           退出

直接输入文本 → 发送给 Agent
Ctrl+C → 中断当前生成
""", "cyan"))

    def do_exit(self, arg: str):
        """/exit — 退出"""
        print(color("\n再见! 👋", "cyan"))
        return True

    do_EOF = do_exit  # Ctrl+D 退出

    # ── 内部 ──

    def _print_model_list(self):
        """打印模型列表"""
        models = self.router.list_models()
        available_names = self.router.list_available_models()

        print(f"\n{'模型名':<25} {'Provider':<12} {'上下文':<10} {'视觉':<6} {'工具':<6} {'输入/$1M':<12} {'输出/$1M':<12} {'状态'}")
        print("-" * 110)

        for m in sorted(models, key=lambda x: x["provider"]):
            available = m["name"] in available_names
            marker = color("●", "green") if available else color("○", "red")
            if self.current_model == m["name"]:
                marker = color("★", "yellow")
            print(
                f"{marker} {m['name']:<23} "
                f"{m['provider']:<12} "
                f"{m['context_length']//1000}K{'':<7} "
                f"{'✅' if m['supports_vision'] else '❌':<6} "
                f"{'✅' if m['supports_tools'] else '❌':<6} "
                f"${m['cost_per_1k_input']*1000:<11.4f} "
                f"${m['cost_per_1k_output']*1000:<11.4f} "
            )
        print()
        print(color("● 可用  ○ 未配置 API Key  ★ 当前选中", "dim"))

    async def _chat(self, user_input: str):
        """发送消息到 Agent 并流式显示"""
        if not user_input.strip():
            return

        # 构建 enabled_tools
        enabled_tools = [
            {"name": "echo", "description": "Echo back the input",
             "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
            {"name": "get_current_time", "description": "Get the current date and time",
             "parameters": {"type": "object", "properties": {}, "required": []}},
        ]

        # 模型信息提示
        route = self.router.route(RouteRequest(
            task_type=self.current_task,
            override_model=self.current_model,
        ))
        model_label = f"{route.model} ({route.provider})" + (" [手动]" if self.current_model else " [自动]")
        print(color(f"\n🤖 Agent [{model_label}]:", "cyan"), end=" ", flush=True)

        try:
            async for event in self.engine.run_stream(
                user_message=user_input,
                history=self.history,
                enabled_tools=enabled_tools,
                override_model=self.current_model,
                task_type=self.current_task,
            ):
                etype = event.get("type")

                if etype == "text":
                    print(event["content"], end="", flush=True)

                elif etype == "compressing":
                    print(color(f"\n  [{event['content']}]", "dim"), end="")

                elif etype == "tool_calls":
                    print(color(f"\n  🔧 调用工具: ", "yellow"), end="")
                    for tc in event.get("calls", []):
                        name = tc.get("function", {}).get("name", "?")
                        print(color(f"{name} ", "yellow"), end="")

                elif etype == "tool_results":
                    for r in event.get("results", []):
                        status = color("✓", "green") if not r.get("error") else color("✗", "red")
                        print(color(f"  {status} {r['name']}: ", "dim"), end="")
                        output = r.get("output", "")[:100]
                        print(color(output, "dim"))

                elif etype == "error":
                    print(color(f"\n  ✗ 错误: {event['message']}", "red"))

                elif etype == "done":
                    stop_reason = event.get("stop_reason", "")
                    if stop_reason == "max_turns":
                        print(color(f"\n  ⚠️ {event.get('content', '')}", "yellow"))
                    print()  # final newline

        except KeyboardInterrupt:
            print(color("\n  ⏹ 已中断", "yellow"))
            return

        # 更新历史
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": "(see above)"})


# ── Entry Point ──

def main():
    try:
        AgentCLI().cmdloop()
    except KeyboardInterrupt:
        print(color("\n再见! 👋", "cyan"))


if __name__ == "__main__":
    main()
