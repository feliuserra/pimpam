"""Tests for the site-wide admin layer (/api/v1/admin/*)."""

from sqlalchemy import update

from app.models.user import User
from tests.conftest import get_test_db, setup_user


async def _make_admin(username: str):
    """Promote a user to admin via direct DB access."""
    async for db in get_test_db():
        await db.execute(
            update(User).where(User.username == username).values(is_admin=True)
        )
        await db.commit()


async def _setup_admin(client, username="admin_user"):
    """Register a user, promote to admin, return auth headers."""
    h = await setup_user(client, username)
    await _make_admin(username)
    return h


# ── Auth & Permissions ──────────────────────────────────────────────


async def test_admin_requires_auth(client):
    r = await client.get("/api/v1/admin/reports")
    assert r.status_code == 401


async def test_admin_requires_admin_flag(client):
    h = await setup_user(client, "regular")
    r = await client.get("/api/v1/admin/reports", headers=h)
    assert r.status_code == 403
    assert r.json()["detail"] == "Admin access required"


# ── Reports ──────────────────────────────────────────────────────────


async def test_list_reports_empty(client):
    h = await _setup_admin(client)
    r = await client.get("/api/v1/admin/reports", headers=h)
    assert r.status_code == 200
    assert r.json() == []


async def test_list_reports_with_data(client):
    admin_h = await _setup_admin(client)
    alice_h = await setup_user(client, "alice")
    # Create a post to report
    post_r = await client.post(
        "/api/v1/posts",
        headers=alice_h,
        json={"title": "Bad", "content": "Bad content"},
    )
    post_id = post_r.json()["id"]
    # Report it
    bob_h = await setup_user(client, "bob")
    await client.post(
        f"/api/v1/posts/{post_id}/report", headers=bob_h, json={"reason": "Spam"}
    )
    r = await client.get("/api/v1/admin/reports", headers=admin_h)
    assert r.status_code == 200
    reports = r.json()
    assert len(reports) == 1
    assert reports[0]["content_type"] == "post"
    assert reports[0]["content_id"] == post_id
    assert reports[0]["status"] == "pending"
    assert reports[0]["reporter_username"] == "bob"


async def test_list_reports_filter_by_status(client):
    admin_h = await _setup_admin(client)
    alice_h = await setup_user(client, "alice")
    post_r = await client.post(
        "/api/v1/posts", headers=alice_h, json={"title": "X", "content": "Y"}
    )
    post_id = post_r.json()["id"]
    bob_h = await setup_user(client, "bob")
    await client.post(
        f"/api/v1/posts/{post_id}/report", headers=bob_h, json={"reason": "Spam"}
    )
    # Filter for resolved — should be empty
    r = await client.get("/api/v1/admin/reports?status=resolved", headers=admin_h)
    assert r.status_code == 200
    assert r.json() == []
    # Filter for pending — should have 1
    r = await client.get("/api/v1/admin/reports?status=pending", headers=admin_h)
    assert len(r.json()) == 1


