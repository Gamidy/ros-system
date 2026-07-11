"""Loop 3 — 登出 Token 撤销 + Docker 集成测试"""

import pytest


class TestLogoutTokenRevocation:
    """POST /auth/logout 应使 token 立即失效"""

    @pytest.mark.asyncio
    async def test_logout_invalidates_token(self, async_client, auth_headers):
        """登出后，原 token 无法访问受保护资源"""
        # 提取当前 token
        token = auth_headers["Authorization"].split(" ")[1]

        # 先确认 token 有效
        resp = await async_client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200

        # 登出
        resp = await async_client.post("/api/v1/auth/logout", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "已登出"

        # 原 token 应失效
        resp = await async_client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_endpoint_exists(self, async_client, auth_headers):
        """登出端点存在且可访问"""
        resp = await async_client.post("/api/v1/auth/logout", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_logout_without_token_fails(self, async_client):
        """无 token 登出应返回 401"""
        resp = await async_client.post("/api/v1/auth/logout")
        assert resp.status_code in (401, 403)


class TestDockerHealth:
    """Docker Compose 部署后服务可访问"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client):
        """健康检查端点"""
        resp = await async_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "app" in data

    @pytest.mark.asyncio
    async def test_swagger_docs_accessible(self, async_client):
        """OpenAPI 文档可访问"""
        resp = await async_client.get("/docs")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_json_accessible(self, async_client):
        """OpenAPI JSON schema 可访问"""
        resp = await async_client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "paths" in data
