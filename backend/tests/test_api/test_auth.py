"""认证 API 测试 — login / register / me"""
import pytest


@pytest.mark.asyncio
async def test_register(async_client):
    resp = await async_client.post("/api/v1/auth/register", json={
        "username": "newuser", "email": "new@test.com",
        "password": "testpass123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"


@pytest.mark.asyncio
async def test_login_success(async_client):
    # Register first
    await async_client.post("/api/v1/auth/register", json={
        "username": "testuser", "email": "tu@test.com",
        "password": "mypassword",
    })
    # Login (JSON body)
    resp = await async_client.post("/api/v1/auth/token", json={
        "username": "testuser", "password": "mypassword",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(async_client):
    await async_client.post("/api/v1/auth/register", json={
        "username": "user2", "email": "u2@test.com",
        "password": "correct",
    })
    resp = await async_client.post("/api/v1/auth/token", json={
        "username": "user2", "password": "wrong",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(async_client, auth_headers):
    resp = await async_client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "testadmin"


@pytest.mark.asyncio
async def test_me_no_auth(async_client):
    resp = await async_client.get("/api/v1/auth/me")
    assert resp.status_code == 401