async def test_dismiss_report(client):
    admin_h = await _setup_admin(client)
    alice_h = await setup_user(client, "alice")
    post_r = await client.post(
        "/api/v1/posts", headers=alice_h, json={"title": "X", "content": "Y"}
    )
    post_id = post_r.json()["id"]
    bob_h = await setup_user(client, "bob")
    await client.post(
        f"/api/v1/posts/{post_id}/report", headers=bob_h, json={"reason": "Spam"}
    )
    reports = (await client.get("/api/v1/admin/reports", headers=admin_h)).json()
    report_id = reports[0]["id"]

    r = await client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        headers=admin_h,
        json={"action": "dismiss"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "dismissed"

    # Post should still be visible
    post = await client.get(f"/api/v1/posts/{post_id}")
    assert post.status_code == 200
    assert post.json()["is_removed"] is False


async def test_resolve_report_removes_content(client):
    admin_h = await _setup_admin(client)
    alice_h = await setup_user(client, "alice")
    post_r = await client.post(
        "/api/v1/posts", headers=alice_h, json={"title": "X", "content": "Y"}
    )
    post_id = post_r.json()["id"]
    bob_h = await setup_user(client, "bob")
    await client.post(
        f"/api/v1/posts/{post_id}/report", headers=bob_h, json={"reason": "Spam"}
    )
    reports = (await client.get("/api/v1/admin/reports", headers=admin_h)).json()
    report_id = reports[0]["id"]

    r = await client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        headers=admin_h,
        json={"action": "remove_content", "reason": "Violates rules"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"

    # Post should be removed (returns 404 for removed posts)
    post = await client.get(f"/api/v1/posts/{post_id}")
    assert post.status_code == 404

    # Verify it's in the content removals audit log
    removals = await client.get("/api/v1/admin/content-removals", headers=admin_h)
    assert any(
        cr["content_type"] == "post" and cr["content_id"] == post_id
        for cr in removals.json()
    )


async def test_resolve_report_already_resolved(client):
    admin_h = await _setup_admin(client)
    alice_h = await setup_user(client, "alice")
    post_r = await client.post(
        "/api/v1/posts", headers=alice_h, json={"title": "X", "content": "Y"}
    )
    post_id = post_r.json()["id"]
    bob_h = await setup_user(client, "bob")
    await client.post(
        f"/api/v1/posts/{post_id}/report", headers=bob_h, json={"reason": "Spam"}
    )
    reports = (await client.get("/api/v1/admin/reports", headers=admin_h)).json()
    report_id = reports[0]["id"]
    await client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        headers=admin_h,
        json={"action": "dismiss"},
    )
    # Try to resolve again
    r = await client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        headers=admin_h,
        json={"action": "dismiss"},
    )
    assert r.status_code == 409


async def test_resolve_report_not_found(client):
    admin_h = await _setup_admin(client)
    r = await client.post(
        "/api/v1/admin/reports/9999/resolve",
        headers=admin_h,
        json={"action": "dismiss"},
    )
    assert r.status_code == 404


# ── Suspensions ──────────────────────────────────────────────────────


async def test_suspend_user(client):
    admin_h = await _setup_admin(client)
    await setup_user(client, "target")
    # Get target user ID
    target_r = await client.get("/api/v1/users/target")
    target_id = target_r.json()["id"]

    r = await client.post(
        f"/api/v1/admin/users/{target_id}/suspend",
        headers=admin_h,
        json={"reason": "Spamming"},
    )
    assert r.status_code == 200
    assert r.json()["username"] == "target"
    assert r.json()["reason"] == "Spamming"
    assert r.json()["is_active"] is True


async def test_suspend_already_suspended(client):
    admin_h = await _setup_admin(client)
    await setup_user(client, "target")
    target_r = await client.get("/api/v1/users/target")
    target_id = target_r.json()["id"]

    await client.post(
        f"/api/v1/admin/users/{target_id}/suspend",
        headers=admin_h,
        json={"reason": "Spamming"},
    )
    r = await client.post(
        f"/api/v1/admin/users/{target_id}/suspend",
        headers=admin_h,
        json={"reason": "Still spamming"},
    )
    assert r.status_code == 409


async def test_suspend_admin_forbidden(client):
    admin_h = await _setup_admin(client, "admin1")
    await setup_user(client, "admin2")
    await _make_admin("admin2")
    admin2_r = await client.get("/api/v1/users/admin2")
    admin2_id = admin2_r.json()["id"]

    r = await client.post(
        f"/api/v1/admin/users/{admin2_id}/suspend",
        headers=admin_h,
        json={"reason": "Test"},
    )
    assert r.status_code == 400
    assert "Cannot suspend an admin" in r.json()["detail"]


async def test_suspend_self_forbidden(client):
    admin_h = await _setup_admin(client)
    admin_r = await client.get("/api/v1/users/admin_user")
    admin_id = admin_r.json()["id"]

    r = await client.post(
        f"/api/v1/admin/users/{admin_id}/suspend",
        headers=admin_h,
        json={"reason": "Test"},
    )
    assert r.status_code == 400
    assert "Cannot suspend yourself" in r.json()["detail"]


