from tests.conftest import register, login, headers


async def test_register_success(client):
    r = await register(client, "alice")
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "alice"
    assert "id" in body
    assert "hashed_password" not in body


async def test_register_duplicate_username(client):
    await register(client, "alice")
    r = await register(client, "alice", email="other@example.com")
    assert r.status_code == 409


async def test_register_duplicate_email(client):
    await register(client, "alice")
    r = await register(client, "bob", email="alice@example.com")
    assert r.status_code == 409


async def test_login_success(client):
    await register(client, "alice")
    r = await client.post("/api/v1/auth/login", json={
        "username": "alice", "password": "testpass123"
    })
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body


async def test_login_wrong_password(client):
    await register(client, "alice")
    r = await client.post("/api/v1/auth/login", json={
        "username": "alice", "password": "wrongpass"
    })
    assert r.status_code == 401


async def test_login_unknown_user(client):
    r = await client.post("/api/v1/auth/login", json={
        "username": "nobody", "password": "testpass123"
    })
    assert r.status_code == 401


async def test_me_authenticated(client):
    await register(client, "alice")
    h = await headers(client, "alice")
    r = await client.get("/api/v1/users/me", headers=h)
    assert r.status_code == 200
    assert r.json()["username"] == "alice"


async def test_me_unauthenticated(client):
    r = await client.get("/api/v1/users/me")
    assert r.status_code == 401


async def test_refresh_token(client):
    await register(client, "alice")
    login_r = await client.post("/api/v1/auth/login", json={
        "username": "alice", "password": "testpass123"
    })
    refresh_token = login_r.json()["refresh_token"]
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    assert "access_token" in r.json()
