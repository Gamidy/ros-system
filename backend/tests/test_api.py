"""ROS API基础测试 — 使用conftest共享fixture"""
import pytest


class TestHealth:
    """第1轮: 健康检查"""
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json()["app"] == "ROS (R&D Operations System)"


class TestAuth:
    """第2轮: 认证测试"""
    def test_register_and_login(self, client):
        r = client.post("/api/auth/register", json={
            "username": "testuser", "password": "Test1234!", "role": "engineer"
        })
        assert r.status_code == 200
        assert r.json()["username"] == "testuser"
        r = client.post("/api/auth/login", json={
            "username": "testuser", "password": "Test1234!"
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_wrong_password(self, client):
        client.post("/api/auth/register", json={
            "username": "testuser", "password": "Test1234!"
        })
        r = client.post("/api/auth/login", json={
            "username": "testuser", "password": "wrong"
        })
        assert r.status_code == 401

    def test_get_me(self, client):
        client.post("/api/auth/register", json={
            "username": "testuser", "password": "Test1234!"
        })
        r = client.post("/api/auth/login", json={
            "username": "testuser", "password": "Test1234!"
        })
        token = r.json()["access_token"]
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["username"] == "testuser"

    def test_duplicate_username(self, client):
        client.post("/api/auth/register", json={
            "username": "dupuser", "password": "Test1234!"
        })
        r = client.post("/api/auth/register", json={
            "username": "dupuser", "password": "Test1234!"
        })
        assert r.status_code == 400

    def test_weak_password_rejected(self, client):
        """安全加固验证：弱密码应被拒绝"""
        r = client.post("/api/auth/register", json={
            "username": "weakpwd", "password": "123456", "role": "engineer"
        })
        assert r.status_code in (400, 422), f"弱密码应被拒绝: {r.text}"

    def test_login_admin_cannot_register_as_admin(self, client, admin_headers):
        """admin用户可以创建admin角色"""
        r = client.post("/api/auth/register", json={
            "username": "newadmin",
            "password": "NewAdmin123!",
            "role": "admin",
        }, headers=admin_headers)
        assert r.status_code == 200


class TestProducts:
    """第3-4轮: 产品主线测试"""
    def test_create_platform(self, client, admin_headers):
        r = client.post("/api/products/platforms", json={
            "code": "IDU900", "name": "室内机900平台", "platform_type": "IDU"
        }, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["code"] == "IDU900"

    def test_create_product(self, client, admin_headers):
        rp = client.post("/api/products/platforms", json={
            "code": "IDU900", "name": "室内机900平台", "platform_type": "IDU"
        }, headers=admin_headers)
        pid = rp.json()["id"]
        r = client.post("/api/products", json={
            "code": "EU-09K", "name": "EU系列09K产品", "platform_id": pid
        }, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["code"] == "EU-09K"

    def test_create_version(self, client, admin_headers):
        rp = client.post("/api/products/platforms", json={
            "code": "IDU900", "name": "室内机900平台", "platform_type": "IDU"
        }, headers=admin_headers)
        pid = rp.json()["id"]
        rp2 = client.post("/api/products", json={
            "code": "EU-09K", "name": "EU系列09K产品", "platform_id": pid
        }, headers=admin_headers)
        prod_id = rp2.json()["id"]
        r = client.post(f"/api/products/{prod_id}/versions", json={
            "version_no": "V1.0", "reason": "初始版本"
        }, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["version_no"] == "V1.0"

    def test_version_lifecycle(self, client, admin_headers):
        rp = client.post("/api/products/platforms", json={
            "code": "IDU900", "name": "室内机900平台", "platform_type": "IDU"
        }, headers=admin_headers)
        pid = rp.json()["id"]
        rp2 = client.post("/api/products", json={
            "code": "EU-09K", "name": "EU系列09K产品", "platform_id": pid
        }, headers=admin_headers)
        prod_id = rp2.json()["id"]
        rv = client.post(f"/api/products/{prod_id}/versions", json={
            "version_no": "V1.0", "reason": "初始版本"
        }, headers=admin_headers)
        vid = rv.json()["id"]
        for status in ["developing", "released", "production"]:
            r = client.patch(f"/api/products/versions/{vid}/status", json={"status": status}, headers=admin_headers)
            assert r.status_code == 200
            assert r.json()["status"] == status

    def test_product_not_found(self, client, admin_headers):
        r = client.get("/api/products/999", headers=admin_headers)
        assert r.status_code == 404


class TestBOM:
    """第5-6轮: BOM物料测试"""
    def test_create_part(self, client, admin_headers):
        r = client.post("/api/bom/parts", json={
            "part_no": "1010010001", "name": "压缩机A型", "unit": "台"
        }, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["part_no"] == "1010010001"

    def test_duplicate_part_no(self, client, admin_headers):
        client.post("/api/bom/parts", json={
            "part_no": "1010010001", "name": "压缩机A型"
        }, headers=admin_headers)
        r = client.post("/api/bom/parts", json={
            "part_no": "1010010001", "name": "重复压缩机"
        }, headers=admin_headers)
        assert r.status_code == 400

    def test_create_bom(self, client, admin_headers):
        r = client.post("/api/bom", json={
            "bom_no": "BOM-EU-09K-V1", "product_code": "EU-09K", "bom_type": "EBOM"
        }, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["bom_no"] == "BOM-EU-09K-V1"


class TestProjects:
    """第7-8轮: 项目管理测试"""

    def _create_project(self, client, admin_headers, pclass="A"):
        from datetime import date, timedelta
        r = client.post("/api/projects", json={
            "code": f"P2026-test",
            "name": "EU-09K新产品开发",
            "project_class": pclass, "source": "年度产品规划",
            "target_end_date": str(date.today() + timedelta(days=180)),
        }, headers=admin_headers)
        assert r.status_code == 200
        return r.json()

    def test_create_project(self, client, admin_headers):
        data = self._create_project(client, admin_headers)
        assert data["code"].startswith("P2026-")

    def test_project_gates(self, client, admin_headers):
        proj = self._create_project(client, admin_headers)
        pid = proj["id"]
        r = client.get(f"/api/projects/{pid}/gates", headers=admin_headers)
        assert r.status_code == 200
        gates = r.json()
        assert len(gates) >= 9

    def test_update_gate(self, client, admin_headers):
        proj = self._create_project(client, admin_headers)
        pid = proj["id"]
        r = client.patch(
            f"/api/projects/{pid}/gates/M1?status=passed&decision=方案评审通过",
            headers=admin_headers
        )
        assert r.status_code == 200


class TestTests:
    """第9轮: 测试/实验"""
    def test_create_test_request(self, client, admin_headers):
        r = client.post("/api/tests", json={
            "title": "EU-09K制冷性能测试",
            "test_type": "性能",
            "requester": "张工"
        }, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["request_no"].startswith("TR-")

    def test_update_ng_count(self, client, admin_headers):
        r = client.post("/api/tests", json={
            "title": "NG测试", "test_type": "可靠性",
            "requester": "张工"
        }, headers=admin_headers)
        tid = r.json()["id"]
        # Step through valid state transitions: draft→submitted→testing→done
        client.patch(f"/api/tests/{tid}?status=submitted", headers=admin_headers)
        client.patch(f"/api/tests/{tid}?status=testing", headers=admin_headers)
        r2 = client.patch(f"/api/tests/{tid}?status=done&result_summary=测试完成，2项不合格", headers=admin_headers)
        assert r2.status_code == 200


class TestDashboard:
    """第10轮: 驾驶舱/预警"""
    def test_dashboard_summary(self, client, admin_headers):
        r = client.get("/api/dashboard/summary", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert "total_products" in data.get("layer1_system_health", {})

    def test_check_overdue_alert(self, client, admin_headers):
        r = client.get("/api/dashboard/alerts", headers=admin_headers)
        assert r.status_code == 200
