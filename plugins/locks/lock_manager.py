"""分布式锁 — Redis Redlock + CRC 乐观锁，防并发写覆盖"""

import asyncio
import hashlib
import json
import time
from contextlib import asynccontextmanager


class OptimisticLock:
    """CRC 乐观锁 — 单节点 SQLite 场景适用

    写入前记录当前版本 CRC，提交时校验:
      if current_crc == expected_crc:
          写入成功
      else:
          冲突 → 重试 (最多 3 次)
    """

    def __init__(self, max_retries: int = 3):
        self._versions: dict[str, str] = {}  # key → crc
        self._max_retries = max_retries

    def read(self, key: str, data: dict) -> tuple[dict, str]:
        """读取数据并返回 (数据, CRC token)"""
        crc = self._compute_crc(data)
        self._versions[key] = crc
        return data, crc

    async def write(self, key: str, expected_crc: str, new_data: dict) -> tuple[bool, dict | None]:
        """乐观写入: CRC 匹配则成功，否则重试"""
        for attempt in range(self._max_retries):
            current_crc = self._versions.get(key, "")
            if current_crc == expected_crc or current_crc == "":
                new_crc = self._compute_crc(new_data)
                self._versions[key] = new_crc
                return True, new_data
            # 冲突 — 等待后重试
            await asyncio.sleep(0.1 * (attempt + 1))
        return False, None

    @staticmethod
    def _compute_crc(data: dict) -> str:
        raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


class RedisLock:
    """Redis Redlock 分布式锁

    用法:
        async with RedisLock(redis, "memory:user123:write", ttl=10):
            await write_memory(data)
    """

    def __init__(self, redis_client, key: str, ttl: int = 10):
        self._redis = redis_client
        self._key = f"lock:{key}"
        self._ttl = ttl
        self._token = hashlib.sha256(f"{key}:{time.time()}".encode()).hexdigest()

    async def acquire(self) -> bool:
        """尝试获取锁"""
        return bool(
            await self._redis.set(
                self._key,
                self._token,
                nx=True,
                ex=self._ttl,
            )
        )

    async def release(self):
        """释放锁 (Lua 脚本保证原子性)"""
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await self._redis.eval(script, 1, self._key, self._token)

    async def __aenter__(self):
        acquired = await self.acquire()
        if not acquired:
            raise LockAcquisitionError(f"Failed to acquire lock: {self._key}")
        return self

    async def __aexit__(self, *args):
        await self.release()


class LockAcquisitionError(Exception):
    pass


class LockManager:
    """锁管理器 — 自动选择 Redlock 或乐观锁"""

    def __init__(self, redis_url: str | None = None):
        self._redis = None
        if redis_url:
            try:
                import redis.asyncio as aioredis

                self._redis = aioredis.from_url(redis_url, decode_responses=True)
            except ImportError:
                pass
        self._optimistic = OptimisticLock()

    @asynccontextmanager
    async def with_lock(self, key: str, ttl: int = 10):
        """上下文管理器: 自动选择锁策略"""
        if self._redis:
            async with RedisLock(self._redis, key, ttl):
                yield
        else:
            # 乐观锁模式 — 在调用侧手动 read/write
            yield

    def optimistic(self) -> OptimisticLock:
        return self._optimistic
