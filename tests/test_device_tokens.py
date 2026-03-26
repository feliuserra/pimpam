"""Tests for device token registration and removal."""

from tests.conftest import setup_user


async def test_register_device_token(client):
    alice_h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/users/me/device-tokens",
        headers=alice_h,
        json={"token": "apns-token-abc123", "platform": "ios"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["token"] == "apns-token-abc123"
    assert data["platform"] == "ios"


async def test_register_device_token_android(client):
    alice_h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/users/me/device-tokens",
        headers=alice_h,
        json={"token": "fcm-token-xyz789", "platform": "android"},
    )
    assert r.status_code == 201
    assert r.json()["platform"] == "android"


async def test_register_device_token_web(client):
    alice_h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/users/me/device-tokens",
        headers=alice_h,
        json={"token": "web-push-token", "platform": "web"},
    )
    assert r.status_code == 201
    assert r.json()["platform"] == "web"


async def test_register_invalid_platform(client):
    alice_h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/users/me/device-tokens",
        headers=alice_h,
        json={"token": "some-token", "platform": "blackberry"},
    )
    assert r.status_code == 422


async def test_register_empty_token(client):
    alice_h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/users/me/device-tokens",
        headers=alice_h,
        json={"token": "", "platform": "ios"},
    )
    assert r.status_code == 422


async def test_register_duplicate_token_updates_platform(client):
    """Registering the same token again should update its platform."""
    alice_h = await setup_user(client, "alice")
    await client.post(
        "/api/v1/users/me/device-tokens",
        headers=alice_h,
        json={"token": "shared-token", "platform": "ios"},
    )
    r = await client.post(
        "/api/v1/users/me/device-tokens",
        headers=alice_h,
        json={"token": "shared-token", "platform": "android"},
    )
    assert r.status_code == 201
    assert r.json()["platform"] == "android"


async def test_unregister_device_token(client):
    alice_h = await setup_user(client, "alice")
    await client.post(
        "/api/v1/users/me/device-tokens",
        headers=alice_h,
        json={"token": "my-token", "platform": "ios"},
    )
    r = await client.delete(
        "/api/v1/users/me/device-tokens/my-token",
        headers=alice_h,
    )
    assert r.status_code == 204


async def test_unregister_nonexistent_token(client):
    alice_h = await setup_user(client, "alice")
    r = await client.delete(
        "/api/v1/users/me/device-tokens/no-such-token",
        headers=alice_h,
    )
    assert r.status_code == 404


async def test_register_multiple_tokens(client):
    """A user can register multiple device tokens (multiple devices)."""
    alice_h = await setup_user(client, "alice")
    r1 = await client.post(
        "/api/v1/users/me/device-tokens",
        headers=alice_h,
        json={"token": "iphone-token", "platform": "ios"},
    )
    r2 = await client.post(
        "/api/v1/users/me/device-tokens",
        headers=alice_h,
        json={"token": "ipad-token", "platform": "ios"},
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["token"] != r2.json()["token"]


async def test_register_requires_auth(client):
    r = await client.post(
        "/api/v1/users/me/device-tokens",
        json={"token": "some-token", "platform": "ios"},
    )
    assert r.status_code == 401


async def test_unregister_requires_auth(client):
    r = await client.delete("/api/v1/users/me/device-tokens/some-token")
    assert r.status_code == 401
