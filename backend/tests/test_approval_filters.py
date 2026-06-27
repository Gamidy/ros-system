"""集成测试：审批请求的角色过滤（非超级用户只能看到自己的审批请求）

测试目标：GET /api/approval/requests 中非 super 用户的角色过滤逻辑。
修复要点：将 elif not status and not requester: 改为 elif not requester:，
确保 status 参数不会导致非 super 用户看到别人的审批记录。
"""
import pytest


class TestApprovalRoleFilter:
    """审批请求列表 - 角色过滤测试"""

    # ── fixtures ──────────────────────────────────────────────

    @pytest.fixture
    def manager_token(self, client):
        """创建 module_manager 用户（非 super 角色但有 approvals 菜单权限）"""
        r = client.post("/api/auth/register", json={
            "username": "modmanager",
            "password": "ModMgr123!",
            "role": "module_manager",
        })
        assert r.status_code == 200, f"注册 modmanager 失败: {r.text}"
        r = client.post("/api/auth/login", json={
            "username": "modmanager",
            "password": "ModMgr123!",
        })
        assert r.status_code == 200
        return r.json()["access_token"]

    @pytest.fixture
    def manager_headers(self, manager_token):
        return {"Authorization": f"Bearer {manager_token}"}

    # ── helpers ───────────────────────────────────────────────

    def _ensure_chains(self, client, headers):
        """调用 GET /approval/chains 确保默认审批链已初始化"""
        r = client.get("/api/approval/chains", headers=headers)
        assert r.status_code == 200, f"获取审批链失败: {r.text}"
        return r.json()

    def _create_request(self, client, headers, chain_id, requester, title):
        """创建一个 pending 状态的审批请求"""
        r = client.post("/api/approval/requests", json={
            "chain_id": chain_id,
            "request_type": "register",
            "title": title,
            "requester": requester,
        }, headers=headers)
        assert r.status_code == 200, f"创建审批请求失败: {r.text}"
        return r.json()

    def _approve_fully(self, client, headers, request_id):
        """用 admin 完全审批通过一个请求（走完所有步骤）"""
        # 获取请求详情，找到 chain 的步骤数
        r = client.get(f"/api/approval/requests/{request_id}", headers=headers)
        assert r.status_code == 200
        req = r.json()
        step_count = len(req["steps"])

        for _ in range(step_count):
            r = client.post(
                f"/api/approval/requests/{request_id}/approve",
                json={"comment": "通过"},
                headers=headers,
            )
            assert r.status_code == 200, f"审批操作失败: {r.text}"
            # 如果已经 approved，停止
            if r.json()["status"] == "approved":
                break

        # 最终验证
        r = client.get(f"/api/approval/requests/{request_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "approved", f"审批未完成: {r.json()}"

    # ── 测试用例 ──────────────────────────────────────────────

    def test_non_super_only_sees_own_requests(self, client, admin_headers, manager_headers):
        """场景1: 非super用户调用 GET /approval/requests 只看到自己的审批"""
        chains = self._ensure_chains(client, admin_headers)
        assert len(chains) > 0
        chain_id = chains[0]["id"]

        # 管理员创建两个审批请求：一个给 modmanager，一个给 otheruser
        self._create_request(client, admin_headers, chain_id, "modmanager", "modmanager 的审批")
        self._create_request(client, admin_headers, chain_id, "otheruser", "别人的审批")

        # modmanager 查询自己的审批列表
        r = client.get("/api/approval/requests", headers=manager_headers)
        assert r.status_code == 200
        data = r.json()

        # 应该只看到自己的那条
        assert len(data) == 1, (
            f"期望 1 条记录（仅自己的），实际得到 {len(data)} 条: {data}"
        )
        assert data[0]["requester"] == "modmanager"

    def test_non_super_with_status_pending(self, client, admin_headers, manager_headers):
        """场景2: 非super用户调用 GET /approval/requests?status=pending 只看到自己的待审批"""
        chains = self._ensure_chains(client, admin_headers)
        chain_id = chains[0]["id"]

        # 创建两个 pending 请求，分属不同用户
        self._create_request(client, admin_headers, chain_id, "modmanager", "modmanager 待审批")
        self._create_request(client, admin_headers, chain_id, "otheruser", "别人的待审批")

        r = client.get("/api/approval/requests?status=pending", headers=manager_headers)
        assert r.status_code == 200
        data = r.json()

        assert len(data) == 1, (
            f"期望 1 条待审批记录（仅自己的），实际得到 {len(data)} 条: {data}"
        )
        assert data[0]["requester"] == "modmanager"
        assert data[0]["status"] == "pending"

    def test_non_super_with_status_approved(self, client, admin_headers, manager_headers):
        """场景3: 非super用户调用 GET /approval/requests?status=approved 只看到自己的已审批"""
        chains = self._ensure_chains(client, admin_headers)
        chain_id = chains[0]["id"]

        # 创建两个请求，分属不同用户
        req1 = self._create_request(client, admin_headers, chain_id, "modmanager", "modmanager 已审批")
        req2 = self._create_request(client, admin_headers, chain_id, "otheruser", "别人的已审批")

        # 用 admin 完全审批通过两个请求
        self._approve_fully(client, admin_headers, req1["id"])
        self._approve_fully(client, admin_headers, req2["id"])

        # modmanager 查询自己的已审批
        r = client.get("/api/approval/requests?status=approved", headers=manager_headers)
        assert r.status_code == 200
        data = r.json()

        assert len(data) == 1, (
            f"期望 1 条已审批记录（仅自己的），实际得到 {len(data)} 条: {data}"
        )
        assert data[0]["requester"] == "modmanager"
        assert data[0]["status"] == "approved"
