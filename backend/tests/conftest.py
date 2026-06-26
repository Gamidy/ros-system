"""ROS测试共用fixture"""
import os
import tempfile

# 必须在任何app导入前设置环境变量
_db_file = os.path.join(tempfile.mkdtemp(), "test_ros.db")
os.environ.setdefault("ALLOW_PUBLIC_REGISTER", "true")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_file}")

# 禁用事件总线（避免 async ExceptionGroup）
import app.services.events as events_module
events_module.bus.emit = lambda *a, **kw: None
events_module.bus.emit_async = lambda *a, **kw: None

# 测试环境下禁用限流器
import app.middleware.rate_limit as rate_limit_mod
rate_limit_mod.IP_LIMIT = 999999
rate_limit_mod.USER_LIMIT = 999999

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine, SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
import pytest


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前重建数据库"""
    Base.metadata.create_all(bind=engine)
    yield
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        engine.dispose()
        db_path = _db_file
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.fixture
def client():
    """FastAPI测试客户端"""
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """创建admin用户（直接插DB bypass注册限制）并返回Bearer token"""
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.core.security import get_password_hash
    db = SessionLocal()
    admin = User(
        username="admintest",
        hashed_password=get_password_hash("Admin1234!"),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.close()
    # 登录获取token
    r = client.post("/api/auth/login", json={
        "username": "admintest",
        "password": "Admin1234!",
    })
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    """admin认证头"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def engineer_token(client):
    """创建engineer用户并返回token"""
    r = client.post("/api/auth/register", json={
        "username": "engtest",
        "password": "Engineer12!",
        "role": "engineer",
    })
    assert r.status_code == 200, f"注册engineer失败: {r.text}"
    r = client.post("/api/auth/login", json={
        "username": "engtest",
        "password": "Engineer12!",
    })
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture
def engineer_headers(engineer_token):
    return {"Authorization": f"Bearer {engineer_token}"}


VALID_PASSWORD = "Test1234!"
WEAK_PASSWORD = "test123"
