"""上下文压缩 — LLM 摘要压缩 (滑动窗口 + 关键信息保留)"""

from typing import Any

from litellm import acompletion


async def compress_messages(
    messages: list[dict],
    route_result: Any,
    keep_recent: int = 10,
) -> list[dict]:
    """压缩消息历史

    策略: 保留 system prompt + 最近 N 条完整消息 + 更早消息的 LLM 摘要
    """
    if len(messages) <= keep_recent + 4:
        return messages  # 还不够长，不需要压缩

    system_msg = messages[0] if messages[0]["role"] == "system" else None
    recent = messages[-keep_recent:]
    older = messages[1:-keep_recent] if system_msg else messages[:-keep_recent]

    if not older:
        return messages

    # 将更早的消息压缩为摘要
    summary = await _summarize(older, route_result)

    compressed = []
    if system_msg:
        compressed.append(system_msg)
    compressed.append({"role": "system", "content": f"[历史对话摘要]\n{summary}"})
    compressed.extend(recent)

    return compressed


async def _summarize(messages: list[dict], route_result: Any) -> str:
    """用 LLM 生成对话摘要"""
    conversation_text = []
    for m in messages:
        role = m.get("role", "unknown")
        content = m.get("content", "")
        if content:
            conversation_text.append(f"{role}: {content[:500]}")  # 截断每条

    text = "\n".join(conversation_text[-50:])  # 最多取最后 50 条

    if not text.strip():
        return "(空对话)"

    try:
        response = await acompletion(
            model=f"{route_result.provider}/{route_result.model}",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "请用 3-5 句话简要总结以下对话的关键信息和决策。"
                        "只输出摘要，不要加任何前缀。"
                    ),
                },
                {"role": "user", "content": text},
            ],
            api_key=route_result.api_key,
            api_base=route_result.base_url if route_result.base_url else None,
            max_tokens=300,
        )
        return response.choices[0].message.content or "(摘要生成失败)"
    except Exception:
        return "(摘要生成失败)"
