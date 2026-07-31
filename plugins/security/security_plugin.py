"""Security Plugin — PluginProtocol 实现，串联三级安全网"""

from core.protocols import PluginProtocol


class SecurityPlugin(PluginProtocol):
    """安全插件 — L1 输入 → L2 执行 → L3 输出"""

    @property
    def name(self) -> str:
        return "security"

    @property
    def version(self) -> str:
        return "0.1.1"

    async def on_load(self, container):
        from plugins.security.content_filter import ContentFilter
        from plugins.security.execution_guard import ExecutionGuard
        from plugins.security.output_guard import OutputGuard
        from plugins.security.tool_approval import ToolApproval

        config = container.resolve("config") if hasattr(container, "resolve") else {}
        sec_cfg = config.get("security", {}) if isinstance(config, dict) else {}

        self.content_filter = ContentFilter()
        self.execution_guard = ExecutionGuard(sec_cfg)
        self.output_guard = OutputGuard()
        self.tool_approval = ToolApproval(sec_cfg)

        container.register("ContentFilter", self.content_filter)
        container.register("ExecutionGuard", self.execution_guard)
        container.register("OutputGuard", self.output_guard)
        container.register("ToolApproval", self.tool_approval)

    async def on_enable(self):
        pass

    async def on_disable(self):
        pass

    def get_extensions(self):
        return {
            "content_filter": self.content_filter,
            "execution_guard": self.execution_guard,
            "output_guard": self.output_guard,
            "tool_approval": self.tool_approval,
        }
