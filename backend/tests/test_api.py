"""ROS API测试 - 10轮测试"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine, SessionLocal

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    db = SessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


class TestHealth:
    """第1轮: 健康检查"""
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json()["app"] == "ROS (R&D Operations System)"


class TestAuth:
    """第2轮: 认证测试"""
    def test_register_and_login(self):
        r = client.post("/api/auth/register", json={
            "username": "testuser", "password": "test123", "role": "engineer"
        })
        assert r.status_code == 200
        assert r.json()["username"] == "testuser"
        r = client.post("/api/auth/login", json={
            "username": "testuser", "password": "test123"
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_wrong_password(self):
        client.post("/api/auth/register", json={
            "username": "testuser", "password": "test123"
        })
        r = client.post("/api/auth/login", json={
            "username": "testuser", "password": "wrong"
        })
        assert r.status_code == 401

    def test_get_me(self):
        client.post("/api/auth/register", json={
            "username": "testuser", "password": "test123"
        })
        r = client.post("/api/auth/login", json={
            "username": "testuser", "password": "test123"
        })
        token = r.json()["access_token"]
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["username"] == "testuser"

    def test_duplicate_username(self):
        client.post("/api/auth/register", json={
            "username": "dupuser", "password": "test123"
        })
        r = client.post("/api/auth/register", json={
            "username": "dupuser", "password": "test123"
        })
        assert r.status_code == 400


class TestProducts:
    """第3-4轮: 产品主线测试"""

    def setup_method(self):
        client.post("/api/auth/register", json={
            "username": "produser", "password": "test123", "role": "admin"
        })
        r = client.post("/api/auth/login", json={
            "username": "produser", "password": "test123"
        })
        self.token = r.json()["access_token"]

    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def test_create_platform(self):
        r = client.post("/api/products/platforms", json={
            "code": "IDU900", "name": "室内机900平台", "platform_type": "IDU"
        }, headers=self.headers())
        assert r.status_code == 200
        assert r.json()["code"] == "IDU900"

    def test_create_product(self):
        rp = client.post("/api/products/platforms", json={
            "code": "IDU900", "name": "室内机900平台", "platform_type": "IDU"
        }, headers=self.headers())
        pid = rp.json()["id"]

        r = client.post("/api/products", json={
            "code": "EU-09K", "name": "EU系列09K产品",
            "platform_id": pid
        }, headers=self.headers())
        assert r.status_code == 200
        assert r.json()["code"] == "EU-09K"

    def test_create_version(self):
        rp = client.post("/api/products/platforms", json={
            "code": "IDU900", "name": "室内机900平台", "platform_type": "IDU"
        }, headers=self.headers())
        pid = rp.json()["id"]
        rp2 = client.post("/api/products", json={
            "code": "EU-09K", "name": "EU系列09K产品",
            "platform_id": pid
        }, headers=self.headers())
        prod_id = rp2.json()["id"]

        r = client.post(f"/api/products/{prod_id}/versions", json={
            "version_no": "V1.0", "reason": "初始版本"
        }, headers=self.headers())
        assert r.status_code == 200
        assert r.json()["version_no"] == "V1.0"

    def test_version_lifecycle(self):
        rp = client.post("/api/products/platforms", json={
            "code": "IDU900", "name": "室内机900平台", "platform_type": "IDU"
        }, headers=self.headers())
        pid = rp.json()["id"]
        rp2 = client.post("/api/products", json={
            "code": "EU-09K", "name": "EU系列09K产品",
            "platform_id": pid
        }, headers=self.headers())
        prod_id = rp2.json()["id"]
        rv = client.post(f"/api/products/{prod_id}/versions", json={
            "version_no": "V1.0", "reason": "初始版本"
        }, headers=self.headers())
        vid = rv.json()["id"]

        for status in ["developing", "released", "production"]:
            r = client.patch(f"/api/products/versions/{vid}/status", json={"status": status}, headers=self.headers())
            assert r.status_code == 200
            assert r.json()["status"] == status

    def test_product_not_found(self):
        r = client.get("/api/products/999", headers=self.headers())
        assert r.status_code == 404


class TestBOM:
    """第5-6轮: BOM物料测试"""

    def setup_method(self):
        client.post("/api/auth/register", json={
            "username": "bomuser", "password": "test123", "role": "admin"
        })
        r = client.post("/api/auth/login", json={
            "username": "bomuser", "password": "test123"
        })
        self.token = r.json()["access_token"]

    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def test_create_part(self):
        r = client.post("/api/bom/parts", json={
            "part_no": "1010010001", "name": "压缩机A型", "unit": "台"
        }, headers=self.headers())
        assert r.status_code == 200
        assert r.json()["part_no"] == "1010010001"

    def test_duplicate_part_no(self):
        client.post("/api/bom/parts", json={
            "part_no": "1010010001", "name": "压缩机A型"
        }, headers=self.headers())
        r = client.post("/api/bom/parts", json={
            "part_no": "1010010001", "name": "重复压缩机"
        }, headers=self.headers())
        assert r.status_code == 400

    def test_create_bom(self):
        r = client.post("/api/bom", json={
            "bom_no": "BOM-EU-09K-V1", "product_code": "EU-09K", "bom_type": "EBOM"
        }, headers=self.headers())
        assert r.status_code == 200
        assert r.json()["bom_no"] == "BOM-EU-09K-V1"


class TestProjects:
    """第7-8轮: 项目管理测试"""

    def setup_method(self):
        client.post("/api/auth/register", json={
            "username": "projuser", "password": "test123", "role": "manager"
        })
        r = client.post("/api/auth/login", json={
            "username": "projuser", "password": "test123"
        })
        self.token = r.json()["access_token"]

    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def _create_project(self, pclass="A"):
        from datetime import date, timedelta
        r = client.post("/api/projects", params={
            "code": f"P2026-{date.today().isoformat()}",
            "name": "EU-09K新产品开发",
            "project_class": pclass, "source": "年度产品规划",
            "target_end_date": str(date.today() + timedelta(days=180)),
        }, headers=self.headers())
        assert r.status_code == 200
        return r.json()

    def test_create_project(self):
        data = self._create_project("A")
        assert data["code"].startswith("P2026-")

    def test_project_gates(self):
        proj = self._create_project("A")
        pid = proj["id"]
        r = client.get(f"/api/projects/{pid}/gates", headers=self.headers())
        assert r.status_code == 200
        gates = r.json()
        assert len(gates) >= 9

    def test_update_gate(self):
        proj = self._create_project("A")
        pid = proj["id"]
        r = client.patch(
            f"/api/projects/{pid}/gates/M1?status=passed&decision=方案评审通过",
            headers=self.headers()
        )
        assert r.status_code == 200


class TestTests:
    """第9轮: 测试/实验"""

    def setup_method(self):
        client.post("/api/auth/register", json={
            "username": "testeng", "password": "test123", "role": "engineer"
        })
        r = client.post("/api/auth/login", json={
            "username": "testeng", "password": "test123"
        })
        self.token = r.json()["access_token"]

    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def test_create_test_request(self):
        r = client.post("/api/tests", json={
            "title": "EU-09K制冷性能测试",
            "test_type": "性能",
            "requester": "张工"
        }, headers=self.headers())
        assert r.status_code == 200
        assert r.json()["request_no"].startswith("TR-")

    def test_update_ng_count(self):
        r = client.post("/api/tests", json={
            "title": "NG测试", "test_type": "可靠性",
            "requester": "张工"
        }, headers=self.headers())
        tid = r.json()["id"]
        r2 = client.patch(f"/api/tests/{tid}?status=done&result_summary=测试完成，2项不合格", headers=self.headers())
        assert r2.status_code == 200


class TestDashboard:
    """第10轮: 驾驶舱/预警"""

    def test_dashboard_summary(self):
        r = client.get("/api/dashboard/summary")
        assert r.status_code == 200
        data = r.json()
        assert "total_products" in data

    def test_check_overdue_alert(self):
        r = client.get("/api/dashboard/alerts")
        assert r.status_code == 200
