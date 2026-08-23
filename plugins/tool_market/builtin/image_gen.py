"""内置工具: image_gen — AI 图像生成 (DALL-E/Stable Diffusion)"""

import json


async def image_generate(prompt: str, size: str = "1024x1024", n: int = 1) -> str:
    try:
        import os

        import httpx

        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            return json.dumps({"error": "OPENAI_API_KEY not configured"})
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {key}"},
                json={"prompt": prompt, "size": size, "n": n},
            )
            data = r.json()
            return json.dumps({"images": [{"url": i.get("url", "")} for i in data.get("data", [])]})
    except Exception as e:
        return json.dumps({"error": str(e)})
