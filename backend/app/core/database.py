"""数据库连接"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings
import json
import redis.asyncio as aioredis

engine = create_engine(
    settings.db_url,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Redis connection (预留，当前未使用)
# import redis.asyncio as aioredis
# redis_client = None
#
# async def get_redis():
#     global redis_client
#     if redis_client is None:
#         redis_client = aioredis.Redis(
#             host=settings.REDIS_HOST,
#             port=settings.REDIS_PORT,
#             db=settings.REDIS_DB,
#             password=settings.REDIS_PASSWORD or None,
#             decode_responses=True,
#         )
#     return redis_client
