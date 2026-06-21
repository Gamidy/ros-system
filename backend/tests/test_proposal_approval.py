"""立项审批模块测试 — 覆盖并发安全、审批人校验、状态同步"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine, SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.project import Project
from app.models.proposal_approval import ProposalApproval, ProposalParallelReviewer
from app.models.approval import ApprovalRequest, ApprovalChain, ApprovalStep

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


def _create_user(db, username, role, password="test123"):
    """直接创建用户（绕过 register，确保角色精确控制）"""
    u = User(
        username=username,
        hashed_password=get_password_hash(password),
        role=role,
        is_active=True,
        full_name=f"{role}_{username}",
    )
    db.add(u)
    db.flush()
    return u.id


def _create_project(db, owner="pmuser"):
    p = Project(
        code="PRJ-TEST-001",
        name="测试产品立项",
        project_class="B",
        owner=owner,
        is_draft=True,
        status="draft",
    )
    db.add(p)
    db.flush()
    return p.id


def _login(username="pmuser"):
    r = client.post("/api/auth/login", json={"username": username, "password": "test123"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ═════════════════════════════════════════════════
# 问题 1 测试: 审批人配置校验
# ═════════════════════════════════════════════════

class TestApproverValidation:
    """验证 _validate_approver_config 的行为"""

    def _ensure_chain(self, db):
        _ensure_proposal_chain(db)

    def test_submit_when_no_approvers_returns_400(self):
        """角色0人时提交返回400且错误信息包含角色中文名"""
        db = SessionLocal()
        try:
            pm_id = _create_user(db, "pmuser", "product_manager")
            pid = _create_project(db, "pmuser")
            db.commit()
        finally:
            db.close()

        headers = _login("pmuser")
        r = client.post("/api/pm/proposals/submit", json={"project_id": pid}, headers=headers)

        assert r.status_code == 400
        detail = r.json()["detail"]
        assert "结构模块经理" in detail or "系统模块经理" in detail or "电控工程师" in detail or "电气工程师" in detail

    def test_submit_when_duplicate_approvers_returns_400(self):
        """角色2人时提交返回400"""
        db = SessionLocal()
        try:
            pm_id = _create_user(db, "pmuser", "product_manager")
            pid = _create_project(db, "pmuser")
            # 创建2个结构模块经理
            _create_user(db, "struct1", "module_manager_struct")
            _create_user(db, "struct2", "module_manager_struct")
            # 创建其他必需角色各1个
            _create_user(db, "sys1", "module_manager_sys")
            _create_user(db, "elec_ctrl1", "electrical_control_engineer")
            _create_user(db, "elec_eng1", "electrical_engineer")
            _create_user(db, "director1", "rd_director")
            db.commit()
        finally:
            db.close()

        headers = _login("pmuser")
        r = client.post("/api/pm/proposals/submit", json={"project_id": pid}, headers=headers)

        assert r.status_code == 400
        detail = r.json()["detail"]
        assert "结构模块经理" in detail
        assert "2人" in detail

    def test_submit_with_exact_approvers_succeeds(self):
        """4角色+总监均恰好1人时提交成功且parallel_reviewers长度为4"""
        db = SessionLocal()
        try:
            pm_id = _create_user(db, "pmuser", "product_manager")
            pid = _create_project(db, "pmuser")
            # 创建恰好1个的并行审批人
            _create_user(db, "struct1", "module_manager_struct")
            _create_user(db, "sys1", "module_manager_sys")
            _create_user(db, "elec_ctrl1", "electrical_control_engineer")
            _create_user(db, "elec_eng1", "electrical_engineer")
            _create_user(db, "director1", "rd_director")
            db.commit()
        finally:
            db.close()

        headers = _login("pmuser")
        r = client.post("/api/pm/proposals/submit", json={"project_id": pid}, headers=headers)

        assert r.status_code == 200, f"Submit failed: {r.text}"
        data = r.json()
        reviewers = data["approval"]["parallel_reviewers"]
        assert len(reviewers) == 4, f"Expected 4 reviewers, got {len(reviewers)}"
        statuses = [rv["status"] for rv in reviewers]
        assert all(s == "pending" for s in statuses)


# ═════════════════════════════════════════════════
# 问题 2 测试: 并发安全
# ═════════════════════════════════════════════════

class TestConcurrentReview:
    """验证并行审批的并发安全和原子更新"""

    @pytest.fixture(autouse=True)
    def setup_approval(self):
        db = SessionLocal()
        try:
            self.pm_id = _create_user(db, "pmuser", "product_manager")
            self.pid = _create_project(db, "pmuser")
            # 创建审批用户
            self.struct_id = _create_user(db, "struct1", "module_manager_struct")
            self.sys_id = _create_user(db, "sys1", "module_manager_sys")
            self.ctrl_id = _create_user(db, "elec_ctrl1", "electrical_control_engineer")
            self.eng_id = _create_user(db, "elec_eng1", "electrical_engineer")
            _create_user(db, "director1", "rd_director")

            _ensure_proposal_chain(db)
            db.commit()
        finally:
            db.close()

        # 提交审批
        headers = _login("pmuser")
        r = client.post("/api/pm/proposals/submit", json={"project_id": self.pid}, headers=headers)
        assert r.status_code == 200
        self.approval_id = r.json()["approval"]["id"]
        yield

    def test_concurrent_reviews_both_succeed(self):
        """模拟两个不同审批人同时调用review，断言两条记录都正确落库"""
        import threading
        errors = []

        def review(user_id, action):
            try:
                # 模拟并发：每个请求独立调用
                from app.main import app as fapp
                local_client = TestClient(fapp)
                _, token = _login_for_user(user_id)
                ts = {"Authorization": f"Bearer {token}"}
                r = local_client.post(
                    f"/api/approvals/{self.approval_id}/review",
                    json={"action": action},
                    headers=ts,
                )
                if r.status_code not in (200, 400):
                    errors.append(f"User {user_id}: {r.status_code} {r.text}")
                if r.status_code == 400 and "已审批过" in r.text:
                    pass  # duplicate is ok in concurrent scenario
            except Exception as e:
                errors.append(str(e))

        def _login_for_user(user_id):
                """Retrieve the actual user from DB for login"""
                db = SessionLocal()
                try:
                    u = db.query(User).filter(User.id == user_id).first()
                    username = u.username
                finally:
                    db.close()
                r = client.post("/api/auth/login", json={"username": username, "password": "test123"})
                return 200, r.json()["access_token"]

        threads = []
        for uid in [self.struct_id, self.sys_id]:
            t = threading.Thread(target=review, args=(uid, "approved"))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent review errors: {errors}"

        # 验证两条记录都正确落库
        db = SessionLocal()
        try:
            rows = db.query(ProposalParallelReviewer).filter(
                ProposalParallelReviewer.approval_id == self.approval_id,
            ).order_by(ProposalParallelReviewer.id).all()
            statuses = [(r.user_id, r.status) for r in rows]
            assert (self.struct_id, "approved") in statuses, f"struct not approved: {statuses}"
            assert (self.sys_id, "approved") in statuses, f"sys not approved: {statuses}"
        finally:
            db.close()

    def test_duplicate_review_returns_400(self):
        """同一审批人对同一条记录重复提交审批，第二次返回400"""
        headers = _login("struct1")
        # 第一次审批
        r = client.post(
            f"/api/approvals/{self.approval_id}/review",
            json={"action": "approved"},
            headers=headers,
        )
        assert r.status_code == 200

        # 第二次重复审批
        r = client.post(
            f"/api/approvals/{self.approval_id}/review",
            json={"action": "approved"},
            headers=headers,
        )
        assert r.status_code == 400
        assert "已审批过" in r.json()["detail"]


# ═════════════════════════════════════════════════
# 问题 3 测试: 状态变更同步
# ═════════════════════════════════════════════════

class TestStatusSync:
    """验证 _change_status 同步 ApprovalRequest"""

    @pytest.fixture(autouse=True)
    def setup_approval(self):
        db = SessionLocal()
        try:
            self.pm_id = _create_user(db, "pmuser", "product_manager")
            self.pid = _create_project(db, "pmuser")
            self.struct_id = _create_user(db, "struct1", "module_manager_struct")
            self.sys_id = _create_user(db, "sys1", "module_manager_sys")
            self.ctrl_id = _create_user(db, "elec_ctrl1", "electrical_control_engineer")
            self.eng_id = _create_user(db, "elec_eng1", "electrical_engineer")
            self.director_id = _create_user(db, "director1", "rd_director")
            _ensure_proposal_chain(db)
            db.commit()
        finally:
            db.close()

        headers = _login("pmuser")
        r = client.post("/api/pm/proposals/submit", json={"project_id": self.pid}, headers=headers)
        assert r.status_code == 200
        self.approval_id = r.json()["approval"]["id"]
        yield

    def test_parallel_all_approved_syncs_approval_request(self):
        """并行审批全部通过后，ApprovalRequest状态同步为pending"""
        # 4位并行审批人都通过
        for uname in ["struct1", "sys1", "elec_ctrl1", "elec_eng1"]:
            headers = _login(uname)
            r = client.post(
                f"/api/approvals/{self.approval_id}/review",
                json={"action": "approved"},
                headers=headers,
            )
            assert r.status_code == 200

        # 验证 ApprovalRequest 同步为 pending（对应 pending_director）
        db = SessionLocal()
        try:
            pa = db.query(ProposalApproval).filter(ProposalApproval.id == self.approval_id).first()
            assert pa.status == "pending_director"

            ar = db.query(ApprovalRequest).filter(
                ApprovalRequest.request_type == "proposal",
                ApprovalRequest.request_id == self.approval_id,
            ).first()
            assert ar is not None
            assert ar.status == "pending", f"Expected pending, got {ar.status}"
        finally:
            db.close()

    def test_rejected_syncs_approval_request(self):
        """并行审批驳回后，ApprovalRequest状态同步为rejected"""
        headers = _login("struct1")
        r = client.post(
            f"/api/approvals/{self.approval_id}/review",
            json={"action": "rejected", "reason": "技术方案不成熟"},
            headers=headers,
        )
        assert r.status_code == 200

        db = SessionLocal()
        try:
            pa = db.query(ProposalApproval).filter(ProposalApproval.id == self.approval_id).first()
            assert pa.status == "rejected"

            ar = db.query(ApprovalRequest).filter(
                ApprovalRequest.request_type == "proposal",
                ApprovalRequest.request_id == self.approval_id,
            ).first()
            assert ar is not None
            assert ar.status == "rejected", f"Expected rejected, got {ar.status}"
        finally:
            db.close()


# ═════════════════════════════════════════════════
# 辅助函数
# ═════════════════════════════════════════════════

def _ensure_proposal_chain(db):
    """确保 proposal 审批链存在"""
    chain = db.query(ApprovalChain).filter(ApprovalChain.code == "proposal").first()
    if not chain:
        chain = ApprovalChain(
            name="立项审批", code="proposal",
            description="产品立项审批流程",
        )
        db.add(chain)
        db.flush()
        for s in [{"seq": 1, "role": "产品经理", "name": "提交"},
                  {"seq": 2, "role": "并行审批人", "name": "并行审批"},
                  {"seq": 3, "role": "研发总监", "name": "终审"}]:
            db.add(ApprovalStep(chain_id=chain.id, seq=s["seq"], role=s["role"], name=s["name"]))
        db.flush()
    return chain
