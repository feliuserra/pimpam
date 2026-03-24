"""Tests for the notification system."""
import pytest

from tests.conftest import setup_user


# --- Helpers ---

async def create_post(client, h, title="Test", content="Content"):
    r = await client.post("/api/v1/posts", json={"title": title, "content": content}, headers=h)
    assert r.status_code == 201
    return r.json()


async def create_comment(client, h, post_id, content="A comment", parent_id=None):
    body = {"content": content}
    if parent_id:
        body["parent_id"] = parent_id
    r = await client.post(f"/api/v1/posts/{post_id}/comments", json=body, headers=h)
    assert r.status_code == 201
    return r.json()


async def get_notifications(client, h):
    r = await client.get("/api/v1/notifications", headers=h)
    assert r.status_code == 200
    return r.json()


# --- Follow ---

async def test_follow_creates_notification(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")

    await client.post("/api/v1/users/alice/follow", headers=hb)

    notifs = await get_notifications(client, ha)
    assert any(n["type"] == "follow" for n in notifs)


# --- Vote (grouped) ---

async def test_vote_notification_created(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    await client.post(f"/api/v1/posts/{post['id']}/vote", json={"direction": 1}, headers=hb)

    notifs = await get_notifications(client, ha)
    vote_notifs = [n for n in notifs if n["type"] == "vote"]
    assert len(vote_notifs) == 1
    assert vote_notifs[0]["post_id"] == post["id"]


async def test_vote_notification_grouped(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    hc = await setup_user(client, "carol")
    post = await create_post(client, ha)

    await client.post(f"/api/v1/posts/{post['id']}/vote", json={"direction": 1}, headers=hb)
    await client.post(f"/api/v1/posts/{post['id']}/vote", json={"direction": 1}, headers=hc)

    notifs = await get_notifications(client, ha)
    vote_notifs = [n for n in notifs if n["type"] == "vote"]
    assert len(vote_notifs) == 1
    assert vote_notifs[0]["group_count"] == 2


# --- Reaction (grouped) ---

async def test_reaction_notification_grouped(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    hc = await setup_user(client, "carol")
    post = await create_post(client, ha)
    comment = await create_comment(client, ha, post["id"])

    await client.post(
        f"/api/v1/comments/{comment['id']}/reactions",
        json={"reaction_type": "agree"},
        headers=hb,
    )
    await client.post(
        f"/api/v1/comments/{comment['id']}/reactions",
        json={"reaction_type": "love"},
        headers=hc,
    )

    notifs = await get_notifications(client, ha)
    reaction_notifs = [n for n in notifs if n["type"] == "reaction"]
    assert len(reaction_notifs) == 1
    assert reaction_notifs[0]["group_count"] == 2
    assert reaction_notifs[0]["comment_id"] == comment["id"]


# --- Grouping reset after mark_read ---

async def test_mark_read_resets_group(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    hc = await setup_user(client, "carol")
    post = await create_post(client, ha)

    await client.post(f"/api/v1/posts/{post['id']}/vote", json={"direction": 1}, headers=hb)

    notifs = await get_notifications(client, ha)
    notif_id = next(n["id"] for n in notifs if n["type"] == "vote")
    await client.patch(f"/api/v1/notifications/{notif_id}/read", headers=ha)

    # New vote after mark_read should create a fresh notification
    await client.post(f"/api/v1/posts/{post['id']}/vote", json={"direction": 1}, headers=hc)

    notifs = await get_notifications(client, ha)
    vote_notifs = [n for n in notifs if n["type"] == "vote"]
    unread = [n for n in vote_notifs if not n["is_read"]]
    assert len(unread) == 1
    assert unread[0]["group_count"] == 1


# --- Reply ---

async def test_reply_notifies_parent_comment_author(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = await create_comment(client, hb, post["id"])

    # alice replies to bob's comment
    await create_comment(client, ha, post["id"], parent_id=comment["id"])

    notifs = await get_notifications(client, hb)
    assert any(n["type"] == "reply" for n in notifs)


async def test_reply_does_not_notify_self(client):
    ha = await setup_user(client, "alice")
    post = await create_post(client, ha)
    comment = await create_comment(client, ha, post["id"])

    # alice replies to her own comment — should get no reply notification
    await create_comment(client, ha, post["id"], parent_id=comment["id"])

    notifs = await get_notifications(client, ha)
    assert not any(n["type"] == "reply" for n in notifs)


# --- New comment ---

async def test_new_comment_notifies_post_author(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    await create_comment(client, hb, post["id"])

    notifs = await get_notifications(client, ha)
    assert any(n["type"] == "new_comment" for n in notifs)


async def test_new_comment_by_post_author_does_not_self_notify(client):
    ha = await setup_user(client, "alice")
    post = await create_post(client, ha)
    await create_comment(client, ha, post["id"])

    notifs = await get_notifications(client, ha)
    assert not any(n["type"] == "new_comment" for n in notifs)


# --- Share ---

async def test_share_notifies_original_author(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    await client.post(f"/api/v1/posts/{post['id']}/share", json={}, headers=hb)

    notifs = await get_notifications(client, ha)
    assert any(n["type"] == "share" for n in notifs)


# --- Opt-out ---

async def test_opt_out_suppresses_notification(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")

    # alice opts out of follow notifications
    await client.patch(
        "/api/v1/notifications/preferences",
        json={"notification_type": "follow", "enabled": False},
        headers=ha,
    )

    await client.post("/api/v1/users/alice/follow", headers=hb)

    notifs = await get_notifications(client, ha)
    assert not any(n["type"] == "follow" for n in notifs)


async def test_opt_back_in_resumes_notifications(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")

    await client.patch(
        "/api/v1/notifications/preferences",
        json={"notification_type": "follow", "enabled": False},
        headers=ha,
    )
    await client.patch(
        "/api/v1/notifications/preferences",
        json={"notification_type": "follow", "enabled": True},
        headers=ha,
    )

    await client.post("/api/v1/users/alice/follow", headers=hb)

    notifs = await get_notifications(client, ha)
    assert any(n["type"] == "follow" for n in notifs)


# --- Mark all read ---

async def test_mark_all_read(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    await client.post(f"/api/v1/posts/{post['id']}/vote", json={"direction": 1}, headers=hb)
    await client.post("/api/v1/users/alice/follow", headers=hb)

    count_before = (await client.get("/api/v1/notifications/unread-count", headers=ha)).json()["count"]
    assert count_before >= 2

    await client.patch("/api/v1/notifications/read-all", headers=ha)

    count_after = (await client.get("/api/v1/notifications/unread-count", headers=ha)).json()["count"]
    assert count_after == 0


# --- Unread count ---

async def test_unread_count(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    r = await client.get("/api/v1/notifications/unread-count", headers=ha)
    assert r.json()["count"] == 0

    await client.post(f"/api/v1/posts/{post['id']}/vote", json={"direction": 1}, headers=hb)
    await client.post("/api/v1/users/alice/follow", headers=hb)

    r = await client.get("/api/v1/notifications/unread-count", headers=ha)
    assert r.json()["count"] == 2


# --- Preferences roundtrip ---

async def test_preferences_roundtrip(client):
    ha = await setup_user(client, "alice")

    # All enabled by default
    disabled = (await client.get("/api/v1/notifications/preferences", headers=ha)).json()
    assert disabled == []

    # Disable two types
    for t in ("vote", "reaction"):
        await client.patch(
            "/api/v1/notifications/preferences",
            json={"notification_type": t, "enabled": False},
            headers=ha,
        )

    disabled = (await client.get("/api/v1/notifications/preferences", headers=ha)).json()
    assert set(disabled) == {"vote", "reaction"}

    # Re-enable one
    await client.patch(
        "/api/v1/notifications/preferences",
        json={"notification_type": "vote", "enabled": True},
        headers=ha,
    )
    disabled = (await client.get("/api/v1/notifications/preferences", headers=ha)).json()
    assert disabled == ["reaction"]
