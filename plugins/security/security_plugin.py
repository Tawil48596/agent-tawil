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
        if container is None:
            raise RuntimeError("Security plugin requires the runtime container")
        self.content_filter = container.resolve("ContentFilter")
        self.execution_guard = container.resolve("ExecutionGuard")
        self.output_guard = container.resolve("OutputGuard")
        self.tool_approval = container.resolve("ToolApproval")

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
