"""P2 — family_ids 关联表 + 列表分页 测试"""

import pytest


class TestConfigGroupFamilies:
    """ConfigGroup.family_ids 从逗号字符串升级为关联表"""

    @pytest.mark.asyncio
    async def test_create_group_with_families(self, async_client, auth_headers):
        """创建配置组时可以绑定多个特征族"""
        # 先创建特征族
        resp = await async_client.post("/api/v1/feature-families", json={
            "name": "制冷剂类型", "code": "REFRIGERANT",
        }, headers=auth_headers)
        fam1_id = resp.json()["id"]

        resp = await async_client.post("/api/v1/feature-families", json={
            "name": "电压", "code": "VOLTAGE",
        }, headers=auth_headers)
        fam2_id = resp.json()["id"]

        # 创建配置组并关联特征族
        resp = await async_client.post("/api/v1/config/groups", json={
            "name": "关联表测试组",
            "series_id": 1,
            "family_ids": [fam1_id, fam2_id],
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["family_ids"]) == 2
        assert fam1_id in data["family_ids"]
        assert fam2_id in data["family_ids"]

    @pytest.mark.asyncio
    async def test_get_group_returns_families(self, async_client, auth_headers):
        """获取配置组时返回关联的特征族 ID 列表"""
        resp = await async_client.post("/api/v1/feature-families", json={
            "name": "能效等级", "code": "EER",
        }, headers=auth_headers)
        fam_id = resp.json()["id"]

        resp = await async_client.post("/api/v1/config/groups", json={
            "name": "单个关联测试",
            "series_id": 1,
            "family_ids": [fam_id],
        }, headers=auth_headers)
        group_id = resp.json()["id"]

        # 获取配置组
        resp = await async_client.get("/api/v1/config/groups", headers=auth_headers)
        groups = resp.json()
        target = next(g for g in groups if g["id"] == group_id)
        assert isinstance(target["family_ids"], list)
        assert fam_id in target["family_ids"]


class TestPaginatedListEndpoints:
    """列表端点应支持 skip/limit 分页"""

    @pytest.mark.asyncio
    async def test_platforms_paginated(self, async_client, auth_headers):
        """Platforms 列表支持分页"""
        resp = await async_client.get("/api/v1/platforms?skip=0&limit=5", headers=auth_headers)
        assert resp.status_code == 200
        # 可以是 list 或 paginated object
        data = resp.json()
        if isinstance(data, dict):
            assert "items" in data
            assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_series_paginated(self, async_client, auth_headers):
        """Series 列表支持分页"""
        resp = await async_client.get("/api/v1/series?skip=0&limit=5", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_models_paginated(self, async_client, auth_headers):
        """Models 列表支持分页"""
        resp = await async_client.get("/api/v1/models?skip=0&limit=5", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_materials_paginated(self, async_client, auth_headers):
        """Materials 列表支持分页"""
        resp = await async_client.get("/api/v1/materials?skip=0&limit=5", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_bom_paginated(self, async_client, auth_headers):
        """BOM 列表支持分页"""
        resp = await async_client.get("/api/v1/bom?model_id=1&skip=0&limit=5", headers=auth_headers)
        assert resp.status_code == 200
