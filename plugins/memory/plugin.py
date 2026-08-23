"""Memory plugin entrypoint backed by the composed memory runtime."""

from core.protocols import PluginProtocol


class MemoryPlugin(PluginProtocol):
    @property
    def name(self) -> str:
        return "memory"

    @property
    def dependencies(self) -> list[str]:
        return ["conversation"]

    async def on_load(self, container):
        if container is None:
            raise RuntimeError("Memory plugin requires the runtime container")
        self.long_term = container.resolve("LongTermMemory")
        self.consolidator = container.resolve("MemoryConsolidator")

    def get_extensions(self):
        return {"long_term": self.long_term, "consolidator": self.consolidator}


def create_plugin() -> MemoryPlugin:
    return MemoryPlugin()
