"""物料/BOM/特征 模型测试"""

import pytest
from app.models.bom import Material, SuperBOMNode
from app.models.feature import FeatureFamily, FeatureOption


@pytest.mark.asyncio
async def test_create_material(async_session):
    m = Material(material_code="MTR-001", name="压缩机", category="结构", specification="GMCC 1HP", unit="pcs")
    async_session.add(m)
    await async_session.flush()
    assert m.material_code == "MTR-001"


@pytest.mark.asyncio
async def test_create_feature_family(async_session):
    f = FeatureFamily(name="冷媒类型", code="REFRIGERANT", data_type="enum")
    async_session.add(f)
    await async_session.flush()

    opt = FeatureOption(family_id=f.id, value="R32", code="R32")
    async_session.add(opt)
    await async_session.flush()

    assert opt.value == "R32"
    assert opt.family_id == f.id
