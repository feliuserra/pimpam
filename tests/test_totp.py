"""
Integration tests for 2FA (TOTP) endpoints.

Flow tested:
  setup  → verify  → login with code  → disable
  setup  → verify  → login without code → 401 totp_required
  setup  → verify  → login with wrong code → 401
  error paths: double-setup, verify without setup, disable with bad password/code
"""
import pyotp

from tests.conftest import register, setup_user


async def _setup_and_enable_totp(client, h: dict) -> str:
    """Run setup + verify for a user; return the raw secret."""
    r = await client.post("/api/v1/auth/totp/setup", headers=h)
    assert r.status_code == 201, r.text
    secret = r.json()["secret"]

    code = pyotp.TOTP(secret).now()
    r = await client.post("/api/v1/auth/totp/verify", json={"code": code}, headers=h)
    assert r.status_code == 200, r.text
    return secret


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

async def test_totp_setup_returns_uri_and_secret(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/auth/totp/setup", headers=h)
    assert r.status_code == 201
    body = r.json()
    assert "uri" in body and "secret" in body
    assert body["uri"].startswith("otpauth://totp/PimPam:alice")
    assert len(body["secret"]) == 32  # pyotp default base32 length


async def test_totp_setup_fails_if_already_enabled(client):
    h = await setup_user(client, "alice")
    await _setup_and_enable_totp(client, h)
    r = await client.post("/api/v1/auth/totp/setup", headers=h)
    assert r.status_code == 409


async def test_totp_setup_requires_auth(client):
    r = await client.post("/api/v1/auth/totp/setup")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------

async def test_totp_verify_enables_2fa(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/auth/totp/setup", headers=h)
    secret = r.json()["secret"]

    code = pyotp.TOTP(secret).now()
    r = await client.post("/api/v1/auth/totp/verify", json={"code": code}, headers=h)
    assert r.status_code == 200
    assert r.json()["detail"] == "2FA enabled."


async def test_totp_verify_wrong_code(client):
    h = await setup_user(client, "alice")
    await client.post("/api/v1/auth/totp/setup", headers=h)
    r = await client.post("/api/v1/auth/totp/verify", json={"code": "000000"}, headers=h)
    assert r.status_code == 422


async def test_totp_verify_without_setup(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/auth/totp/verify", json={"code": "123456"}, headers=h)
    assert r.status_code == 400


async def test_totp_verify_already_enabled(client):
    h = await setup_user(client, "alice")
    secret = await _setup_and_enable_totp(client, h)
    code = pyotp.TOTP(secret).now()
    r = await client.post("/api/v1/auth/totp/verify", json={"code": code}, headers=h)
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# Login with TOTP
# ---------------------------------------------------------------------------

async def test_login_without_totp_unchanged(client):
    """Users without 2FA should log in exactly as before."""
    await register(client, "alice")
    r = await client.post("/api/v1/auth/login", json={"username": "alice", "password": "testpass123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


async def test_login_totp_required_when_enabled(client):
    h = await setup_user(client, "alice")
    await _setup_and_enable_totp(client, h)
    r = await client.post("/api/v1/auth/login", json={"username": "alice", "password": "testpass123"})
    assert r.status_code == 401
    assert r.json()["detail"] == "totp_required"


async def test_login_totp_wrong_code(client):
    h = await setup_user(client, "alice")
    await _setup_and_enable_totp(client, h)
    r = await client.post("/api/v1/auth/login", json={
        "username": "alice", "password": "testpass123", "totp_code": "000000",
    })
    assert r.status_code == 401
    assert r.json()["detail"] == "Incorrect TOTP code"


async def test_login_totp_correct_code(client):
    h = await setup_user(client, "alice")
    secret = await _setup_and_enable_totp(client, h)
    code = pyotp.TOTP(secret).now()
    r = await client.post("/api/v1/auth/login", json={
        "username": "alice", "password": "testpass123", "totp_code": code,
    })
    assert r.status_code == 200
    assert "access_token" in r.json()


# ---------------------------------------------------------------------------
# Disable
# ---------------------------------------------------------------------------

async def test_totp_disable(client):
    h = await setup_user(client, "alice")
    secret = await _setup_and_enable_totp(client, h)

    code = pyotp.TOTP(secret).now()
    r = await client.post("/api/v1/auth/totp/disable", json={
        "password": "testpass123", "code": code,
    }, headers=h)
    assert r.status_code == 200
    assert r.json()["detail"] == "2FA disabled."

    # Should now be able to log in without TOTP code
    r = await client.post("/api/v1/auth/login", json={"username": "alice", "password": "testpass123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


async def test_totp_disable_wrong_password(client):
    h = await setup_user(client, "alice")
    secret = await _setup_and_enable_totp(client, h)

    code = pyotp.TOTP(secret).now()
    r = await client.post("/api/v1/auth/totp/disable", json={
        "password": "wrongpassword", "code": code,
    }, headers=h)
    assert r.status_code == 401


async def test_totp_disable_wrong_code(client):
    h = await setup_user(client, "alice")
    await _setup_and_enable_totp(client, h)

    r = await client.post("/api/v1/auth/totp/disable", json={
        "password": "testpass123", "code": "000000",
    }, headers=h)
    assert r.status_code == 422


async def test_totp_disable_not_enabled(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/auth/totp/disable", json={
        "password": "testpass123", "code": "123456",
    }, headers=h)
    assert r.status_code == 400
