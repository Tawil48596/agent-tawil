"""依赖注入容器"""

from collections.abc import Callable
from typing import Any


class DIContainer:
    """轻量级 DI 容器——所有扩展点通过容器获取"""

    def __init__(self) -> None:
        self._registry: dict[str, dict[str, Any]] = {}
        self._factories: dict[str, dict[str, Callable[[], Any]]] = {}

    def register(
        self,
        interface: type[Any] | str,
        implementation: Any,
        *,
        name: str = "default",
    ) -> None:
        """注册实现"""
        key = self._type_key(interface)
        self._registry.setdefault(key, {})[name] = implementation

    def register_factory(
        self,
        interface: type[Any] | str,
        factory: Callable[[], Any],
        *,
        name: str = "default",
    ) -> None:
        """注册工厂函数（延迟创建）"""
        key = self._type_key(interface)
        self._factories.setdefault(key, {})[name] = factory

    def resolve(self, interface: type[Any] | str, name: str = "default") -> Any:
        """获取实现"""
        key = self._type_key(interface)
        if key in self._factories and name in self._factories[key]:
            return self._factories[key][name]()
        if key in self._registry and name in self._registry[key]:
            return self._registry[key][name]
        raise KeyError(f"No implementation registered for {key}[{name}]")

    def resolve_all(self, interface: type[Any] | str) -> list[Any]:
        """获取某接口的所有注册实现（用于链式调用）"""
        key = self._type_key(interface)
        result: list[Any] = []
        for group in [self._registry, self._factories]:
            if key in group:
                result.extend(group[key].values())
        return result

    @staticmethod
    def _type_key(interface: type[Any] | str) -> str:
        if isinstance(interface, str):
            return interface
        return getattr(interface, "__name__", str(interface))
