"""
Tests for app/core/email.py — SMTP delivery functions.
"""
import sys
import types
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core import email as email_mod


def _mock_aiosmtplib_module():
    """Return a fake aiosmtplib module with a mock send() coroutine."""
    mod = types.ModuleType("aiosmtplib")
    mod.send = AsyncMock()
    return mod


# ---------------------------------------------------------------------------
# send_email
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_email_skipped_when_smtp_disabled():
    """When smtp_enabled=False, send_email returns without calling aiosmtplib."""
    with patch.object(email_mod.settings, "smtp_enabled", False):
        # No aiosmtplib import at all — should succeed silently
        await email_mod.send_email("user@example.com", "Subject", "Body")


@pytest.mark.asyncio
async def test_send_email_calls_aiosmtplib_when_enabled():
    """When smtp_enabled=True, send_email calls aiosmtplib.send with correct args."""
    fake_mod = _mock_aiosmtplib_module()
    with (
        patch.object(email_mod.settings, "smtp_enabled", True),
        patch.object(email_mod.settings, "smtp_host", "mail.example.com"),
        patch.object(email_mod.settings, "smtp_port", 587),
        patch.object(email_mod.settings, "smtp_username", "user"),
        patch.object(email_mod.settings, "smtp_password", "pass"),
        patch.object(email_mod.settings, "smtp_tls", True),
        patch.object(email_mod.settings, "smtp_from", "noreply@example.com"),
        patch.dict(sys.modules, {"aiosmtplib": fake_mod}),
    ):
        await email_mod.send_email("alice@example.com", "Hello", "World")

    fake_mod.send.assert_awaited_once()
    call_kwargs = fake_mod.send.call_args.kwargs
    assert call_kwargs["hostname"] == "mail.example.com"
    assert call_kwargs["port"] == 587
    assert call_kwargs["start_tls"] is True


@pytest.mark.asyncio
async def test_send_email_empty_credentials_passed_as_none():
    """Empty smtp_username / smtp_password strings are converted to None."""
    fake_mod = _mock_aiosmtplib_module()
    with (
        patch.object(email_mod.settings, "smtp_enabled", True),
        patch.object(email_mod.settings, "smtp_host", "mail.example.com"),
        patch.object(email_mod.settings, "smtp_port", 25),
        patch.object(email_mod.settings, "smtp_username", ""),
        patch.object(email_mod.settings, "smtp_password", ""),
        patch.object(email_mod.settings, "smtp_tls", False),
        patch.object(email_mod.settings, "smtp_from", "noreply@example.com"),
        patch.dict(sys.modules, {"aiosmtplib": fake_mod}),
    ):
        await email_mod.send_email("alice@example.com", "Subject", "Body")

    call_kwargs = fake_mod.send.call_args.kwargs
    assert call_kwargs["username"] is None
    assert call_kwargs["password"] is None


# ---------------------------------------------------------------------------
# send_verification_email
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_verification_email_disabled():
    """No error when SMTP is disabled."""
    with patch.object(email_mod.settings, "smtp_enabled", False):
        await email_mod.send_verification_email("alice@example.com", "tok123")


@pytest.mark.asyncio
async def test_send_verification_email_body_contains_token():
    """Verification email body includes the token and domain."""
    fake_mod = _mock_aiosmtplib_module()
    with (
        patch.object(email_mod.settings, "smtp_enabled", True),
        patch.object(email_mod.settings, "smtp_host", "mail.example.com"),
        patch.object(email_mod.settings, "smtp_port", 587),
        patch.object(email_mod.settings, "smtp_username", ""),
        patch.object(email_mod.settings, "smtp_password", ""),
        patch.object(email_mod.settings, "smtp_tls", False),
        patch.object(email_mod.settings, "smtp_from", "noreply@pimpam.org"),
        patch.object(email_mod.settings, "domain", "pimpam.org"),
        patch.object(email_mod.settings, "email_verification_token_expire_minutes", 60),
        patch.dict(sys.modules, {"aiosmtplib": fake_mod}),
    ):
        await email_mod.send_verification_email("alice@example.com", "mytoken42")

    msg = fake_mod.send.call_args.args[0]
    body = msg.get_payload()
    assert "mytoken42" in body
    assert "pimpam.org" in body


# ---------------------------------------------------------------------------
# send_password_reset_email — code mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_password_reset_email_code_mode_disabled():
    """No error when SMTP is disabled in code mode."""
    with patch.object(email_mod.settings, "smtp_enabled", False):
        await email_mod.send_password_reset_email("alice@example.com", "123456", mode="code")


@pytest.mark.asyncio
async def test_send_password_reset_email_code_mode_body():
    """Code-mode reset email contains the code."""
    fake_mod = _mock_aiosmtplib_module()
    with (
        patch.object(email_mod.settings, "smtp_enabled", True),
        patch.object(email_mod.settings, "smtp_host", "mail.example.com"),
        patch.object(email_mod.settings, "smtp_port", 587),
        patch.object(email_mod.settings, "smtp_username", ""),
        patch.object(email_mod.settings, "smtp_password", ""),
        patch.object(email_mod.settings, "smtp_tls", False),
        patch.object(email_mod.settings, "smtp_from", "noreply@pimpam.org"),
        patch.object(email_mod.settings, "password_reset_code_expire_minutes", 10),
        patch.dict(sys.modules, {"aiosmtplib": fake_mod}),
    ):
        await email_mod.send_password_reset_email("alice@example.com", "654321", mode="code")

    msg = fake_mod.send.call_args.args[0]
    body = msg.get_payload()
    subject = msg["Subject"]
    assert "654321" in body
    assert "code" in subject.lower()


# ---------------------------------------------------------------------------
# send_password_reset_email — link mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_password_reset_email_link_mode_disabled():
    """No error when SMTP is disabled in link mode."""
    with patch.object(email_mod.settings, "smtp_enabled", False):
        await email_mod.send_password_reset_email("alice@example.com", "tokenxyz", mode="link")


@pytest.mark.asyncio
async def test_send_password_reset_email_link_mode_body():
    """Link-mode reset email contains the token as a URL."""
    fake_mod = _mock_aiosmtplib_module()
    with (
        patch.object(email_mod.settings, "smtp_enabled", True),
        patch.object(email_mod.settings, "smtp_host", "mail.example.com"),
        patch.object(email_mod.settings, "smtp_port", 587),
        patch.object(email_mod.settings, "smtp_username", ""),
        patch.object(email_mod.settings, "smtp_password", ""),
        patch.object(email_mod.settings, "smtp_tls", False),
        patch.object(email_mod.settings, "smtp_from", "noreply@pimpam.org"),
        patch.object(email_mod.settings, "domain", "pimpam.org"),
        patch.object(email_mod.settings, "password_reset_link_expire_minutes", 15),
        patch.dict(sys.modules, {"aiosmtplib": fake_mod}),
    ):
        await email_mod.send_password_reset_email("alice@example.com", "resettoken99", mode="link")

    msg = fake_mod.send.call_args.args[0]
    body = msg.get_payload()
    subject = msg["Subject"]
    assert "resettoken99" in body
    assert "pimpam.org" in body
    assert "reset" in subject.lower()
