"""AST-Aware 代码分块 — 基于 Tree-sitter 的语法树分块

保留类名、方法签名、模块 import 声明等层级语义。
"""

import re
from typing import Optional


class CodeAwareChunker:
    """代码感知分块 — 优先使用 Tree-sitter，回退到启发式"""

    LANGUAGES = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
    }

    def __init__(self):
        self._parser = None
        self._language = None
        self._try_load_tree_sitter()

    def _try_load_tree_sitter(self):
        try:
            import tree_sitter_python
            from tree_sitter import Language, Parser
            PY_LANG = Language(tree_sitter_python.language())
            self._parser = Parser(PY_LANG)
            self._language = PY_LANG
        except ImportError:
            self._parser = None

    def chunk(self, code: str, file_ext: str = ".py") -> list[str]:
        """将代码按函数/类边界分块"""
        if self._parser:
            return self._tree_sitter_chunk(code)
        else:
            return self._heuristic_chunk(code, file_ext)

    def _tree_sitter_chunk(self, code: str) -> list[str]:
        """Tree-sitter 精确分块"""
        tree = self._parser.parse(bytes(code, "utf-8"))
        root = tree.root_node

        chunks = []
        imports = self._extract_imports(root)

        for node in root.children:
            if node.type in ("function_definition", "class_definition",
                             "decorated_definition", "async_function_definition"):
                # 提取函数/类的完整代码块
                chunk_text = node.text.decode("utf-8")

                # 添加上下文 (父类信息)
                context = self._get_node_context(node)
                if context:
                    chunk_text = f"# context: {context}\n{chunk_text}"

                chunks.append(chunk_text)

        # 如果分块数太少，回退到启发式
        if len(chunks) < 2:
            return self._heuristic_chunk(code, ".py")

        # 在开头加入 import 块
        if imports:
            chunks.insert(0, "# imports\n" + "\n".join(imports) + "\n")

        return chunks

    def _heuristic_chunk(self, code: str, file_ext: str = ".py") -> list[str]:
        """启发式分块 — 按 def/class 边界"""
        chunks = []
        lines = code.split("\n")
        current = []
        current_header = ""

        for line in lines:
            stripped = line.strip()
            # 检测函数/类定义
            if re.match(r"^\s*(def |class |async def |export |function |public class )", line):
                if current:
                    chunks.append("\n".join(current))
                current = [line]
                current_header = stripped
            else:
                current.append(line)

        if current:
            chunks.append("\n".join(current))

        # 提取 import 语句作为独立 chunk
        imports = [l for l in lines if re.match(r"^\s*(import |from \w+ import)", l)]
        if imports and len(chunks) > 1:
            chunks.insert(0, "\n".join(imports))

        return chunks

    def _extract_imports(self, root) -> list[str]:
        """提取 import 语句"""
        imports = []
        for child in root.children:
            if child.type in ("import_statement", "import_from_statement"):
                imports.append(child.text.decode("utf-8"))
        return imports

    def _get_node_context(self, node) -> Optional[str]:
        """获取节点的上下文 (父类名等)"""
        parent = node.parent
        if parent and parent.type == "class_definition":
            # 在类内部定义的函数，添加上下文
            class_name = parent.child_by_field_name("name")
            if class_name:
                return f"class {class_name.text.decode('utf-8')}"
        return None
