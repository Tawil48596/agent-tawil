"""Analytics API"""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(request: Request):
    return {"today_tokens": 0, "today_cost": 0, "today_requests": 0, "active_sessions": 0}


@router.get("/tokens")
async def token_usage(request: Request, days: int = 7):
    return {"days": days, "data": []}


@router.get("/costs")
async def costs(request: Request):
    return {"by_model": {}, "by_provider": {}, "total": 0}


@router.get("/latency")
async def latency(request: Request):
    return {"avg_ms": 0, "p50_ms": 0, "p95_ms": 0, "p99_ms": 0}


@router.get("/tools")
async def tool_usage(request: Request):
    return {"by_tool": {}, "total_calls": 0}


@router.get("/export")
async def export_csv(request: Request, fmt: str = "csv"):
    from plugins.analytics.exporter import DataExporter
    return {"format": fmt, "data": ""}
