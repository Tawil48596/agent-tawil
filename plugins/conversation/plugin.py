"""Conversation plugin entrypoint backed by the runtime session store."""

from core.protocols import PluginProtocol


class ConversationPlugin(PluginProtocol):
    @property
    def name(self) -> str:
        return "conversation"

    async def on_load(self, container):
        if container is None:
            raise RuntimeError("Conversation plugin requires the runtime container")
        self.session_store = container.resolve("SessionStore")

    def get_extensions(self):
        return {"session_store": self.session_store}


def create_plugin() -> ConversationPlugin:
    return ConversationPlugin()
