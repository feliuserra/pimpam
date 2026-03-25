from tests.conftest import register, setup_user


async def test_get_profile(client):
    await register(client, "alice")
    r = await client.get("/api/v1/users/alice")
    assert r.status_code == 200
    assert r.json()["username"] == "alice"


async def test_get_profile_not_found(client):
    r = await client.get("/api/v1/users/nobody")
    assert r.status_code == 404


async def test_follow_user(client):
    alice_h = await setup_user(client, "alice")
    await register(client, "bob")
    r = await client.post("/api/v1/users/bob/follow", headers=alice_h)
    assert r.status_code == 204


async def test_follow_self(client):
    alice_h = await setup_user(client, "alice")
    r = await client.post("/api/v1/users/alice/follow", headers=alice_h)
    assert r.status_code == 400


async def test_follow_nonexistent_user(client):
    alice_h = await setup_user(client, "alice")
    r = await client.post("/api/v1/users/nobody/follow", headers=alice_h)
    assert r.status_code == 404


async def test_double_follow_is_idempotent(client):
    alice_h = await setup_user(client, "alice")
    await register(client, "bob")
    await client.post("/api/v1/users/bob/follow", headers=alice_h)
    r = await client.post("/api/v1/users/bob/follow", headers=alice_h)
    assert r.status_code == 204


async def test_unfollow_user(client):
    alice_h = await setup_user(client, "alice")
    await register(client, "bob")
    await client.post("/api/v1/users/bob/follow", headers=alice_h)
    r = await client.delete("/api/v1/users/bob/follow", headers=alice_h)
    assert r.status_code == 204


async def test_unfollow_not_following_is_idempotent(client):
    alice_h = await setup_user(client, "alice")
    await register(client, "bob")
    r = await client.delete("/api/v1/users/bob/follow", headers=alice_h)
    assert r.status_code == 204


async def test_follow_requires_auth(client):
    await register(client, "bob")
    r = await client.post("/api/v1/users/bob/follow")
    assert r.status_code == 401