async def test_suspend_nonexistent_user(client):
    admin_h = await _setup_admin(client)
    r = await client.post(
        "/api/v1/admin/users/9999/suspend",
        headers=admin_h,
        json={"reason": "Test"},
    )
    assert r.status_code == 404


async def test_unsuspend_user(client):
    admin_h = await _setup_admin(client)
    await setup_user(client, "target")
    target_r = await client.get("/api/v1/users/target")
    target_id = target_r.json()["id"]

    await client.post(
        f"/api/v1/admin/users/{target_id}/suspend",
        headers=admin_h,
        json={"reason": "Spamming"},
    )
    r = await client.post(f"/api/v1/admin/users/{target_id}/unsuspend", headers=admin_h)
    assert r.status_code == 204


async def test_suspended_user_cannot_login(client):
    admin_h = await _setup_admin(client)
    await setup_user(client, "target")
    target_r = await client.get("/api/v1/users/target")
    target_id = target_r.json()["id"]

    await client.post(
        f"/api/v1/admin/users/{target_id}/suspend",
        headers=admin_h,
        json={"reason": "Spamming"},
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "target", "password": "testpass123"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "Account is suspended"


async def test_list_suspensions(client):
    admin_h = await _setup_admin(client)
    await setup_user(client, "target")
    target_r = await client.get("/api/v1/users/target")
    target_id = target_r.json()["id"]

    await client.post(
        f"/api/v1/admin/users/{target_id}/suspend",
        headers=admin_h,
        json={"reason": "Spamming"},
    )
    r = await client.get("/api/v1/admin/suspensions", headers=admin_h)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["username"] == "target"


# ── Global Bans ──────────────────────────────────────────────────────


async def test_global_ban_user(client):
    admin_h = await _setup_admin(client)
    await setup_user(client, "badactor")
    target_r = await client.get("/api/v1/users/badactor")
    target_id = target_r.json()["id"]

    r = await client.post(
        f"/api/v1/admin/users/{target_id}/ban",
        headers=admin_h,
        json={"reason": "Severe violations"},
    )
    assert r.status_code == 200
    assert r.json()["username"] == "badactor"
    assert r.json()["reason"] == "Severe violations"


async def test_global_ban_deactivates_user(client):
    """After a global ban, the user should not be able to log in."""
    admin_h = await _setup_admin(client)
    await setup_user(client, "badactor")
    target_r = await client.get("/api/v1/users/badactor")
    target_id = target_r.json()["id"]

    await client.post(
        f"/api/v1/admin/users/{target_id}/ban",
        headers=admin_h,
        json={"reason": "Banned"},
    )
    # Try to log in as banned user
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "badactor", "password": "testpass123"},
    )
    assert r.status_code == 401


async def test_global_ban_already_banned(client):
    admin_h = await _setup_admin(client)
    await setup_user(client, "badactor")
    target_r = await client.get("/api/v1/users/badactor")
    target_id = target_r.json()["id"]

    await client.post(
        f"/api/v1/admin/users/{target_id}/ban",
        headers=admin_h,
        json={"reason": "Banned"},
    )
    r = await client.post(
        f"/api/v1/admin/users/{target_id}/ban",
        headers=admin_h,
        json={"reason": "Banned again"},
    )
    assert r.status_code == 409


async def test_global_ban_admin_forbidden(client):
    admin_h = await _setup_admin(client, "admin1")
    await setup_user(client, "admin2")
    await _make_admin("admin2")
    admin2_r = await client.get("/api/v1/users/admin2")
    admin2_id = admin2_r.json()["id"]

    r = await client.post(
        f"/api/v1/admin/users/{admin2_id}/ban",
        headers=admin_h,
        json={"reason": "Test"},
    )
    assert r.status_code == 400


async def test_unban_user(client):
    admin_h = await _setup_admin(client)
    await setup_user(client, "badactor")
    target_r = await client.get("/api/v1/users/badactor")
    target_id = target_r.json()["id"]

    await client.post(
        f"/api/v1/admin/users/{target_id}/ban",
        headers=admin_h,
        json={"reason": "Banned"},
    )
    r = await client.post(f"/api/v1/admin/users/{target_id}/unban", headers=admin_h)
    assert r.status_code == 204

    # User should be able to log in again
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "badactor", "password": "testpass123"},
    )
    assert r.status_code == 200


