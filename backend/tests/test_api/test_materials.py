"""物料 + BOM + 特征族 API 集成测试"""
import pytest

pytestmark = pytest.mark.asyncio


class TestMaterialAPI:
    async def test_create_material(self, async_client, auth_headers):
        resp = await async_client.post("/api/v1/materials", json={
            "material_code": "MTR-COMP-001", "name": "压缩机 GMCC 1HP",
            "category": "结构", "specification": "QXA-B092zX070", "unit": "pcs",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["material_code"] == "MTR-COMP-001"

    async def test_list_materials(self, async_client, auth_headers):
        resp = await async_client.get("/api/v1/materials", headers=auth_headers)
        assert resp.status_code == 200

    async def test_get_material(self, async_client, auth_headers):
        create_resp = await async_client.post("/api/v1/materials", json={
            "material_code": "MTR-FAN-001", "name": "贯流风扇",
            "category": "结构", "unit": "pcs",
        }, headers=auth_headers)
        mid = create_resp.json()["id"]
        resp = await async_client.get(f"/api/v1/materials/{mid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "贯流风扇"

    async def test_get_nonexistent_material(self, async_client, auth_headers):
        resp = await async_client.get("/api/v1/materials/99999", headers=auth_headers)
        assert resp.status_code == 404


class TestFeatureAPI:
    async def test_create_feature_family(self, async_client, auth_headers):
        resp = await async_client.post("/api/v1/feature-families", json={
            "name": "冷媒类型", "code": "REFRIGERANT", "data_type": "enum",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["code"] == "REFRIGERANT"

    async def test_add_feature_option(self, async_client, auth_headers):
        fam_resp = await async_client.post("/api/v1/feature-families", json={
            "name": "能效等级", "code": "ENERGY_RATING", "data_type": "enum",
        }, headers=auth_headers)
        fid = fam_resp.json()["id"]
        resp = await async_client.post(f"/api/v1/feature-families/{fid}/options", json={
            "value": "一级能效", "code": "L1",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["value"] == "一级能效"

    async def test_list_features(self, async_client, auth_headers):
        resp = await async_client.get("/api/v1/feature-families", headers=auth_headers)
        assert resp.status_code == 200


class TestBOMAPI:
    async def test_create_bom_node(self, async_client, auth_headers):
        # Setup: platform → series → model → material
        p = await async_client.post("/api/v1/platforms", json={
            "name": "BOM Test Platform", "code": "BOM-PLATFORM",
        }, headers=auth_headers)
        s = await async_client.post("/api/v1/series", json={
            "name": "BOM Test Series", "code": "BOM-SERIES",
            "platform_id": p.json()["id"],
        }, headers=auth_headers)
        m = await async_client.post("/api/v1/models", json={
            "model_number": "BOM-MODEL-001", "name": "BOM Test Model",
            "series_id": s.json()["id"],
        }, headers=auth_headers)
        mat = await async_client.post("/api/v1/materials", json={
            "material_code": "MTR-BOM-001", "name": "BOM材料",
            "category": "结构", "unit": "pcs",
        }, headers=auth_headers)

        resp = await async_client.post("/api/v1/bom", json={
            "model_id": m.json()["id"], "material_id": mat.json()["id"],
            "quantity": 1.0, "node_type": "assembly", "sequence": 1,
        }, headers=auth_headers)
        assert resp.status_code == 201

    async def test_get_bom_tree(self, async_client, auth_headers):
        p = await async_client.post("/api/v1/platforms", json={
            "name": "BOM Tree Platform", "code": "BOM-TREE-P",
        }, headers=auth_headers)
        s = await async_client.post("/api/v1/series", json={
            "name": "BOM Tree Series", "code": "BOM-TREE-S",
            "platform_id": p.json()["id"],
        }, headers=auth_headers)
        m = await async_client.post("/api/v1/models", json={
            "model_number": "BOM-TREE-MODEL", "name": "BOM Tree Model",
            "series_id": s.json()["id"],
        }, headers=auth_headers)
        resp = await async_client.get(f"/api/v1/bom?model_id={m.json()['id']}", headers=auth_headers)
        assert resp.status_code == 200
