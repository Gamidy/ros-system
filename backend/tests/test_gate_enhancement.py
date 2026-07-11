"""P1 — 项目阶段门增强: Gate 模板 T/A/B/C + 前置校验"""

import pytest


@pytest.mark.asyncio
async def test_create_project_auto_generates_gates(async_client, auth_headers):
    """创建项目时自动生成 Gate 模板"""
    resp = await async_client.post("/api/v1/projects", json={
        "name": "Gate模板测试项目",
        "code": "PROJ-GATE-TEST",
        "project_class": "T",
    }, headers=auth_headers)
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # 验证自动生成了 Gates
    resp = await async_client.get(f"/api/v1/projects/{project_id}/gates", headers=auth_headers)
    assert resp.status_code == 200
    gates = resp.json()
    assert len(gates) >= 8
    codes = [g["gate_code"] for g in gates]
    assert "M1" in codes


@pytest.mark.asyncio
async def test_gate_template_by_class_a(async_client, auth_headers):
    """A 级项目 Gate 模板"""
    resp = await async_client.post("/api/v1/projects", json={
        "name": "A级项目",
        "code": "PROJ-A-TEST",
        "project_class": "A",
    }, headers=auth_headers)
    project_id = resp.json()["id"]
    resp = await async_client.get(f"/api/v1/projects/{project_id}/gates", headers=auth_headers)
    gates = resp.json()
    codes = [g["gate_code"] for g in gates]
    assert "M1" in codes  # A 级有 M1
    assert len(gates) >= 8


@pytest.mark.asyncio
async def test_gate_template_by_class_b(async_client, auth_headers):
    """B 级项目 Gate 模板（精简）"""
    resp = await async_client.post("/api/v1/projects", json={
        "name": "B级项目",
        "code": "PROJ-B-TEST",
        "project_class": "B",
    }, headers=auth_headers)
    project_id = resp.json()["id"]
    resp = await async_client.get(f"/api/v1/projects/{project_id}/gates", headers=auth_headers)
    gates = resp.json()
    codes = [g["gate_code"] for g in gates]
    assert "M1" not in codes  # B 级跳过 M1
    assert "M2" in codes
    assert len(gates) <= 6


@pytest.mark.asyncio
async def test_gate_template_by_class_c(async_client, auth_headers):
    """C 级项目 Gate 模板（最精简）"""
    resp = await async_client.post("/api/v1/projects", json={
        "name": "C级项目",
        "code": "PROJ-C-TEST",
        "project_class": "C",
    }, headers=auth_headers)
    project_id = resp.json()["id"]
    resp = await async_client.get(f"/api/v1/projects/{project_id}/gates", headers=auth_headers)
    gates = resp.json()
    assert len(gates) <= 5  # C 级最精简


@pytest.mark.asyncio
async def test_gate_predecessor_validation(async_client, auth_headers):
    """前置 Gate 未通过时不能跳过"""
    resp = await async_client.post("/api/v1/projects", json={
        "name": "前置校验测试",
        "code": "PROJ-PRED-TEST",
        "project_class": "T",
    }, headers=auth_headers)
    project_id = resp.json()["id"]

    # 获取 Gates
    resp = await async_client.get(f"/api/v1/projects/{project_id}/gates", headers=auth_headers)
    gates = resp.json()

    # 尝试跳过 M1 直接通过 M2 → 应被拒绝
    m2_gate = next(g for g in gates if g["gate_code"] == "M2")
    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/gates/{m2_gate['id']}/decision",
        json={"decision": "go"},
        headers=auth_headers,
    )
    assert resp.status_code == 400  # 前置 Gate 未通过


@pytest.mark.asyncio
async def test_gate_full_flow(async_client, auth_headers):
    """完整 Gate 流转: M1→M2"""
    resp = await async_client.post("/api/v1/projects", json={
        "name": "Gate流转测试",
        "code": "PROJ-FLOW-TEST",
        "project_class": "T",
    }, headers=auth_headers)
    project_id = resp.json()["id"]

    resp = await async_client.get(f"/api/v1/projects/{project_id}/gates", headers=auth_headers)
    gates = resp.json()
    m1_gate = next(g for g in gates if g["gate_code"] == "M1")
    m2_gate = next(g for g in gates if g["gate_code"] == "M2")

    # M1 通过
    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/gates/{m1_gate['id']}/decision",
        json={"decision": "go"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # 现在 M2 可以通过
    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/gates/{m2_gate['id']}/decision",
        json={"decision": "go"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
