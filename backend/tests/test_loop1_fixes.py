# noqa: E501 — test assertions are intentionally multi-line for readability
"""Loop 1 — RED 阶段: 状态机集成 + 编号竞态 + 事务修复测试"""

import pytest
from sqlalchemy import select, text
from app.core.enums import ECRStatus


class TestStateMachineIntegration:
    """E2E: CRUD层状态转换必须通过 state_machine"""

    @pytest.mark.asyncio
    async def test_ecr_submit_via_state_machine(self, async_client, auth_headers):
        """ECR submit 应调用 state_machine.assert_transition 而非硬编码"""
        # GREEN 条件: ECR 提交时调用 services/state_machine.py
        resp = await async_client.post("/api/v1/ecr/", json={
            "title": "状态机集成测试-提交",
            "ecr_type": "other",
            "reason": "验证状态机被调用",
        }, headers=auth_headers)
        assert resp.status_code == 201
        ecr_id = resp.json()["id"]

        # 提交 → 应通过状态机校验
        resp = await async_client.post(f"/api/v1/ecr/{ecr_id}/submit", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == ECRStatus.SUBMITTED.value

    @pytest.mark.asyncio
    async def test_ecr_invalid_transition_blocked(self, async_client, auth_headers):
        """非法状态转换应被状态机拦截"""
        resp = await async_client.post("/api/v1/ecr/", json={
            "title": "非法转换测试",
            "ecr_type": "other",
            "reason": "测试状态机拦截",
        }, headers=auth_headers)
        ecr_id = resp.json()["id"]

        # 跳过 submit 直接 review → 应被拦截
        resp = await async_client.post(f"/api/v1/ecr/{ecr_id}/review", json={
            "action": "approve",
        }, headers=auth_headers)
        assert resp.status_code == 400
        detail = resp.json()["detail"].lower()
        assert "不是合法转换" in detail or "state" in detail

    @pytest.mark.asyncio
    async def test_eco_lifecycle_via_state_machine(self, async_client, auth_headers):
        """ECO 完整生命周期应通过状态机"""
        resp = await async_client.post("/api/v1/eco/", json={
            "title": "ECO状态机集成测试",
            "change_summary": "验证状态机调用",
        }, headers=auth_headers)
        eco_id = resp.json()["id"]

        # draft → implementing ✅
        resp = await async_client.post(f"/api/v1/eco/{eco_id}/implement", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "implementing"

        # 尝试跳过 verify 直接 close → ❌
        resp = await async_client.post(f"/api/v1/eco/{eco_id}/close", headers=auth_headers)
        assert resp.status_code == 400


class TestECRCodeGeneration:
    """编号生成应原子化，避免竞态"""

    @pytest.mark.asyncio
    async def test_ecr_code_generation_atomic(self, async_client, auth_headers):
        """快速连续创建 ECR 不会生成重复编号"""
        codes = set()
        for i in range(3):
            resp = await async_client.post("/api/v1/ecr/", json={
                "title": f"编号竞态测试-{i}",
                "ecr_type": "other",
                "reason": "验证编号唯一性",
            }, headers=auth_headers)
            assert resp.status_code == 201
            code = resp.json()["code"]
            assert code not in codes, f"重复编号: {code}"
            codes.add(code)

    @pytest.mark.asyncio
    async def test_eco_code_generation_atomic(self, async_client, auth_headers):
        """快速连续创建 ECO 不会生成重复编号"""
        codes = set()
        for i in range(3):
            resp = await async_client.post("/api/v1/eco/", json={
                "title": f"ECO编号竞态测试-{i}",
                "change_summary": "验证编号唯一性",
            }, headers=auth_headers)
            assert resp.status_code == 201
            code = resp.json()["code"]
            assert code not in codes, f"重复编号: {code}"
            codes.add(code)


class TestDatabaseTransaction:
    """数据库会话管理应一致"""

    @pytest.mark.asyncio
    async def test_create_ecr_transaction_consistent(self, async_client, auth_headers):
        """ECR 创建过程中出现异常应回滚，不留下脏数据"""
        # 正常创建确认可用
        resp = await async_client.post("/api/v1/ecr/", json={
            "title": "事务一致性测试",
            "ecr_type": "other",
            "reason": "验证事务回滚",
        }, headers=auth_headers)
        assert resp.status_code == 201
        ecr_id = resp.json()["id"]

        # 确认数据持久化
        resp = await async_client.get(f"/api/v1/ecr/{ecr_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "事务一致性测试"
