"""P2-T1: ChangeImpactRule CRUD API - 集成测试"""
import pytest
from fastapi.testclient import TestClient


class TestChangeImpactRules:
    """验证变更影响规则 CRUD 主要流程"""

    RULE_ENDPOINT = "/api/s2/change-impact/rules"
    RECORDS_ENDPOINT = "/api/s2/change-impact/records"

    def test_create_rule(self, client, admin_headers):
        """创建一条规则"""
        payload = {
            "name": "压缩机变更→影响CE/CB",
            "description": "当压缩机发生变更时，CE和CB认证需要重新评估",
            "trigger_type": "part_category",
            "trigger_value": "compressor",
            "affected_cert_types": '["CE","CB"]',
            "impact_level": "high",
            "is_active": True,
        }
        r = client.post(self.RULE_ENDPOINT, json=payload, headers=admin_headers)
        assert r.status_code == 201, f"创建失败: {r.text}"
        data = r.json()
        assert data["name"] == payload["name"]
        assert data["trigger_type"] == "part_category"
        assert data["id"] > 0
        return data

    def test_list_rules_with_pagination(self, client, admin_headers):
        """分页查询规则列表"""
        # 先创建两条
        for i in range(2):
            client.post(
                self.RULE_ENDPOINT,
                json={
                    "name": f"规则{i}",
                    "trigger_type": "material_type",
                    "trigger_value": f"val{i}",
                    "affected_cert_types": '["CE"]',
                    "impact_level": "medium",
                    "is_active": True,
                },
                headers=admin_headers,
            )
        r = client.get(self.RULE_ENDPOINT, headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "items" in data
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["items"]) >= 2

        # 测试分页参数
        r2 = client.get(
            self.RULE_ENDPOINT,
            params={"page": 1, "page_size": 1},
            headers=admin_headers,
        )
        assert r2.status_code == 200
        assert len(r2.json()["items"]) == 1

        # 测试 filtering
        r3 = client.get(
            self.RULE_ENDPOINT,
            params={"name": "规则0"},
            headers=admin_headers,
        )
        assert r3.status_code == 200
        assert len(r3.json()["items"]) >= 1
        assert r3.json()["items"][0]["name"] == "规则0"

    def test_update_rule(self, client, admin_headers):
        """创建→更新规则"""
        # 先创建
        create_r = client.post(
            self.RULE_ENDPOINT,
            json={
                "name": "原始规则",
                "trigger_type": "part_category",
                "trigger_value": "original",
                "affected_cert_types": '["CE"]',
                "impact_level": "low",
                "is_active": True,
            },
            headers=admin_headers,
        )
        assert create_r.status_code == 201
        rule_id = create_r.json()["id"]

        # 更新
        update_payload = {
            "name": "更新后的规则",
            "impact_level": "high",
            "is_active": False,
        }
        r = client.put(
            f"{self.RULE_ENDPOINT}/{rule_id}",
            json=update_payload,
            headers=admin_headers,
        )
        assert r.status_code == 200, f"更新失败: {r.text}"
        data = r.json()
        assert data["name"] == "更新后的规则"
        assert data["impact_level"] == "high"
        assert data["is_active"] is False
        # 未更新的字段保持不变
        assert data["trigger_value"] == "original"

    def test_delete_rule(self, client, admin_headers):
        """创建→删除→验证不存在"""
        # 先创建
        create_r = client.post(
            self.RULE_ENDPOINT,
            json={
                "name": "待删除规则",
                "trigger_type": "cdf_type",
                "trigger_value": "cdf_item",
                "affected_cert_types": '["CB"]',
                "impact_level": "critical",
                "is_active": True,
            },
            headers=admin_headers,
        )
        assert create_r.status_code == 201
        rule_id = create_r.json()["id"]

        # 删除
        r = client.delete(
            f"{self.RULE_ENDPOINT}/{rule_id}",
            headers=admin_headers,
        )
        assert r.status_code == 200, f"删除失败: {r.text}"
        assert r.json()["message"] == "删除成功"
        assert r.json()["id"] == rule_id

        # 验证已删除
        r2 = client.put(
            f"{self.RULE_ENDPOINT}/{rule_id}",
            json={"name": "不应存在"},
            headers=admin_headers,
        )
        assert r2.status_code == 404

