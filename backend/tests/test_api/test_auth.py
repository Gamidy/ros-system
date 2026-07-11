"""认证 API 测试 — login / register / me"""

import pytest


@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post("/api/v1/auth/register", json={
        "username": "newuser", "password": "testpass123"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"


@pytest.mark.asyncio
async def test_login_success(client):
    # Register first
    await client.post("/api/v1/auth/register", json={
        "username": "testuser", "password": "mypassword"
    })
    # Login
    resp = await client.post("/api/v1/auth/token", json={
        "username": "testuser", "password": "mypassword"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "username": "user2", "password": "correct"
    })
    resp = await client.post("/api/v1/auth/token", json={
        "username": "user2", "password": "wrong"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "testadmin"


@pytest.mark.asyncio
async def test_me_no_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
