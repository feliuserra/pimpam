"""Tests for E2EE device management: registration, revocation, backup, multi-device messaging."""

import pytest

from tests.conftest import setup_user

# Two distinct valid RSA-2048 SPKI public keys (base64-encoded DER)
VALID_SPKI_1 = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAv06L2BLDCJpXoKQzty0i"
    "Ae9iSGYUFTQTiO0nplL1tQ/NOqwB3d5F16hCCJY3bkvs5rLEBO0M4dQLlgXt1iOt"
    "8pVMiZGUBDiU7EUxVfgiIl9OKSWCNMaFz46uUiIQpWVXAHT1RkXAuVO63aibvmA1"
    "IaHMZ6gOePlzqVyCqFPpHbb+ktDAD3s5GTCQHYTL3itZmfFFa1wO65yWy29Aca3sj"
    "cjooAC3OMJtwL7Jz6EMkPkHb/60dL33cG1DMNrvekotWLoJ/A5yYj7HgnBVw89WB"
    "OBOofXk/bu/dNBf1j/DdSJArfDvtevUTDrJYylKK4JKj8S64taj4Y3gHKp3CHaMr"
    "QIDAQAB"
)

VALID_SPKI_2 = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxzunqiwDjZkxAEmuCzLT"
    "WPL6SoKsW74A6VEfdzIVdjU16iRP53O9vPJrwcsrIi2JZagVmudZ1mvl1Em2RxFN"
    "qg6jq8WCBJI4pyMgrt112KjGbYmav60ad50UR0YPt62coOPQV4J3335itOLGI58Sg"
    "hSe15liRICFaDOake7KXTjheAR2/4goSOqS1gQ6ynAg+plwQWDdLYuU3cfZ+CbA8"
    "DvexpvbQ3/Y93F+UaraTDS1IEF4fX/8ocvkDNGf74kQ4AYDz8f1kqF1lZppANpSf"
    "KvbnIQppmzULPKtqa+LhsJyXAPGgsx4QO9Dsi0+SUaf/MVjxUeb2gdiB6AAZfH74"
    "wIDAQAB"
)


async def _register_device(
    client, headers, name="Test Device", public_key=VALID_SPKI_1
):
    r = await client.post(
        "/api/v1/devices",
        headers=headers,
        json={"device_name": name, "public_key": public_key},
    )
    return r


async def _get_user_id(client, headers):
    r = await client.get("/api/v1/users/me", headers=headers)
    return r.json()["id"]


# ── Device registration ─────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_register_device(client):
    h = await setup_user(client, "alice")
    r = await _register_device(client, h)
    assert r.status_code == 201
    data = r.json()
    assert data["device_name"] == "Test Device"
    assert len(data["public_key_fingerprint"]) == 64  # SHA-256 hex
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_register_invalid_base64(client):
    h = await setup_user(client, "alice")
    r = await _register_device(client, h, public_key="not-valid-base64!!!")
    assert r.status_code == 422


@pytest.mark.anyio
async def test_register_too_short_key(client):
    h = await setup_user(client, "alice")
    r = await _register_device(client, h, public_key="AAAA")
    assert r.status_code == 422
    assert "too short" in r.json()["detail"].lower()


@pytest.mark.anyio
async def test_register_non_rsa_key(client):
    """A valid base64 blob that is long enough but not RSA should fail."""
    import base64

    fake_blob = base64.b64encode(b"\x00" * 300).decode()
    h = await setup_user(client, "alice")
    r = await _register_device(client, h, public_key=fake_blob)
    assert r.status_code == 422
    assert "rsa" in r.json()["detail"].lower()


@pytest.mark.anyio
async def test_max_device_limit(client):
    h = await setup_user(client, "alice")
    # Register 10 devices with unique keys (we only have 2 real keys,
    # so we'll register 2 real + test that re-registering same key reactivates)
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    for i in range(10):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        spki = key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        spki_b64 = base64.b64encode(spki).decode()
        r = await _register_device(client, h, name=f"Device {i}", public_key=spki_b64)
        assert r.status_code == 201

    # 11th device should fail
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    spki = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    r = await _register_device(
        client, h, name="Too Many", public_key=base64.b64encode(spki).decode()
    )
    assert r.status_code == 400
    assert "maximum" in r.json()["detail"].lower()


@pytest.mark.anyio
async def test_duplicate_fingerprint_reactivates(client):
    """Re-registering a revoked device with the same key reactivates it."""
    h = await setup_user(client, "alice")
    r = await _register_device(client, h)
    device_id = r.json()["id"]

    # Revoke
    await client.delete(f"/api/v1/devices/{device_id}", headers=h)

    # Re-register same key
    r = await _register_device(client, h)
    assert r.status_code == 201
    assert r.json()["is_active"] is True


