"""Agent Engine Plugin — PluginProtocol 实现"""

from core.protocols import PluginProtocol


class AgentEnginePlugin(PluginProtocol):
    """Agent 引擎插件"""

    @property
    def name(self) -> str:
        return "agent-engine"

    @property
    def version(self) -> str:
        return "0.1.1"

    @property
    def dependencies(self) -> list[str]:
        return ["conversation", "memory"]

    async def on_load(self, container):
        if container is None:
            raise RuntimeError("Agent engine plugin requires the runtime container")
        self.router = container.resolve("ModelRouter")
        self.engine = container.resolve("AgentEngine")
        self.dispatcher = container.resolve("ToolDispatcher")

    async def on_enable(self):
        pass

    async def on_disable(self):
        pass

    def get_extensions(self):
        return {
            "agent_engine": self.engine,
            "model_router": self.router,
            "tool_dispatcher": self.dispatcher,
        }


def create_plugin() -> AgentEnginePlugin:
    return AgentEnginePlugin()
