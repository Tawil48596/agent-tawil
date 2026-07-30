"""内置工具: file_ops — 文件读写/搜索/编辑"""

import json
import os
from pathlib import Path
from typing import Optional


async def file_read(path: str, encoding: str = "utf-8", max_lines: int = 500) -> str:
    """读取文件"""
    p = Path(path)
    if not p.exists():
        return json.dumps({"error": f"File not found: {path}"})
    if p.is_dir():
        return json.dumps({"error": f"Path is a directory: {path}"})
    try:
        content = p.read_text(encoding=encoding)
        lines = content.split("\n")
        if len(lines) > max_lines:
            truncated = "\n".join(lines[:max_lines])
            return json.dumps({
                "path": str(p.absolute()),
                "content": truncated,
                "total_lines": len(lines),
                "truncated": True,
            })
        return json.dumps({"path": str(p.absolute()), "content": content, "total_lines": len(lines)})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def file_write(path: str, content: str, encoding: str = "utf-8",
                      create_dirs: bool = True) -> str:
    """写入文件"""
    p = Path(path)
    if create_dirs:
        p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(content, encoding=encoding)
        return json.dumps({"ok": True, "path": str(p.absolute()), "size": len(content)})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def file_list(path: str = ".", pattern: str = "*",
                     recursive: bool = False, max_items: int = 100) -> str:
    """列出文件"""
    p = Path(path)
    if not p.exists():
        return json.dumps({"error": f"Path not found: {path}"})

    if recursive:
        items = list(p.rglob(pattern))
    else:
        items = list(p.glob(pattern))

    result = []
    for item in items[:max_items]:
        try:
            stat = item.stat()
            result.append({
                "name": item.name,
                "path": str(item.relative_to(p)),
                "type": "dir" if item.is_dir() else "file",
                "size": stat.st_size if item.is_file() else 0,
            })
        except OSError:
            pass

    return json.dumps({
        "path": str(p.absolute()),
        "items": result,
        "total": len(items),
        "truncated": len(items) > max_items,
    })


async def file_search(path: str, query: str, recursive: bool = True,
                       case_sensitive: bool = False, max_results: int = 20) -> str:
    """搜索文件内容"""
    p = Path(path)
    if not p.exists():
        return json.dumps({"error": f"Path not found: {path}"})

    results = []
    files = p.rglob("*") if recursive else p.glob("*")
    q = query if case_sensitive else query.lower()

    for f in files:
        if f.is_file() and f.suffix in (".py", ".md", ".txt", ".toml", ".yaml", ".json",
                                          ".js", ".ts", ".html", ".css", ".go", ".rs"):
            try:
                content = f.read_text(errors="ignore")
                content_to_search = content if case_sensitive else content.lower()
                if q in content_to_search:
                    lines = content.split("\n")
                    matches = [(i+1, l) for i, l in enumerate(lines)
                               if q in (l if case_sensitive else l.lower())]
                    results.append({
                        "file": str(f.relative_to(p)),
                        "matches": len(matches),
                        "first_match_line": matches[0][0] if matches else 0,
                        "preview": matches[0][1].strip()[:200] if matches else "",
                    })
            except Exception:
                pass

            if len(results) >= max_results:
                break

    return json.dumps({"path": str(p.absolute()), "query": query, "results": results})
