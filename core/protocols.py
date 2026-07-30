"""协议定义 — 所有插件必须实现的抽象接口"""

from abc import ABC, abstractmethod
from typing import Any, Callable, AsyncIterator


class PluginProtocol(ABC):
    """所有插件必须实现此协议"""

    @property
    @abstractmethod
    def name(self) -> str:
        """唯一标识，如 'rag-engine', 'github-mcp'"""
        ...

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def dependencies(self) -> list[str]:
        """依赖的其他插件名"""
        return []

    async def on_load(self, container: "DIContainer") -> None:
        """插件加载时调用，获取依赖"""
        pass

    async def on_enable(self) -> None:
        """插件启用：注册事件监听、启动后台任务"""
        pass

    async def on_disable(self) -> None:
        """插件禁用：清理资源、取消监听"""
        pass

    def get_extensions(self) -> dict[str, Any]:
        """暴露给外部的扩展点接口"""
        return {}

    def get_commands(self) -> list[dict]:
        """暴露 CLI / slash 命令"""
        return []

    def get_api_routes(self) -> list[dict]:
        """暴露 REST API 路由"""
        return []


class LLMProviderProtocol(ABC):
    """LLM Provider 扩展点"""

    @abstractmethod
    async def chat(self, messages: list[dict], tools: list[dict] | None = None, **kwargs) -> Any:
        ...

    @abstractmethod
    async def stream_chat(self, messages: list[dict], tools: list[dict] | None = None, **kwargs) -> AsyncIterator[str]:
        ...

    @property
    @abstractmethod
    def context_length(self) -> int:
        ...

    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        ...


class MemoryBackendProtocol(ABC):
    """记忆存储后端扩展点"""

    @abstractmethod
    async def save(self, entry: dict) -> str:
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 10, **filters) -> list[dict]:
        ...

    @abstractmethod
    async def get(self, entry_id: str) -> dict | None:
        ...

    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        ...

    @abstractmethod
    async def clear(self) -> None:
        ...


class ToolProtocol(ABC):
    """Agent 工具扩展点"""

    @property
    @abstractmethod
    def definition(self) -> dict:
        ...

    @abstractmethod
    async def execute(self, **params) -> str:
        ...

    @abstractmethod
    async def check_availability(self) -> bool:
        ...


class PlatformAdapterProtocol(ABC):
    """消息平台适配器扩展点"""

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...

    @abstractmethod
    async def send_message(self, chat_id: str, text: str, **options) -> str:
        ...

    @abstractmethod
    async def on_message(self, handler: Callable) -> None:
        ...


class SessionStoreProtocol(ABC):
    """会话存储扩展点"""

    @abstractmethod
    async def create(self, **kwargs) -> dict:
        ...

    @abstractmethod
    async def get(self, session_id: str) -> dict | None:
        ...

    @abstractmethod
    async def update(self, session_id: str, **kwargs) -> dict:
        ...

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        ...

    @abstractmethod
    async def list(self, limit: int = 50, offset: int = 0, **filters) -> list[dict]:
        ...

    @abstractmethod
    async def add_message(self, session_id: str, role: str, content: str, **kwargs) -> dict:
        ...

    @abstractmethod
    async def get_messages(self, session_id: str, limit: int = 100, offset: int = 0) -> list[dict]:
        ...


class RAGEngineProtocol(ABC):
    """RAG 引擎扩展点"""

    @abstractmethod
    async def query(self, query: str, knowledge_bases: list[str], top_k: int = 5) -> list[dict]:
        ...

    @abstractmethod
    async def index(self, documents: list[dict], knowledge_base_id: str) -> None:
        ...

    @abstractmethod
    async def delete_knowledge_base(self, kb_id: str) -> bool:
        ...


class AgentEngineProtocol(ABC):
    """Agent 引擎扩展点"""

    @abstractmethod
    async def run(self, user_message: str, session: dict, **context) -> dict:
        ...

    @abstractmethod
    async def run_stream(self, user_message: str, session: dict, **context) -> AsyncIterator[dict]:
        ...
