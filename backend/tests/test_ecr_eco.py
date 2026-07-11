"""Phase 2 — ECR/ECO 集成测试"""

import pytest


# ── ECR 测试 ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_ecr(async_client, auth_headers):
    resp = await async_client.post("/api/v1/ecr/", json={
        "title": "变更压缩机规格",
        "ecr_type": "design_change",
        "reason": "噪音超标需要更换压缩机型号",
        "urgency": "high",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "变更压缩机规格"
    assert data["status"] == "draft"
    assert data["code"].startswith("ECR-")


@pytest.mark.asyncio
async def test_list_ecr(async_client, auth_headers):
    resp = await async_client.get("/api/v1/ecr/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_ecr_not_found(async_client, auth_headers):
    resp = await async_client.get("/api/v1/ecr/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_ecr_draft(async_client, auth_headers):
    # 先创建
    resp = await async_client.post("/api/v1/ecr/", json={
        "title": "待编辑的ECR",
        "ecr_type": "other",
        "reason": "测试编辑功能",
    }, headers=auth_headers)
    ecr_id = resp.json()["id"]

    # 编辑
    resp = await async_client.put(f"/api/v1/ecr/{ecr_id}", json={
        "title": "已编辑的ECR",
        "urgency": "critical",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "已编辑的ECR"
    assert resp.json()["urgency"] == "critical"


@pytest.mark.asyncio
async def test_submit_ecr(async_client, auth_headers):
    resp = await async_client.post("/api/v1/ecr/", json={
        "title": "待提交的ECR",
        "ecr_type": "design_change",
        "reason": "测试提交流程",
    }, headers=auth_headers)
    ecr_id = resp.json()["id"]

    resp = await async_client.post(f"/api/v1/ecr/{ecr_id}/submit", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"


@pytest.mark.asyncio
async def test_approve_ecr(async_client, auth_headers):
    resp = await async_client.post("/api/v1/ecr/", json={
        "title": "待审批的ECR",
        "ecr_type": "design_change",
        "reason": "测试审批流程",
    }, headers=auth_headers)
    ecr_id = resp.json()["id"]

    await async_client.post(f"/api/v1/ecr/{ecr_id}/submit", headers=auth_headers)

    resp = await async_client.post(f"/api/v1/ecr/{ecr_id}/review", json={
        "action": "approve",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_reject_ecr(async_client, auth_headers):
    resp = await async_client.post("/api/v1/ecr/", json={
        "title": "待驳回的ECR",
        "ecr_type": "other",
        "reason": "测试驳回流程",
    }, headers=auth_headers)
    ecr_id = resp.json()["id"]

    await async_client.post(f"/api/v1/ecr/{ecr_id}/submit", headers=auth_headers)

    resp = await async_client.post(f"/api/v1/ecr/{ecr_id}/review", json={
        "action": "reject",
        "rejection_reason": "变更理由不充分",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_cannot_edit_submitted_ecr(async_client, auth_headers):
    resp = await async_client.post("/api/v1/ecr/", json={
        "title": "提交后不可编辑",
        "ecr_type": "other",
        "reason": "测试状态锁",
    }, headers=auth_headers)
    ecr_id = resp.json()["id"]

    await async_client.post(f"/api/v1/ecr/{ecr_id}/submit", headers=auth_headers)

    resp = await async_client.put(f"/api/v1/ecr/{ecr_id}", json={
        "title": "试图编辑",
    }, headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_filter_by_status(async_client, auth_headers):
    resp = await async_client.get("/api/v1/ecr/?status=draft", headers=auth_headers)
    assert resp.status_code == 200
    for ecr in resp.json():
        assert ecr["status"] == "draft"


# ── ECO 测试 ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_eco(async_client, auth_headers):
    resp = await async_client.post("/api/v1/eco/", json={
        "title": "压缩机变更实施",
        "change_summary": "将 A 型号压缩机替换为 B 型号",
        "implementation_plan": "1. 采购 B 型号 2. 更换产线",
        "items": [{
            "seq": 1, "change_type": "replace", "object_type": "bom",
            "object_code": "MTR-001", "object_name": "A型压缩机",
            "old_value": "A型-220V-1.5P", "new_value": "B型-220V-1.5P",
        }],
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "draft"
    assert data["code"].startswith("ECO-")
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_get_eco_not_found(async_client, auth_headers):
    resp = await async_client.get("/api/v1/eco/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_eco_full_lifecycle(async_client, auth_headers):
    # 创建
    resp = await async_client.post("/api/v1/eco/", json={
        "title": "生命周期测试ECO",
        "change_summary": "测试完整状态流转",
    }, headers=auth_headers)
    eco_id = resp.json()["id"]
    assert resp.json()["status"] == "draft"

    # 实施
    resp = await async_client.post(f"/api/v1/eco/{eco_id}/implement", headers=auth_headers)
    assert resp.json()["status"] == "implementing"

    # 验证
    resp = await async_client.post(f"/api/v1/eco/{eco_id}/verify", headers=auth_headers)
    assert resp.json()["status"] == "verified"

    # 生效
    resp = await async_client.post(f"/api/v1/eco/{eco_id}/effect", headers=auth_headers)
    assert resp.json()["status"] == "effective"

    # 关闭
    resp = await async_client.post(f"/api/v1/eco/{eco_id}/close", headers=auth_headers)
    assert resp.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_eco_cancel(async_client, auth_headers):
    resp = await async_client.post("/api/v1/eco/", json={
        "title": "待取消ECO",
        "change_summary": "测试取消流程",
    }, headers=auth_headers)
    eco_id = resp.json()["id"]

    resp = await async_client.post(f"/api/v1/eco/{eco_id}/cancel", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_eco_list(async_client, auth_headers):
    resp = await async_client.get("/api/v1/eco/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_ecr_to_eco_flow(async_client, auth_headers):
    # 1. 创建 ECR
    resp = await async_client.post("/api/v1/ecr/", json={
        "title": "ECR→ECO 测试",
        "ecr_type": "design_change",
        "reason": "测试完整变更流程",
    }, headers=auth_headers)
    ecr_id = resp.json()["id"]

    # 2. 提交
    await async_client.post(f"/api/v1/ecr/{ecr_id}/submit", headers=auth_headers)

    # 3. 审批通过
    await async_client.post(f"/api/v1/ecr/{ecr_id}/review", json={
        "action": "approve",
    }, headers=auth_headers)

    # 4. 从 ECR 创建 ECO
    resp = await async_client.post("/api/v1/eco/", json={
        "ecr_id": ecr_id,
        "title": "ECR→ECO 实施",
        "change_summary": "基于已批准ECR实施变更",
    }, headers=auth_headers)
    assert resp.status_code == 201

    # 5. 验证 ECR 已变为 converted
    resp = await async_client.get(f"/api/v1/ecr/{ecr_id}", headers=auth_headers)
    assert resp.json()["status"] == "converted"


@pytest.mark.asyncio
async def test_cannot_create_eco_from_unapproved_ecr(async_client, auth_headers):
    resp = await async_client.post("/api/v1/ecr/", json={
        "title": "未审批的ECR",
        "ecr_type": "other",
        "reason": "测试约束",
    }, headers=auth_headers)
    ecr_id = resp.json()["id"]

    # 不提交，直接尝试创建 ECO
    resp = await async_client.post("/api/v1/eco/", json={
        "ecr_id": ecr_id,
        "title": "不应创建的ECO",
        "change_summary": "应被拒绝",
    }, headers=auth_headers)
    assert resp.status_code == 400
