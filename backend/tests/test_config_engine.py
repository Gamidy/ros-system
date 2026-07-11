"""P0 — 配置引擎测试: ConfigRule + SKU生成"""

import pytest
import pytest_asyncio


class TestConfigRuleModel:
    """配置规则模型测试"""

    @pytest.mark.asyncio
    async def test_create_config_group(self, async_client, auth_headers):
        """测试创建配置组"""
        resp = await async_client.post("/api/v1/config/groups", json={
            "name": "R32变频配置组",
            "series_id": 1,
            "family_ids": [1, 2, 3],
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "R32变频配置组"
        assert data["series_id"] == 1

    @pytest.mark.asyncio
    async def test_create_config_rule_requires(self, async_client, auth_headers):
        """测试创建 requires 规则: A 需要 B"""
        # 先创建配置组
        resp = await async_client.post("/api/v1/config/groups", json={
            "name": "测试配置组",
            "series_id": 1,
        }, headers=auth_headers)
        group_id = resp.json()["id"]

        resp = await async_client.post("/api/v1/config/rules", json={
            "group_id": group_id,
            "rule_type": "requires",
            "source_option_id": 1,
            "target_option_id": 2,
            "description": "R32制冷剂需要直流变频压缩机",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["rule_type"] == "requires"
        assert data["source_option_id"] == 1
        assert data["target_option_id"] == 2

    @pytest.mark.asyncio
    async def test_create_config_rule_excludes(self, async_client, auth_headers):
        """测试创建 excludes 规则: A 与 B 互斥"""
        resp = await async_client.post("/api/v1/config/groups", json={
            "name": "互斥测试组",
            "series_id": 1,
        }, headers=auth_headers)
        group_id = resp.json()["id"]

        resp = await async_client.post("/api/v1/config/rules", json={
            "group_id": group_id,
            "rule_type": "excludes",
            "source_option_id": 3,
            "target_option_id": 4,
            "description": "220V与380V互斥",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["rule_type"] == "excludes"

    @pytest.mark.asyncio
    async def test_list_config_rules(self, async_client, auth_headers):
        """测试列出配置规则"""
        resp = await async_client.get("/api/v1/config/rules", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_validate_config(self, async_client, auth_headers):
        """测试配置校验: 有效配置通过"""
        # 创建配置组
        resp = await async_client.post("/api/v1/config/groups", json={
            "name": "校验测试组",
            "series_id": 1,
        }, headers=auth_headers)
        group_id = resp.json()["id"]

        # 规则: 选项1 requires 选项2
        await async_client.post("/api/v1/config/rules", json={
            "group_id": group_id,
            "rule_type": "requires",
            "source_option_id": 1,
            "target_option_id": 2,
        }, headers=auth_headers)

        # 校验: 选了1和2，应通过
        resp = await async_client.post(f"/api/v1/config/groups/{group_id}/validate", json={
            "selected_option_ids": [1, 2],
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_config_fails_excludes(self, async_client, auth_headers):
        """测试配置校验: 互斥选项被拒绝"""
        resp = await async_client.post("/api/v1/config/groups", json={
            "name": "互斥校验",
            "series_id": 1,
        }, headers=auth_headers)
        group_id = resp.json()["id"]

        await async_client.post("/api/v1/config/rules", json={
            "group_id": group_id,
            "rule_type": "excludes",
            "source_option_id": 3,
            "target_option_id": 4,
        }, headers=auth_headers)

        resp = await async_client.post(f"/api/v1/config/groups/{group_id}/validate", json={
            "selected_option_ids": [3, 4],
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["valid"] is False
        assert len(resp.json()["violations"]) >= 1