# ── Device listing ───────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_list_devices(client):
    h = await setup_user(client, "alice")
    await _register_device(client, h, name="Chrome", public_key=VALID_SPKI_1)
    await _register_device(client, h, name="Firefox", public_key=VALID_SPKI_2)

    r = await client.get("/api/v1/devices", headers=h)
    assert r.status_code == 200
    devices = r.json()
    assert len(devices) == 2
    names = {d["device_name"] for d in devices}
    assert names == {"Chrome", "Firefox"}


@pytest.mark.anyio
async def test_revoked_device_excluded_from_list(client):
    h = await setup_user(client, "alice")
    r = await _register_device(client, h, name="Old")
    device_id = r.json()["id"]
    await client.delete(f"/api/v1/devices/{device_id}", headers=h)

    r = await client.get("/api/v1/devices", headers=h)
    assert len(r.json()) == 0


# ── Rename ───────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_rename_device(client):
    h = await setup_user(client, "alice")
    r = await _register_device(client, h, name="Old Name")
    device_id = r.json()["id"]

    r = await client.patch(
        f"/api/v1/devices/{device_id}",
        headers=h,
        json={"device_name": "New Name"},
    )
    assert r.status_code == 200
    assert r.json()["device_name"] == "New Name"


# ── Revoke ───────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_revoke_device(client):
    h = await setup_user(client, "alice")
    r = await _register_device(client, h)
    device_id = r.json()["id"]

    r = await client.delete(f"/api/v1/devices/{device_id}", headers=h)
    assert r.status_code == 204


@pytest.mark.anyio
async def test_revoke_already_revoked(client):
    h = await setup_user(client, "alice")
    r = await _register_device(client, h)
    device_id = r.json()["id"]

    await client.delete(f"/api/v1/devices/{device_id}", headers=h)
    r = await client.delete(f"/api/v1/devices/{device_id}", headers=h)
    assert r.status_code == 400


# ── User device keys (public endpoint) ──────────────────────────────────────


@pytest.mark.anyio
async def test_get_user_device_keys(client):
    h = await setup_user(client, "alice")
    await _register_device(client, h, name="My Device", public_key=VALID_SPKI_1)

    bob_h = await setup_user(client, "bob")
    r = await client.get("/api/v1/users/alice/devices", headers=bob_h)
    assert r.status_code == 200
    keys = r.json()
    assert len(keys) == 1
    assert keys[0]["public_key"] == VALID_SPKI_1
    assert "device_name" not in keys[0]  # privacy: name not exposed


# ── Key backup ───────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_backup_upload_download(client):
    h = await setup_user(client, "alice")
    r = await _register_device(client, h)
    device_id = r.json()["id"]

    backup_data = {
        "encrypted_private_key": "base64encryptedblob",
        "salt": "base64salt16bytesxx",
        "kdf": "argon2id",
        "kdf_params": '{"memory":65536,"iterations":3,"parallelism":1}',
    }
    r = await client.post(
        f"/api/v1/devices/{device_id}/backup", headers=h, json=backup_data
    )
    assert r.status_code == 201

    # Download
    r = await client.get(f"/api/v1/devices/{device_id}/backup", headers=h)
    assert r.status_code == 200
    assert r.json()["encrypted_private_key"] == "base64encryptedblob"
    assert r.json()["kdf"] == "argon2id"


@pytest.mark.anyio
async def test_backup_not_found(client):
    h = await setup_user(client, "alice")
    r = await _register_device(client, h)
    device_id = r.json()["id"]

    r = await client.get(f"/api/v1/devices/{device_id}/backup", headers=h)
    assert r.status_code == 404


@pytest.mark.anyio
async def test_backup_delete(client):
    h = await setup_user(client, "alice")
    r = await _register_device(client, h)
    device_id = r.json()["id"]

    await client.post(
        f"/api/v1/devices/{device_id}/backup",
        headers=h,
        json={
            "encrypted_private_key": "blob",
            "salt": "salt",
            "kdf": "argon2id",
            "kdf_params": "{}",
        },
    )

    r = await client.delete(f"/api/v1/devices/{device_id}/backup", headers=h)
    assert r.status_code == 204

    r = await client.get(f"/api/v1/devices/{device_id}/backup", headers=h)
    assert r.status_code == 404


@pytest.mark.anyio
async def test_list_available_backups(client):
    h = await setup_user(client, "alice")
    r = await _register_device(client, h)
    device_id = r.json()["id"]

    await client.post(
        f"/api/v1/devices/{device_id}/backup",
        headers=h,
        json={
            "encrypted_private_key": "blob",
            "salt": "salt",
            "kdf": "argon2id",
            "kdf_params": "{}",
        },
    )

    r = await client.get("/api/v1/devices/backups/available", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1


# ── SPKI validation ─────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_fingerprint_is_sha256_hex(client):
    from app.core.e2ee_validation import validate_spki_public_key

    fp = validate_spki_public_key(VALID_SPKI_1)
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)

    # Same key should always produce same fingerprint
    assert validate_spki_public_key(VALID_SPKI_1) == fp

    # Different key should produce different fingerprint
    fp2 = validate_spki_public_key(VALID_SPKI_2)
    assert fp2 != fp
