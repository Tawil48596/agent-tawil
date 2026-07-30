"""工具市场 — 浏览/搜索/安装/卸载 + 社区源"""

from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

from plugins.tool_market.registry import ToolRegistry, ToolDef

logger = structlog.get_logger()


@dataclass
class MarketplaceEntry:
    """市场中的工具条目"""
    name: str
    description: str
    version: str
    author: str
    tags: list[str]
    downloads: int = 0
    rating: float = 0.0
    source_url: str = ""
    is_dangerous: bool = False


class Marketplace:
    """工具市场"""

    def __init__(self, registry: ToolRegistry):
        self._registry = registry
        self._market: dict[str, MarketplaceEntry] = {}
        self._installed_versions: dict[str, str] = {}  # name → version

    # ── 市场管理 ──

    def publish(self, entry: MarketplaceEntry):
        """发布工具到市场"""
        self._market[entry.name] = entry

    def unpublish(self, name: str):
        self._market.pop(name, None)

    # ── 浏览/搜索 ──

    def browse(self, query: str = "", tag: str = "", sort_by: str = "downloads",
                limit: int = 20) -> list[MarketplaceEntry]:
        results = list(self._market.values())

        if query:
            q = query.lower()
            results = [e for e in results
                        if q in e.name.lower() or q in e.description.lower()]
        if tag:
            results = [e for e in results if tag in e.tags]

        sort_key = {"downloads": lambda e: e.downloads, "rating": lambda e: e.rating,
                      "name": lambda e: e.name}
        results.sort(key=sort_key.get(sort_by, lambda e: e.downloads), reverse=True)

        return results[:limit]

    # ── 安装/卸载 ──

    async def install(self, name: str) -> dict:
        """从市场安装工具"""
        entry = self._market.get(name)
        if not entry:
            return {"error": f"Tool '{name}' not found in marketplace"}

        if self._registry.get(name) and self._registry.get(name).installed:
            return {"error": f"Tool '{name}' is already installed"}

        # 检查依赖
        tool = ToolDef(
            name=entry.name,
            description=entry.description,
            version=entry.version,
            author=entry.author,
            tags=entry.tags,
            is_dangerous=entry.is_dangerous,
        )
        dep_check = self._registry.check_dependencies(tool)
        if not dep_check["available"]:
            return {"error": "Dependencies not met", "missing": dep_check["missing"]}

        tool.installed = True
        tool.install_date = __import__("datetime").datetime.now().isoformat()
        self._registry.register(tool)
        self._installed_versions[name] = entry.version

        entry.downloads += 1
        logger.info("Tool installed", name=name, version=entry.version)
        return {"ok": True, "name": name, "version": entry.version}

    async def uninstall(self, name: str) -> dict:
        """卸载工具"""
        tool = self._registry.get(name)
        if not tool or not tool.installed:
            return {"error": f"Tool '{name}' not installed"}

        tool.installed = False
        self._installed_versions.pop(name, None)
        logger.info("Tool uninstalled", name=name)
        return {"ok": True, "name": name}

    async def update(self, name: str) -> dict:
        """更新工具到最新版本"""
        entry = self._market.get(name)
        current = self._installed_versions.get(name, "0.0.0")
        if not entry:
            return {"error": f"Tool '{name}' not in marketplace"}
        if entry.version <= current:
            return {"ok": True, "name": name, "message": "Already up to date",
                     "version": current}

        await self.uninstall(name)
        return await self.install(name)

    # ── 统计 ──

    def get_stats(self) -> dict:
        return {
            "market_size": len(self._market),
            "installed": len(self._installed_versions),
            "total_downloads": sum(e.downloads for e in self._market.values()),
        }
