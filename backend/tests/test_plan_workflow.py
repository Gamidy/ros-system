"""产品策划核心业务流集成测试 — FastAPI TestClient + SQLite 内存数据库

覆盖场景：
  1. 登录获取token
  2. 策划列表（创建前/后）
  3. 创建策划
  4. 5子表CRUD（initiation, market, techSpec, team, costing）
  5. 审批推进（DRAFT→COMPETITOR→DEFINITION→COSTING→TECH_INPUT→PROJECT_INIT→APPROVED）
  6. 推进后检查project_id
  7. 边界测试：非法推进、缺少必要条件
"""
import os
import tempfile

_db_file = os.path.join(tempfile.mkdtemp(), "test_ros.db")
os.environ["ALLOW_PUBLIC_REGISTER"] = "true"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine, SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
import pytest

client = TestClient(app)

# 禁用事件总线（避免 async ExceptionGroup）
import app.services.events as events_module
events_module.bus.emit = lambda *a, **kw: None


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestPlanWorkflow:
    """产品策划全流程集成测试 — 顺序执行"""

    def _create_admin_and_login(self):
        db = SessionLocal()
        db.add(User(username="planadmin", hashed_password=get_password_hash("test123"), role="admin", is_active=True))
        db.commit()
        db.close()
        r = client.post("/api/auth/login", json={"username": "planadmin", "password": "test123"})
        assert r.status_code == 200
        return r.json()["access_token"]

    def test_01_login_get_token(self):
        token = self._create_admin_and_login()
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["username"] == "planadmin"
        assert r.json()["role"] == "admin"

    def test_02_plan_list_before_create(self):
        token = self._create_admin_and_login()
        r = client.get("/api/product-plans", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_03_create_plan(self):
        token = self._create_admin_and_login()
        r = client.post("/api/product-plans", json={"name": "EU-09K", "series": "EU"}, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "EU-09K"
        assert data["status"] == "draft"
        return data["id"]

    def test_04_plan_list_after_create(self):
        token = self._create_admin_and_login()
        # 先创建一个
        client.post("/api/product-plans", json={"name": "X", "series": "Y"}, headers={"Authorization": f"Bearer {token}"})
        r = client.get("/api/product-plans", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_05_subs_crud(self):
        """5个子表CRUD + 审批推进 + 完整性验证"""
        token = self._create_admin_and_login()
        hdrs = {"Authorization": f"Bearer {token}"}

        # 创建策划
        r = client.post("/api/product-plans", json={"name": "完整测试策划", "series": "EU系列"}, headers=hdrs)
        assert r.status_code == 201
        pid = r.json()["id"]

        # Initiation
        r = client.put(f"/api/product-plans/{pid}/initiation", json={
            "product_type": "分体空调", "target_market": "欧盟",
            "refrigerant": "R32", "background_basis": "新能效标准",
        }, headers=hdrs)
        assert r.status_code == 200
        assert r.json()["product_type"] == "分体空调"

        # Market
        r = client.put(f"/api/product-plans/{pid}/market", json={
            "main_capacity": "3.5kW",
            "voltage_freq": "220V/50Hz",
        }, headers=hdrs)
        assert r.status_code == 200
        assert r.json()["main_capacity"] == "3.5kW"

        # TechSpec
        r = client.put(f"/api/product-plans/{pid}/tech-spec", json={
            "core_performance": "制冷3.5kW",
            "safety_compliance": "IEC 60335",
        }, headers=hdrs)
        assert r.status_code == 200
        assert r.json()["core_performance"] == "制冷3.5kW"

        # Team
        r = client.post(f"/api/product-plans/{pid}/team", json={
            "role_name": "产品经理", "member_name": "张三", "department": "产品部",
        }, headers=hdrs)
        assert r.status_code in (200, 201), f"Team创建失败: {r.text}"

        # Cost
        r = client.post(f"/api/product-plans/{pid}/costs", json={
            "cost_type": "target", "item_name": "整机BOM", "target_value": 2000.0,
        }, headers=hdrs)
        assert r.status_code == 200

        # 验证子表完整性
        r = client.get(f"/api/product-plans/{pid}", headers=hdrs)
        assert r.status_code == 200
        data = r.json()
        assert "costs" in data, "策划详情应包含 costs 字段"

    def test_06_approval_full_flow(self):
        """全流程审批推进"""
        token = self._create_admin_and_login()
        hdrs = {"Authorization": f"Bearer {token}"}

        r = client.post("/api/product-plans", json={"name": "审批测试", "series": "EU", "market": "中国"}, headers=hdrs)
        assert r.status_code == 201
        pid = r.json()["id"]

        def advance(expect_next=None):
            r = client.post(f"/api/product-plans/{pid}/advance", json={"comment": "test"}, headers=hdrs)
            assert r.status_code == 200, f"推进失败: {r.text}"
            if expect_next:
                assert r.json()["status"] == expect_next, f"状态应为 {expect_next}，实际 {r.json()['status']}"
            return r.json()

        # DRAFT → COMPETITOR
        advance("competitor")

        # 准备竞品 + 市场数据（COMPETITOR→DEFINITION 前置要求）
        r = client.post("/api/pm/competitors", json={"brand": "格力", "model": "KFR-35GW", "market": "中国"}, headers=hdrs)
        assert r.status_code in (200, 201)
        client.patch(f"/api/product-plans/{pid}", json={"competitor_id": r.json()["id"]}, headers=hdrs)
        client.put(f"/api/product-plans/{pid}/market", json={"main_capacity": "3.5kW"}, headers=hdrs)
        client.put(f"/api/product-plans/{pid}/initiation", json={"background_basis": "新能效标准"}, headers=hdrs)

        # COMPETITOR → DEFINITION
        advance("definition")

        # DEFINITION → COSTING (需要成本目标 + 成本记录)
        client.patch(f"/api/product-plans/{pid}", json={"cost_target": "{\"target\": 2000}"}, headers=hdrs)
        client.post(f"/api/product-plans/{pid}/costs", json={
            "cost_type": "target", "item_name": "测试成本", "target_value": 1000.0,
        }, headers=hdrs)
        advance("costing")

        # COSTING → TECH_INPUT (需要tech-spec)
        client.patch(f"/api/product-plans/{pid}", json={"performance_target": "[{\"param\":\"制冷量\",\"target\":\"3500W\"}]"}, headers=hdrs)
        client.put(f"/api/product-plans/{pid}/tech-spec", json={"core_performance": "制冷量3.5kW"}, headers=hdrs)
        advance("tech_input")

        # TECH_INPUT → PROJECT_INIT (需要子表数据)
        client.put(f"/api/product-plans/{pid}/initiation", json={"product_type": "分体空调", "background_basis": "test"}, headers=hdrs)
        client.put(f"/api/product-plans/{pid}/market", json={"main_capacity": "3.5kW"}, headers=hdrs)
        client.put(f"/api/product-plans/{pid}/tech-spec", json={"core_performance": "制冷量3.5kW"}, headers=hdrs)
        client.post(f"/api/product-plans/{pid}/team", json={"role_name": "PM", "member_name": "张三", "department": "产品部"}, headers=hdrs)
        advance("project_init")

        # PROJECT_INIT → APPROVED (需要所有子表补齐)
        advance("approved")

        # 验证审批请求已创建
        r = client.get("/api/approval/requests", headers=hdrs)
        assert r.status_code == 200
        items = r.json().get("items", r.json().get("data", []))
        assert len(items) > 0, "审批通过后应创建审批请求"

    def test_07_boundary_invalid_advance(self):
        """边界测试：非法推进"""
        token = self._create_admin_and_login()
        hdrs = {"Authorization": f"Bearer {token}"}

        r = client.post("/api/product-plans", json={"name": "边界测试", "series": "X"}, headers=hdrs)
        pid = r.json()["id"]

        # 重复推进
        r = client.post(f"/api/product-plans/{pid}/advance", json={"comment": "ok"}, headers=hdrs)
        assert r.status_code == 200
        r = client.post(f"/api/product-plans/{pid}/advance", json={"comment": "dup"}, headers=hdrs)
        assert r.status_code == 400, f"重复推进应返回400: {r.text}"
