"""Runtime-only provider configuration for local deployments."""

from ipaddress import ip_address
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, SecretStr

router = APIRouter(prefix="/api/v1/runtime/providers", tags=["runtime-config"])
SUPPORTED_PROVIDERS = {"openai", "anthropic", "deepseek"}


class ProviderUpdate(BaseModel):
    api_key: SecretStr
    base_url: str = Field(min_length=8, max_length=2048)


def _require_local_request(request: Request) -> None:
    host = request.client.host if request.client else ""
    try:
        if not ip_address(host).is_loopback:
            raise HTTPException(
                403, "Runtime provider configuration is only available from localhost"
            )
    except ValueError as exc:
        raise HTTPException(
            403, "Runtime provider configuration is only available from localhost"
        ) from exc


def _router(request: Request):
    model_router = getattr(request.app.state, "model_router", None)
    if model_router is None:
        raise HTTPException(503, "Model router is not initialized")
    return model_router


@router.get("")
async def list_runtime_providers(request: Request):
    _require_local_request(request)
    return {"providers": _router(request).provider_status(), "persistence": "memory"}


@router.put("/{provider_name}")
async def update_runtime_provider(provider_name: str, body: ProviderUpdate, request: Request):
    _require_local_request(request)
    name = provider_name.strip().lower()
    if name not in SUPPORTED_PROVIDERS:
        raise HTTPException(400, f"Unsupported provider: {name}")

    parsed = urlparse(body.base_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(400, "base_url must be a valid HTTP(S) URL")

    api_key = body.api_key.get_secret_value().strip()
    if not api_key:
        raise HTTPException(400, "api_key is required")

    model_router = _router(request)
    model_router.update_provider(name, api_key=api_key, base_url=body.base_url)
    return {
        "provider": name,
        "configured": True,
        "base_url": body.base_url.strip(),
        "persistence": "memory",
    }


@router.delete("/{provider_name}")
async def remove_runtime_provider(provider_name: str, request: Request):
    _require_local_request(request)
    name = provider_name.strip().lower()
    if name not in SUPPORTED_PROVIDERS:
        raise HTTPException(400, f"Unsupported provider: {name}")
    _router(request).remove_provider(name)
    return {"provider": name, "configured": False}
