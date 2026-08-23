"""工具版本管理 — 语义版本"""

import re
from dataclasses import dataclass


@dataclass
class SemVer:
    major: int = 0
    minor: int = 1
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def parse(cls, version: str) -> "SemVer":
        m = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
        if m:
            return cls(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return cls()

    def bump_major(self):
        self.major += 1
        self.minor = 0
        self.patch = 0

    def bump_minor(self):
        self.minor += 1
        self.patch = 0

    def bump_patch(self):
        self.patch += 1

    def __gt__(self, other):
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)


class VersionManager:
    def __init__(self):
        self._versions: dict[str, str] = {}

    def register(self, name: str, version: str = "0.1.1"):
        self._versions[name] = version

    def get(self, name: str) -> str:
        return self._versions.get(name, "0.0.0")

    def check_update(self, name: str, latest: str) -> bool:
        current = SemVer.parse(self._versions.get(name, "0.0.0"))
        return SemVer.parse(latest) > current

    def install(self, name: str, version: str):
        self._versions[name] = version

    def uninstall(self, name: str):
        self._versions.pop(name, None)
