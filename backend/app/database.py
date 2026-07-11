"""数据库连接 — SQLAlchemy 2.0 async"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# 异步引擎 (用于FastAPI请求)
_engine_kwargs = {"echo": settings.DEBUG}
if "postgresql" in settings.DATABASE_URL:
    _engine_kwargs.update({"pool_size": 10, "max_overflow": 20, "pool_recycle": 3600})

async_engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI依赖注入：获取异步数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("数据库会话异常，执行回滚")
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_url() -> str:
    """获取同步数据库URL (用于Alembic)"""
    return settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
