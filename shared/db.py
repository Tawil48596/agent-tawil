"""数据库工具 — SQLAlchemy 异步引擎管理"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_database_url(db_url: str) -> str:
    """将 sqlite:// 转为 aiosqlite:// 以支持异步"""
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return db_url


async def init_db(database_url: str, echo: bool = False) -> None:
    """初始化数据库引擎"""
    global _engine, _session_factory
    async_url = get_database_url(database_url)
    _engine = create_async_engine(async_url, echo=echo)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """获取数据库会话（依赖注入用）"""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _session_factory() as session:
        yield session


async def close_db() -> None:
    """关闭数据库连接"""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
