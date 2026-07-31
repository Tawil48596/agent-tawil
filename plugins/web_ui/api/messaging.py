import json

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/v1/messaging", tags=["messaging"])


@router.post("/webhook/{provider}")
async def messaging_webhook(provider: str, request: Request):
    payload = await request.body()
    try:
        event = json.loads(payload)

        async def run_agent(text: str, session_id: str) -> str:
            response = await request.app.state.agent_engine.run(
                user_message=text, session={"id": session_id, "source": provider})
            return response.text

        return await request.app.state.messaging_gateway.process(
            provider, event, payload, request.headers.get("x-signature", ""), run_agent)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/sessions")
async def messaging_sessions(request: Request):
    gateway = request.app.state.messaging_gateway
    return {"count": len(gateway._sessions)}
