"""依赖解析 — Python包/系统库/API Key"""

import importlib
import os
import shutil
from dataclasses import dataclass, field


@dataclass
class DependencyCheck:
    available: bool = True
    missing_env: list[str] = field(default_factory=list)
    missing_packages: list[str] = field(default_factory=list)
    missing_system: list[str] = field(default_factory=list)


class DependencyResolver:
    """依赖解析器"""

    def check(self, requires_env: list[str] = None,
              requires_packages: list[str] = None,
              requires_system: list[str] = None) -> DependencyCheck:
        result = DependencyCheck()

        for var in (requires_env or []):
            if var not in os.environ: result.missing_env.append(var)

        for pkg in (requires_packages or []):
            pkg_name = pkg.split(">=")[0].split("[")[0].strip()
            try: importlib.import_module(pkg_name)
            except ImportError: result.missing_packages.append(pkg)

        for cmd in (requires_system or []):
            if not shutil.which(cmd): result.missing_system.append(cmd)

        result.available = not (result.missing_env or result.missing_packages or result.missing_system)
        return result

    def resolve_install_order(self, tools: list[dict]) -> list[str]:
        """拓扑排序安装顺序"""
        graph: dict[str, list[str]] = {}
        for t in tools:
            deps = t.get("dependencies", [])
            graph[t["name"]] = deps

        in_degree = {n: 0 for n in graph}
        for n, deps in graph.items():
            for d in deps:
                if d in in_degree: in_degree[n] += 1

        queue = [n for n, d in in_degree.items() if d == 0]
        order = []
        while queue:
            node = queue.pop(0); order.append(node)
            for n, deps in graph.items():
                if node in deps:
                    in_degree[n] -= 1
                    if in_degree[n] == 0: queue.append(n)
        return order
