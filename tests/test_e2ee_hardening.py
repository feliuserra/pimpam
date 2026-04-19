"""Tests for E2EE hardening: device_keys validation and key management."""

import pytest

from tests.conftest import setup_user

# Valid RSA-2048 SPKI public keys (base64-encoded DER)
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


async def _register_device(client, headers, public_key=VALID_SPKI_1):
    r = await client.post(
        "/api/v1/devices",
        headers=headers,
        json={"device_name": "Test", "public_key": public_key},
    )
    assert r.status_code == 201
    return r.json()


async def _get_user_id(client, headers):
    r = await client.get("/api/v1/users/me", headers=headers)
    return r.json()["id"]


# ── device_keys must not be empty ────────────────────────────────────────────


@pytest.mark.anyio
async def test_send_message_empty_device_keys_rejected(client):
    """POST /messages with device_keys: [] returns 422 — no plaintext fallback."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    r = await client.post(
        "/api/v1/messages",
        headers=alice_h,
        json={
            "recipient_id": bob_id,
            "ciphertext": "hello",
            "device_keys": [],
        },
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_send_message_with_device_keys_succeeds(client):
    """POST /messages with valid device_keys returns 201."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    alice_dev = await _register_device(client, alice_h, VALID_SPKI_1)
    bob_dev = await _register_device(client, bob_h, VALID_SPKI_2)

    r = await client.post(
        "/api/v1/messages",
        headers=alice_h,
        json={
            "recipient_id": bob_id,
            "ciphertext": "encrypted content",
            "device_keys": [
                {"device_id": alice_dev["id"], "encrypted_key": "wrapped_alice"},
                {"device_id": bob_dev["id"], "encrypted_key": "wrapped_bob"},
            ],
        },
    )
    assert r.status_code == 201


# ── Device registration validation (verify existing) ────────────────────────


@pytest.mark.anyio
async def test_device_registration_rejects_invalid_base64(client):
    """POST /devices with invalid base64 key returns 422."""
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/devices",
        headers=h,
        json={"device_name": "Bad Device", "public_key": "not-valid!!!"},
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_device_fingerprint_in_public_keys(client):
    """GET /users/{username}/devices returns fingerprints for each device."""
    h = await setup_user(client, "alice")
    await _register_device(client, h, VALID_SPKI_1)

    r = await client.get("/api/v1/users/alice/devices", headers=h)
    assert r.status_code == 200
    devices = r.json()
    assert len(devices) >= 1
    assert len(devices[0]["public_key_fingerprint"]) == 64  # SHA-256 hex
