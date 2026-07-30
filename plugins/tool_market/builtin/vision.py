"""内置工具: vision — 图像分析"""
import json, os

async def vision_analyze(image_url: str, prompt: str = "Describe this image in detail") -> str:
    try:
        import httpx
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key: return json.dumps({"error": "OPENAI_API_KEY not configured"})
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={"model": "gpt-4o", "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_url}}]}], "max_tokens": 500})
            data = r.json()
            return json.dumps({"analysis": data["choices"][0]["message"]["content"]})
    except Exception as e: return json.dumps({"error": str(e)})
