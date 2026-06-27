"""市场能效等级 CRUD 接口测试"""
import pytest


class TestMarketEnergyLevels:
    """市场能效等级 CRUD — 顺序执行"""

    def test_01_create_market(self, client, admin_headers):
        """先创建测试市场作为前置条件"""
        r = client.post("/api/pm/markets", json={
            "code": "TEST",
            "name": "TestMarket",
            "region": "SEA",
            "energy_standard": "cspf",
            "energy_label": "CSPF",
        }, headers=admin_headers)
        assert r.status_code == 200, f"创建市场失败: {r.text}"
        data = r.json()
        assert data["code"] == "TEST"
        assert data["name"] == "TestMarket"

    def test_02_create_energy_level(self, client, admin_headers):
        """新增能效等级"""
        # 确保市场存在
        client.post("/api/pm/markets", json={
            "code": "TEST", "name": "TestMarket",
        }, headers=admin_headers)

        r = client.post("/api/pm/markets/TEST/energy-levels", json={
            "level_name": "一级",
            "sort_order": 1,
            "seer_min": 6.0,
            "eer_min": 3.5,
            "cspf_min": 5.0,
            "is_primary": "true",
        }, headers=admin_headers)
        assert r.status_code == 200, f"创建能效等级失败: {r.text}"
        data = r.json()
        assert data["message"] == "新增成功"
        assert "id" in data
        assert isinstance(data["id"], int)

    def test_03_list_energy_levels(self, client, admin_headers):
        """列出市场的能效等级"""
        # 确保市场存在
        client.post("/api/pm/markets", json={
            "code": "TEST", "name": "TestMarket",
        }, headers=admin_headers)

        # 创建两个等级
        client.post("/api/pm/markets/TEST/energy-levels", json={
            "level_name": "一级", "sort_order": 1, "seer_min": 6.0,
        }, headers=admin_headers)
        client.post("/api/pm/markets/TEST/energy-levels", json={
            "level_name": "二级", "sort_order": 2, "seer_min": 5.0,
        }, headers=admin_headers)

        r = client.get("/api/pm/markets/TEST/energy-levels", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 2

        # 验证字段完整
        level = data[0]
        assert "id" in level
        assert "market_code" in level
        assert "level_name" in level
        assert "sort_order" in level
        assert "seer_min" in level
        assert "eer_min" in level
        assert "cspf_min" in level
        assert "is_primary" in level
        assert level["market_code"] == "TEST"

        # 验证按 sort_order 升序排列
        assert data[0]["sort_order"] <= data[-1]["sort_order"]

    def test_04_update_energy_level(self, client, admin_headers):
        """更新能效等级"""
        # 确保市场存在
        client.post("/api/pm/markets", json={
            "code": "TEST", "name": "TestMarket",
        }, headers=admin_headers)

        # 创建一个等级
        r = client.post("/api/pm/markets/TEST/energy-levels", json={
            "level_name": "初始等级",
            "sort_order": 5,
            "is_primary": "false",
        }, headers=admin_headers)
        level_id = r.json()["id"]

        # 更新部分字段
        r = client.put(f"/api/pm/markets/TEST/energy-levels/{level_id}", json={
            "level_name": "Grade A",
            "is_primary": "true",
            "seer_min": 6.5,
        }, headers=admin_headers)
        assert r.status_code == 200, f"更新能效等级失败: {r.text}"
        assert r.json()["message"] == "更新成功"

        # 验证更新结果
        r = client.get("/api/pm/markets/TEST/energy-levels", headers=admin_headers)
        updated = [e for e in r.json() if e["id"] == level_id][0]
        assert updated["level_name"] == "Grade A"
        assert updated["is_primary"] == "true"
        assert updated["seer_min"] == 6.5
        # 未更新的字段应保持不变
        assert updated["sort_order"] == 5

    def test_05_delete_energy_level(self, client, admin_headers):
        """删除能效等级"""
        # 确保市场存在
        client.post("/api/pm/markets", json={
            "code": "TEST", "name": "TestMarket",
        }, headers=admin_headers)

        # 创建一个等级
        r = client.post("/api/pm/markets/TEST/energy-levels", json={
            "level_name": "待删除",
            "sort_order": 99,
        }, headers=admin_headers)
        level_id = r.json()["id"]

        # 删除
        r = client.delete(f"/api/pm/markets/TEST/energy-levels/{level_id}", headers=admin_headers)
        assert r.status_code == 200, f"删除能效等级失败: {r.text}"
        assert r.json()["message"] == "删除成功"

        # 验证已删除
        r = client.get("/api/pm/markets/TEST/energy-levels", headers=admin_headers)
        ids = [e["id"] for e in r.json()]
        assert level_id not in ids

    def test_06_list_non_existent_market(self, client, admin_headers):
        """获取不存在市场的能效等级应返回空列表"""
        r = client.get("/api/pm/markets/NONEXIST/energy-levels", headers=admin_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_07_delete_non_existent_level(self, client, admin_headers):
        """删除不存在的能效等级应返回404"""
        r = client.delete("/api/pm/markets/TEST/energy-levels/99999", headers=admin_headers)
        assert r.status_code == 404
        assert "能效等级不存在" in r.json().get("detail", "")

    def test_08_update_non_existent_level(self, client, admin_headers):
        """更新不存在的能效等级应返回404"""
        r = client.put("/api/pm/markets/TEST/energy-levels/99999", json={
            "level_name": "不应存在",
        }, headers=admin_headers)
        assert r.status_code == 404
        assert "能效等级不存在" in r.json().get("detail", "")
