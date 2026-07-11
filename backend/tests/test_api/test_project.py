"""项目管理 + WBS + Task + Gate + 认证拦截集成测试"""
import pytest

pytestmark = pytest.mark.asyncio


class TestProjectCRUD:
    async def test_create_project(self, async_client, auth_headers):
        resp = await async_client.post("/api/v1/projects", json={
            "name": "天丽系列开发项目", "code": "PRJ-TIANLI-001",
            "description": "格力天丽系列家用变频开发",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "天丽系列开发项目"
        assert data["current_phase"] == "npr"

    async def test_get_project(self, async_client, auth_headers):
        resp = await async_client.get("/api/v1/projects", headers=auth_headers)
        assert resp.status_code == 200

    async def test_get_nonexistent_project(self, async_client, auth_headers):
        resp = await async_client.get("/api/v1/projects/99999", headers=auth_headers)
        assert resp.status_code == 404


class TestPhaseTransition:
    async def test_valid_transition_npr_to_concept(self, async_client, auth_headers):
        resp = await async_client.post("/api/v1/projects", json={
            "name": "Phase Test", "code": "PRJ-PHASE-001",
        }, headers=auth_headers)
        pid = resp.json()["id"]
        resp = await async_client.put(
            f"/api/v1/projects/{pid}/phase?target_phase=concept", headers=auth_headers)
        assert resp.status_code == 200

    async def test_invalid_phase_name(self, async_client, auth_headers):
        resp = await async_client.post("/api/v1/projects", json={
            "name": "Bad Phase", "code": "PRJ-BAD-001",
        }, headers=auth_headers)
        pid = resp.json()["id"]
        resp = await async_client.put(
            f"/api/v1/projects/{pid}/phase?target_phase=INVALID_PHASE", headers=auth_headers)
        assert resp.status_code == 400

    async def test_invalid_transition_skip_phase(self, async_client, auth_headers):
        resp = await async_client.post("/api/v1/projects", json={
            "name": "Skip Test", "code": "PRJ-SKIP-001",
        }, headers=auth_headers)
        pid = resp.json()["id"]
        resp = await async_client.put(
            f"/api/v1/projects/{pid}/phase?target_phase=development", headers=auth_headers)
        assert resp.status_code == 400


class TestGateDecisions:
    async def test_decide_gate_go(self, async_client, auth_headers):
        resp = await async_client.post("/api/v1/projects", json={
            "name": "Gate Test", "code": "PRJ-GATE-001",
        }, headers=auth_headers)
        pid = resp.json()["id"]
        resp = await async_client.post(
            f"/api/v1/projects/{pid}/gates/npr/decide", json={
                "decision": "go", "comment": "NPR评审通过",
            }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["decision"] == "go"

    async def test_get_project_gates(self, async_client, auth_headers):
        resp = await async_client.post("/api/v1/projects", json={
            "name": "Gates List", "code": "PRJ-GATES-001",
        }, headers=auth_headers)
        pid = resp.json()["id"]
        await async_client.post(f"/api/v1/projects/{pid}/gates/npr/decide", json={
            "decision": "go", "comment": "OK",
        }, headers=auth_headers)
        resp = await async_client.get(f"/api/v1/projects/{pid}/gates", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestWBSCRUD:
    async def test_create_wbs(self, async_client, auth_headers):
        resp = await async_client.post("/api/v1/projects", json={
            "name": "WBS Test", "code": "PRJ-WBS-001",
        }, headers=auth_headers)
        pid = resp.json()["id"]
        resp = await async_client.post("/api/v1/wbs", json={
            "project_id": pid, "name": "NPR阶段", "node_type": "phase", "sequence": 1,
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "NPR阶段"

    async def test_get_wbs_tree(self, async_client, auth_headers):
        resp = await async_client.post("/api/v1/projects", json={
            "name": "WBS Tree", "code": "PRJ-WBST-001",
        }, headers=auth_headers)
        pid = resp.json()["id"]
        await async_client.post("/api/v1/wbs", json={
            "project_id": pid, "name": "根节点", "node_type": "phase",
        }, headers=auth_headers)
        resp = await async_client.get(f"/api/v1/wbs?project_id={pid}", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestTaskCRUD:
    async def test_create_and_list_tasks(self, async_client, auth_headers):
        resp = await async_client.post("/api/v1/projects", json={
            "name": "Task Test", "code": "PRJ-TASK-001",
        }, headers=auth_headers)
        pid = resp.json()["id"]
        resp = await async_client.post("/api/v1/wbs", json={
            "project_id": pid, "name": "开发阶段",
        }, headers=auth_headers)
        wbs_id = resp.json()["id"]
        resp = await async_client.post("/api/v1/tasks", json={
            "wbs_id": wbs_id, "title": "编写需求文档",
            "priority": "high", "status": "todo",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["title"] == "编写需求文档"
        resp = await async_client.get(f"/api/v1/tasks?wbs_id={wbs_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestAuthRequired:
    async def test_projects_requires_auth(self, async_client):
        resp = await async_client.get("/api/v1/projects")
        assert resp.status_code in (401, 403)

    async def test_materials_requires_auth(self, async_client):
        resp = await async_client.get("/api/v1/materials")
        assert resp.status_code in (401, 403)

    async def test_bom_requires_auth(self, async_client):
        resp = await async_client.get("/api/v1/bom?model_id=1")
        assert resp.status_code in (401, 403)

    async def test_features_requires_auth(self, async_client):
        resp = await async_client.get("/api/v1/feature-families")
        assert resp.status_code in (401, 403)
