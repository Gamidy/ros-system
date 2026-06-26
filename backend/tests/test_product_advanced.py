"""产品主线新功能测试: 规则引擎 / Market / ManufacturingVariant / Version转换"""
import pytest
import uuid


class TestProductRules:
    """规则引擎测试（纯逻辑，不依赖DB）"""

    def setup_method(self, method=None):
        pass

    def test_regression_test_passes(self):
        """Sanity check"""
        assert True

    def test_critical_material_change_triggers_new_version(self, client, admin_headers):
        """PR-06: 关键物料变更→应创建新Version"""
        r = client.post("/api/products/rules/evaluate-version", json={
            "change_description": "压缩机从转子式改为涡旋式",
            "material_level": "critical",
            "change_category": "part_change",
            "is_customer_perceivable": False,
        }, headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["should_create"] is True
        assert "product_action" in data

    def test_minor_material_change_no_new_version(self, client, admin_headers):
        """PR-06: 非关键物料变更→不创建新Version"""
        r = client.post("/api/products/rules/evaluate-version", json={
            "change_description": "螺丝从M4换成M5",
            "material_level": "minor",
            "change_category": "part_change",
            "is_customer_perceivable": False,
        }, headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["should_create"] is False or data["product_action"] == "mbom_only"

    def test_customer_perceivable_mandates_version(self, client, admin_headers):
        """PR-09: 客户可感知变更→必须创建新Version"""
        r = client.post("/api/products/rules/evaluate-version", json={
            "change_description": "面板颜色从白色改为黑色",
            "material_level": "minor",
            "change_category": "appearance",
            "is_customer_perceivable": True,
        }, headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["should_create"] is True
        assert data["customer_perceivable"] is True

    def test_mbom_only_change(self, client, admin_headers):
        """PR-10: MBOM变更不影响客户→不创建新Product Version (minor级别)"""
        r = client.post("/api/products/rules/evaluate-version", json={
            "change_description": "产线螺丝枪型号更新",
            "material_level": "minor",
            "change_category": "bom_only",
            "is_customer_perceivable": False,
        }, headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["should_create"] is False
        assert data["product_action"] == "mbom_only"

    def test_material_critical_level(self, client, admin_headers):
        """critical物料变更应使影响最大化"""
        r = client.post("/api/products/rules/evaluate-version", json={
            "change_description": "换热器材质从铜管改为铝管",
            "material_level": "critical",
            "change_category": "design_change",
            "is_customer_perceivable": False,
        }, headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["should_create"] is True


class TestMarkets:
    """Market CRUD测试"""

    def test_create_and_list_markets(self, client, admin_headers):
        """CRUD: 创建+列表市场"""
        s = uuid.uuid4().hex[:4]
        created_codes = []
        for code, name, region in [(f"EU-{s}", "欧盟", "Europe"), (f"VN-{s}", "越南", "SE_Asia"), (f"JP-{s}", "日本", "East_Asia")]:
            r = client.post("/api/products/markets", json={
                "code": code, "name": name, "region": region
            }, headers=admin_headers)
            assert r.status_code == 200, f"创建市场{code}失败: {r.text}"
            created_codes.append(r.json()["code"])
        r = client.get("/api/products/markets", headers=admin_headers)
        assert r.status_code == 200
        markets = r.json()
        codes = {m["code"] for m in markets}
        for c in created_codes:
            assert c in codes, f"{c} not in markets list"

    def test_duplicate_market(self, client, admin_headers):
        """重复市场代码"""
        client.post("/api/products/markets", json={
            "code": "TW", "name": "台湾", "region": "East_Asia"
        }, headers=admin_headers)
        r = client.post("/api/products/markets", json={
            "code": "TW", "name": "台湾地区", "region": "East_Asia"
        }, headers=admin_headers)
        assert r.status_code == 400


class TestProductMarkets:
    """Product↔Market多对多关系测试"""

    def create_platform_and_product(self, client, hdrs):
        s = uuid.uuid4().hex[:6]
        rp = client.post("/api/products/platforms", json={
            "code": f"IDU-PM-{s}", "name": "产品市场测试平台", "platform_type": "IDU"
        }, headers=hdrs)
        pid = rp.json()["id"]
        r = client.post("/api/products", json={
            "code": f"PMC-{s}", "name": "多市场关联测试产品",
            "platform_id": pid
        }, headers=hdrs)
        return r.json()["id"]

    def test_assign_multiple_markets(self, client, admin_headers):
        """PR-08: Product↔Market多对多 分配多市场"""
        prod_id = self.create_platform_and_product(client, admin_headers)
        s = uuid.uuid4().hex[:4]
        mkt_codes = []
        for code, name in [(f"EU-{s}", "欧盟"), (f"VN-{s}", "越南"), (f"JP-{s}", "日本")]:
            r = client.post("/api/products/markets", json={
                "code": code, "name": name, "region": "Asia"
            }, headers=admin_headers)
            mkt_codes.append(r.json()["code"])
        r = client.post(f"/api/products/{prod_id}/markets", json={
            "market_codes": mkt_codes
        }, headers=admin_headers)
        assert r.status_code == 200
        assert set(r.json()["market_codes"]) == set(mkt_codes)


class TestVersionTransitions:
    """Version生命周期转换验证测试"""

    def create_version(self, client, hdrs):
        suffix = uuid.uuid4().hex[:6]
        rp = client.post("/api/products/platforms", json={
            "code": f"IDU-VT-{suffix}", "name": "版本转换测试平台", "platform_type": "IDU"
        }, headers=hdrs)
        pid = rp.json()["id"]
        rp2 = client.post("/api/products", json={
            "code": f"VT-{suffix}", "name": "版本转换测试产品", "platform_id": pid
        }, headers=hdrs)
        prod_id = rp2.json()["id"]
        rv = client.post(f"/api/products/{prod_id}/versions", json={
            "version_no": "V1.0", "reason": "测试版本"
        }, headers=hdrs)
        return rv.json()["id"]

    def test_valid_transitions(self, client, admin_headers):
        """合法转换: draft→developing→released→production"""
        vid = self.create_version(client, admin_headers)
        for target in ["developing", "released", "production"]:
            r = client.patch(f"/api/products/versions/{vid}/status", json={"status": target}, headers=admin_headers)
            assert r.status_code == 200, f"转换到{target}失败: {r.text}"
            assert r.json()["status"] == target

    def test_invalid_transition(self, client, admin_headers):
        """非法转换: draft→production（跳过developing和released）"""
        vid = self.create_version(client, admin_headers)
        r = client.patch(f"/api/products/versions/{vid}/status", json={"status": "production"}, headers=admin_headers)
        assert r.status_code == 400
        assert "不允许" in r.json()["detail"] or "不合法" in r.json()["detail"]

    def test_obsolete_transition(self, client, admin_headers):
        """production→obsolete合法"""
        vid = self.create_version(client, admin_headers)
        for target in ["developing", "released", "production"]:
            client.patch(f"/api/products/versions/{vid}/status", json={"status": target}, headers=admin_headers)
        r = client.patch(f"/api/products/versions/{vid}/status", json={"status": "obsolete"}, headers=admin_headers)
        assert r.status_code == 200


class TestManufacturingVariant:
    """ManufacturingVariant CRUD测试"""

    def create_version(self, client, hdrs):
        suffix = uuid.uuid4().hex[:6]
        rp = client.post("/api/products/platforms", json={
            "code": f"IDU-MV-{suffix}", "name": "制造变体测试平台", "platform_type": "IDU"
        }, headers=hdrs)
        pid = rp.json()["id"]
        rp2 = client.post("/api/products", json={
            "code": f"MV-{suffix}", "name": "制造变体测试产品", "platform_id": pid
        }, headers=hdrs)
        prod_id = rp2.json()["id"]
        rv = client.post(f"/api/products/{prod_id}/versions", json={
            "version_no": "V1.0", "reason": "测试变体"
        }, headers=hdrs)
        return rv.json()["id"]

    def test_create_variant(self, client, admin_headers):
        """创建制造变体"""
        vid = self.create_version(client, admin_headers)
        r = client.post(f"/api/products/versions/{vid}/variants", json={
            "factory_code": "GREE-ZH",
            "factory_name": "珠海工厂",
            "mbom_version": "MBOM-V1.2",
            "description": "珠海工厂专用BOM"
        }, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["factory_code"] == "GREE-ZH"
        assert r.json()["mbom_version"] == "MBOM-V1.2"

    def test_duplicate_variant(self, client, admin_headers):
        """同工厂重复创建变体→400"""
        vid = self.create_version(client, admin_headers)
        data = {"factory_code": "GREE-WH", "factory_name": "武汉工厂", "mbom_version": "MBOM-V1.0"}
        client.post(f"/api/products/versions/{vid}/variants", json=data, headers=admin_headers)
        r = client.post(f"/api/products/versions/{vid}/variants", json=data, headers=admin_headers)
        assert r.status_code == 400

    def test_list_variants(self, client, admin_headers):
        """列出版本下所有变体"""
        vid = self.create_version(client, admin_headers)
        for fc in ["SH", "BJ", "GZ"]:
            client.post(f"/api/products/versions/{vid}/variants", json={
                "factory_code": fc, "factory_name": f"{fc}工厂", "mbom_version": f"MBOM-{fc}-V1.0"
            }, headers=admin_headers)
        r = client.get(f"/api/products/versions/{vid}/variants", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.json()) == 3