async def test_unban_not_banned(client):
    admin_h = await _setup_admin(client)
    await setup_user(client, "regular")
    target_r = await client.get("/api/v1/users/regular")
    target_id = target_r.json()["id"]

    r = await client.post(f"/api/v1/admin/users/{target_id}/unban", headers=admin_h)
    assert r.status_code == 404


async def test_list_bans(client):
    admin_h = await _setup_admin(client)
    await setup_user(client, "badactor")
    target_r = await client.get("/api/v1/users/badactor")
    target_id = target_r.json()["id"]

    await client.post(
        f"/api/v1/admin/users/{target_id}/ban",
        headers=admin_h,
        json={"reason": "Banned"},
    )
    r = await client.get("/api/v1/admin/bans", headers=admin_h)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["username"] == "badactor"


# ── Content Removal ──────────────────────────────────────────────────


async def test_admin_remove_post(client):
    admin_h = await _setup_admin(client)
    alice_h = await setup_user(client, "alice")
    post_r = await client.post(
        "/api/v1/posts", headers=alice_h, json={"title": "X", "content": "Y"}
    )
    post_id = post_r.json()["id"]

    r = await client.post(
        f"/api/v1/admin/posts/{post_id}/remove",
        headers=admin_h,
        json={"reason": "Violates platform rules"},
    )
    assert r.status_code == 200
    assert r.json()["content_type"] == "post"
    assert r.json()["content_id"] == post_id

    # Post should be removed (returns 404 for removed posts)
    post = await client.get(f"/api/v1/posts/{post_id}")
    assert post.status_code == 404


async def test_admin_remove_post_already_removed(client):
    admin_h = await _setup_admin(client)
    alice_h = await setup_user(client, "alice")
    post_r = await client.post(
        "/api/v1/posts", headers=alice_h, json={"title": "X", "content": "Y"}
    )
    post_id = post_r.json()["id"]

    await client.post(
        f"/api/v1/admin/posts/{post_id}/remove",
        headers=admin_h,
        json={"reason": "Violates rules"},
    )
    r = await client.post(
        f"/api/v1/admin/posts/{post_id}/remove",
        headers=admin_h,
        json={"reason": "Again"},
    )
    assert r.status_code == 409


async def test_admin_remove_post_not_found(client):
    admin_h = await _setup_admin(client)
    r = await client.post(
        "/api/v1/admin/posts/9999/remove",
        headers=admin_h,
        json={"reason": "Test"},
    )
    assert r.status_code == 404


async def test_admin_remove_comment(client):
    admin_h = await _setup_admin(client)
    alice_h = await setup_user(client, "alice")
    post_r = await client.post(
        "/api/v1/posts", headers=alice_h, json={"title": "X", "content": "Y"}
    )
    post_id = post_r.json()["id"]
    comment_r = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        headers=alice_h,
        json={"content": "Bad comment"},
    )
    comment_id = comment_r.json()["id"]

    r = await client.post(
        f"/api/v1/admin/comments/{comment_id}/remove",
        headers=admin_h,
        json={"reason": "Hate speech"},
    )
    assert r.status_code == 200
    assert r.json()["content_type"] == "comment"
    assert r.json()["content_id"] == comment_id


async def test_list_content_removals(client):
    admin_h = await _setup_admin(client)
    alice_h = await setup_user(client, "alice")
    post_r = await client.post(
        "/api/v1/posts", headers=alice_h, json={"title": "X", "content": "Y"}
    )
    post_id = post_r.json()["id"]

    await client.post(
        f"/api/v1/admin/posts/{post_id}/remove",
        headers=admin_h,
        json={"reason": "Test removal"},
    )
    r = await client.get("/api/v1/admin/content-removals", headers=admin_h)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["content_type"] == "post"


async def test_non_admin_cannot_remove_content(client):
    h = await setup_user(client, "regular")
    r = await client.post(
        "/api/v1/admin/posts/1/remove",
        headers=h,
        json={"reason": "Test"},
    )
    assert r.status_code == 403
