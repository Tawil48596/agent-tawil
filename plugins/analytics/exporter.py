"""数据导出 — CSV / JSON"""

import json


class DataExporter:
    """用量数据导出"""

    def export_csv(self, records: list) -> str:
        headers = [
            "timestamp",
            "model",
            "provider",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "cost",
            "latency_ms",
        ]
        lines = [",".join(headers)]
        for r in records:
            lines.append(
                f"{r.timestamp.isoformat()},{r.model},{r.provider},"
                f"{r.prompt_tokens},{r.completion_tokens},{r.total_tokens},"
                f"{r.cost},{r.latency_ms}"
            )
        return "\n".join(lines)

    def export_json(self, records: list) -> str:
        return json.dumps(
            [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "model": r.model,
                    "provider": r.provider,
                    "total_tokens": r.total_tokens,
                    "cost": r.cost,
                    "latency_ms": r.latency_ms,
                }
                for r in records
            ],
            ensure_ascii=False,
            indent=2,
        )
