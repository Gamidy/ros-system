"""产品模型测试 — Platform / Series / Model"""

import pytest
from app.models.product import Platform, Series, Model


@pytest.mark.asyncio
async def test_create_platform(async_session):
    p = Platform(name="室外机 1HP", code="ODU-1HP", description="1匹室外机平台")
    async_session.add(p)
    await async_session.flush()
    assert p.id is not None
    assert p.name == "室外机 1HP"


@pytest.mark.asyncio
async def test_create_series(async_session):
    p = Platform(name="室外机", code="ODU-TEST")
    async_session.add(p)
    await async_session.flush()

    s = Series(name="壁挂式 1HP", code="WALL-1HP", platform_id=p.id)
    async_session.add(s)
    await async_session.flush()

    assert s.platform_id == p.id


@pytest.mark.asyncio
async def test_create_model(async_session):
    p = Platform(name="室外机", code="ODU-MODEL")
    async_session.add(p)
    await async_session.flush()
    s = Series(name="壁挂式", code="WALL-MODEL", platform_id=p.id)
    async_session.add(s)
    await async_session.flush()

    m = Model(model_number="W09K-1", series_id=s.id, rated_capacity=9000.0, refrigerant="R32")
    async_session.add(m)
    await async_session.flush()

    assert m.model_number == "W09K-1"
    assert m.rated_capacity == 9000.0
