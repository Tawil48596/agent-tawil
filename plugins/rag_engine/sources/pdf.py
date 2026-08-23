"""PDF 文档源"""

from pathlib import Path

import structlog

logger = structlog.get_logger()


class PDFSource:
    """从 PDF 文件索引文档"""

    async def fetch(self, file_path: str) -> list[dict]:
        path = Path(file_path)
        if not path.exists():
            return []

        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages.append(
                        {
                            "content": text,
                            "metadata": {"source": str(path), "page": i + 1, "type": "pdf"},
                        }
                    )
            return pages
        except ImportError:
            return [
                {
                    "content": f"pypdf not installed. Cannot parse: {file_path}",
                    "metadata": {"source": str(path)},
                }
            ]
        except Exception as e:
            logger.warning("PDF parse failed", path=str(path), error=str(e))
            return []
