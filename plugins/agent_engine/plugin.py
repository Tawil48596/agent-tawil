"""Agent Engine Plugin — PluginProtocol 实现"""

from core.protocols import PluginProtocol


class AgentEnginePlugin(PluginProtocol):
    """Agent 引擎插件"""

    @property
    def name(self) -> str:
        return "agent-engine"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def dependencies(self) -> list[str]:
        return ["conversation", "memory"]

    async def on_load(self, container):
        from plugins.agent_engine.model_router import ModelRouter
        from plugins.agent_engine.engine import AgentEngine

        config = container.resolve("config")
        self.router = ModelRouter(config)
        self.engine = AgentEngine(self.router, config.get("agent", {}))

        container.register("ModelRouter", self.router)
        container.register("AgentEngine", self.engine)

    async def on_enable(self):
        pass

    async def on_disable(self):
        pass

    def get_extensions(self):
        return {
            "agent_engine": self.engine,
            "model_router": self.router,
        }
