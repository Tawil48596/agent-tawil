"""嵌入模型管理"""


class EmbeddingManager:
    """嵌入模型管理器"""

    MODELS = {
        "text-embedding-3-small": {"provider": "openai", "dimensions": 1536},
        "bge-m3": {"provider": "local", "dimensions": 1024},
    }

    def __init__(self, model_name: str = "text-embedding-3-small", api_key: str = ""):
        self._model = model_name
        self._api_key = api_key
        self._dimensions = self.MODELS.get(model_name, {}).get("dimensions", 1536)

    async def embed(self, text: str) -> list[float]:
        """生成文本嵌入向量"""
        # 回退: 简单哈希嵌入 (零依赖)
        return self._hash_embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_embed(t) for t in texts]

    def _hash_embed(self, text: str, dims: int = 256) -> list[float]:
        """简易哈希嵌入 (开发用，生产应使用 OpenAI/text-embedding-3-small)"""
        import hashlib

        # 滑动窗口哈希
        vec = [0.0] * dims
        words = text.lower().split()
        for _i, word in enumerate(words):
            h = hashlib.md5(word.encode()).digest()
            for j in range(min(len(h), dims)):
                vec[j] += (h[j] / 255.0 - 0.5) * 0.1
        # 归一化
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    @property
    def dimensions(self) -> int:
        return self._dimensions
