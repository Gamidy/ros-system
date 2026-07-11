"""测试 fixtures — 数据库会话 + 测试客户端"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine):
    session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(async_engine, async_session):
    """带认证token的HTTP测试客户端"""

    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client):
    """创建admin用户并返回Bearer token头"""
    # 注册
    resp = await client.post("/api/v1/auth/register", json={
        "username": "testadmin", "email": "admin@test.com", "password": "admin123"
    })
    assert resp.status_code == 201
    # 登录
    resp = await client.post("/api/v1/auth/token", json={
        "username": "testadmin", "password": "admin123"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
