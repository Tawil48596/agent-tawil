"""技能加载器 — 从文件加载自定义指令/工作流"""

from pathlib import Path


class SkillLoader:
    """加载技能/指令文件 (Markdown 格式)"""

    def __init__(self, skills_dir: str = "skills/"):
        self._skills_dir = Path(skills_dir)
        self._cache: dict[str, str] = {}

    def list_skills(self) -> list[str]:
        """列出所有可用技能"""
        if not self._skills_dir.exists():
            return []
        return [p.stem for p in self._skills_dir.glob("*.md")]

    def load_skill(self, name: str) -> str | None:
        """加载单个技能内容"""
        if name in self._cache:
            return self._cache[name]

        path = self._skills_dir / f"{name}.md"
        if not path.exists():
            # 也尝试 .txt
            path = self._skills_dir / f"{name}.txt"
            if not path.exists():
                return None

        content = path.read_text(encoding="utf-8")
        self._cache[name] = content
        return content

    def load_skills(self, names: list[str]) -> dict[str, str]:
        """批量加载技能"""
        return {name: self.load_skill(name) for name in names if self.load_skill(name)}

    def reload(self):
        """清除缓存，重新加载"""
        self._cache.clear()
