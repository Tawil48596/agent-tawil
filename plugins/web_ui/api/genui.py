"""Generative UI API — 组件列表 + Schema 映射"""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v1/genui", tags=["genui"])


@router.get("/components")
async def list_components(request: Request):
    """列出所有可用 UI 组件"""
    sm = request.app.state.schema_mapper
    return {"components": sm.list_components()}


@router.get("/map/{tool_name}")
async def map_tool(tool_name: str, request: Request):
    """获取工具的 UI 组件映射"""
    sm = request.app.state.schema_mapper
    return sm.get_tool_ui_schema(tool_name)


@router.post("/preview/{tool_name}")
async def preview(tool_name: str, body: dict, request: Request):
    """预览工具结果 → UI 组件映射"""
    sm = request.app.state.schema_mapper
    data = body.get("data", {})
    explicit = body.get("component", "")
    component = sm.map(tool_name, data, explicit_component=explicit)
    return {
        "tool": tool_name,
        "component": component.type,
        "title": component.title,
        "props": component.props,
    }
