"""Tests for comments, reactions, and shares."""
import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import register, setup_user


# --- Helpers ---

async def create_post(client, h, title="Test post", content="Hello"):
    r = await client.post("/api/v1/posts", json={"title": title, "content": content}, headers=h)
    assert r.status_code == 201
    return r.json()


async def create_comment(client, h, post_id, content="Nice post", parent_id=None):
    body = {"content": content}
    if parent_id is not None:
        body["parent_id"] = parent_id
    r = await client.post(f"/api/v1/posts/{post_id}/comments", json=body, headers=h)
    return r


# --- Comment creation ---

async def test_create_top_level_comment(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    r = await create_comment(client, hb, post["id"])
    assert r.status_code == 201
    data = r.json()
    assert data["post_id"] == post["id"]
    assert data["parent_id"] is None
    assert data["depth"] == 0
    assert data["content"] == "Nice post"
    assert data["is_removed"] is False


async def test_create_reply(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = (await create_comment(client, hb, post["id"])).json()

    r = await create_comment(client, ha, post["id"], content="Thanks!", parent_id=comment["id"])
    assert r.status_code == 201
    data = r.json()
    assert data["parent_id"] == comment["id"]
    assert data["depth"] == 1


async def test_comment_max_depth_rejected(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    # Create 5 levels deep (depths 0-4)
    parent_id = None
    for _ in range(5):
        r = await create_comment(client, hb, post["id"], parent_id=parent_id)
        assert r.status_code == 201
        parent_id = r.json()["id"]

    # Depth 5 should be rejected
    r = await create_comment(client, ha, post["id"], parent_id=parent_id)
    assert r.status_code == 400
    assert "depth" in r.json()["detail"].lower()


async def test_comment_on_missing_post_returns_404(client):
    h = await setup_user(client, "alice")
    r = await create_comment(client, h, 9999)
    assert r.status_code == 404


async def test_comment_content_max_length_enforced(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    r = await client.post(
        f"/api/v1/posts/{post['id']}/comments",
        json={"content": "x" * 301},
        headers=hb,
    )
    assert r.status_code == 422


async def test_consecutive_comments_by_same_user(client):
    """Regression: posting multiple comments in succession must not get stuck."""
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    # Bob posts 4 comments in rapid succession — all should succeed
    for i in range(4):
        r = await create_comment(client, hb, post["id"], f"Comment {i + 1}")
        assert r.status_code == 201, f"Comment {i + 1} failed with {r.status_code}"
        assert r.json()["content"] == f"Comment {i + 1}"

    # Verify all 4 appear in the listing
    r = await client.get(f"/api/v1/posts/{post['id']}/comments")
    assert r.status_code == 200
    assert len(r.json()) == 4


async def test_consecutive_replies_by_same_user(client):
    """Regression: posting multiple replies in succession must not get stuck."""
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = (await create_comment(client, ha, post["id"], "Root")).json()

    # Bob posts 3 replies to the same comment back-to-back
    for i in range(3):
        r = await create_comment(
            client, hb, post["id"], f"Reply {i + 1}", parent_id=comment["id"]
        )
        assert r.status_code == 201, f"Reply {i + 1} failed with {r.status_code}"
        assert r.json()["parent_id"] == comment["id"]

    # Verify all 3 replies appear
    r = await client.get(f"/api/v1/comments/{comment['id']}/replies")
    assert r.status_code == 200
    assert len(r.json()) == 3


async def test_rate_limit_returns_429(client):
    """The comment endpoint should return 429 when rate-limited, not hang."""
    from app.core.limiter import limiter as shared_limiter

    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    # Temporarily enable the rate limiter
    shared_limiter.enabled = True
    try:
        # Post 7 comments to exceed the 6/minute limit
        statuses = []
        for i in range(7):
            r = await create_comment(client, hb, post["id"], f"Spam {i + 1}")
            statuses.append(r.status_code)

        # At least one should be 429
        assert 429 in statuses, f"Expected at least one 429 but got: {statuses}"
        # The first few should succeed
        assert statuses[0] == 201
    finally:
        shared_limiter.enabled = False


# --- List comments ---

async def test_list_comments(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    await create_comment(client, hb, post["id"], "First")
    await create_comment(client, ha, post["id"], "Second")

    r = await client.get(f"/api/v1/posts/{post['id']}/comments")
    assert r.status_code == 200
    comments = r.json()
    assert len(comments) == 2
    # Default sort is latest — newest first
    assert comments[0]["content"] == "Second"


async def test_list_replies(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = (await create_comment(client, hb, post["id"])).json()

    await create_comment(client, ha, post["id"], "reply1", parent_id=comment["id"])
    await create_comment(client, hb, post["id"], "reply2", parent_id=comment["id"])

    r = await client.get(f"/api/v1/comments/{comment['id']}/replies")
    assert r.status_code == 200
    replies = r.json()
    assert len(replies) == 2
    # Oldest first for replies
    assert replies[0]["content"] == "reply1"


async def test_removed_comment_shown_as_deleted(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = (await create_comment(client, hb, post["id"])).json()

    await client.delete(f"/api/v1/comments/{comment['id']}", headers=hb)

    r = await client.get(f"/api/v1/posts/{post['id']}/comments")
    found = next(c for c in r.json() if c["id"] == comment["id"])
    assert found["is_removed"] is True
    assert found["content"] == "[deleted]"


# --- Author delete ---

async def test_author_can_delete_own_comment(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = (await create_comment(client, hb, post["id"])).json()

    r = await client.delete(f"/api/v1/comments/{comment['id']}", headers=hb)
    assert r.status_code == 204


async def test_other_user_cannot_delete_comment(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = (await create_comment(client, hb, post["id"])).json()

    r = await client.delete(f"/api/v1/comments/{comment['id']}", headers=ha)
    assert r.status_code == 403


# --- Reactions ---

async def test_add_reaction(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = (await create_comment(client, ha, post["id"])).json()

    r = await client.post(
        f"/api/v1/comments/{comment['id']}/reactions",
        json={"reaction_type": "agree"},
        headers=hb,
    )
    assert r.status_code == 204


async def test_duplicate_reaction_rejected(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = (await create_comment(client, ha, post["id"])).json()

    await client.post(
        f"/api/v1/comments/{comment['id']}/reactions",
        json={"reaction_type": "agree"},
        headers=hb,
    )
    r = await client.post(
        f"/api/v1/comments/{comment['id']}/reactions",
        json={"reaction_type": "agree"},
        headers=hb,
    )
    assert r.status_code == 409


async def test_multiple_reaction_types_allowed(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = (await create_comment(client, ha, post["id"])).json()

    for rt in ("agree", "love"):
        r = await client.post(
            f"/api/v1/comments/{comment['id']}/reactions",
            json={"reaction_type": rt},
            headers=hb,
        )
        assert r.status_code == 204


async def test_cannot_react_to_own_comment(client):
    ha = await setup_user(client, "alice")
    post = await create_post(client, ha)
    comment = (await create_comment(client, ha, post["id"])).json()

    r = await client.post(
        f"/api/v1/comments/{comment['id']}/reactions",
        json={"reaction_type": "agree"},
        headers=ha,
    )
    assert r.status_code == 403


async def test_agree_reaction_increases_karma(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = (await create_comment(client, ha, post["id"])).json()

    before = (await client.get("/api/v1/users/me", headers=ha)).json()["karma"]
    await client.post(
        f"/api/v1/comments/{comment['id']}/reactions",
        json={"reaction_type": "agree"},
        headers=hb,
    )
    after = (await client.get("/api/v1/users/me", headers=ha)).json()["karma"]
    assert after == before + 1


async def test_misleading_reaction_decreases_karma(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = (await create_comment(client, ha, post["id"])).json()

    before = (await client.get("/api/v1/users/me", headers=ha)).json()["karma"]
    await client.post(
        f"/api/v1/comments/{comment['id']}/reactions",
        json={"reaction_type": "misleading"},
        headers=hb,
    )
    after = (await client.get("/api/v1/users/me", headers=ha)).json()["karma"]
    assert after == before - 2


async def test_disagree_starts_inactive(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = (await create_comment(client, ha, post["id"])).json()

    before = (await client.get("/api/v1/users/me", headers=ha)).json()["karma"]
    await client.post(
        f"/api/v1/comments/{comment['id']}/reactions",
        json={"reaction_type": "disagree"},
        headers=hb,
    )
    after = (await client.get("/api/v1/users/me", headers=ha)).json()["karma"]
    # disagree has 0 karma effect
    assert after == before

    # But reaction count should not appear (inactive)
    r = await client.get(f"/api/v1/posts/{post['id']}/comments")
    found = next(c for c in r.json() if c["id"] == comment["id"])
    assert found["reaction_counts"].get("disagree", 0) == 0


async def test_disagree_activates_when_reply_left(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = (await create_comment(client, ha, post["id"])).json()

    await client.post(
        f"/api/v1/comments/{comment['id']}/reactions",
        json={"reaction_type": "disagree"},
        headers=hb,
    )
    # bob replies to alice's comment — disagree should activate
    await create_comment(client, hb, post["id"], "I disagree because...", parent_id=comment["id"])

    r = await client.get(f"/api/v1/posts/{post['id']}/comments")
    found = next(c for c in r.json() if c["id"] == comment["id"])
    assert found["reaction_counts"].get("disagree", 0) == 1


async def test_remove_reaction_reverses_karma(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)
    comment = (await create_comment(client, ha, post["id"])).json()

    await client.post(
        f"/api/v1/comments/{comment['id']}/reactions",
        json={"reaction_type": "love"},
        headers=hb,
    )
    before = (await client.get("/api/v1/users/me", headers=ha)).json()["karma"]
    await client.delete(f"/api/v1/comments/{comment['id']}/reactions/love", headers=hb)
    after = (await client.get("/api/v1/users/me", headers=ha)).json()["karma"]
    assert after == before - 2


# --- WebSocket new_comment notification ---

async def test_new_comment_notifies_post_author(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    with patch("app.api.v1.comments.publish_to_user", new_callable=AsyncMock) as mock_pub:
        await create_comment(client, hb, post["id"])
        # alice (post author) should be notified
        notified_ids = [call.args[0] for call in mock_pub.call_args_list]
        alice_id = (await client.get("/api/v1/users/me", headers=ha)).json()["id"]
        assert alice_id in notified_ids


# --- Shares ---

async def test_create_share(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    r = await client.post(f"/api/v1/posts/{post['id']}/share", json={}, headers=hb)
    assert r.status_code == 201
    data = r.json()
    assert data["shared_from_id"] == post["id"]
    assert data["author_id"] != post["author_id"]


async def test_share_with_comment(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    r = await client.post(
        f"/api/v1/posts/{post['id']}/share",
        json={"comment": "Check this out"},
        headers=hb,
    )
    assert r.status_code == 201
    assert r.json()["share_comment"] == "Check this out"


async def test_cannot_share_twice(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    post = await create_post(client, ha)

    await client.post(f"/api/v1/posts/{post['id']}/share", json={}, headers=hb)
    r = await client.post(f"/api/v1/posts/{post['id']}/share", json={}, headers=hb)
    assert r.status_code == 409


async def test_cannot_share_own_post(client):
    ha = await setup_user(client, "alice")
    post = await create_post(client, ha)

    r = await client.post(f"/api/v1/posts/{post['id']}/share", json={}, headers=ha)
    assert r.status_code == 400


async def test_sharing_a_share_links_to_original(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    hc = await setup_user(client, "carol")
    post = await create_post(client, ha)

    share = (await client.post(f"/api/v1/posts/{post['id']}/share", json={}, headers=hb)).json()
    # carol shares bob's share — should reference alice's original
    r = await client.post(f"/api/v1/posts/{share['id']}/share", json={}, headers=hc)
    assert r.status_code == 201
    assert r.json()["shared_from_id"] == post["id"]


async def test_upvote_share_gives_original_author_karma(client):
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")
    hc = await setup_user(client, "carol")
    post = await create_post(client, ha)
    share = (await client.post(f"/api/v1/posts/{post['id']}/share", json={}, headers=hb)).json()

    before = (await client.get("/api/v1/users/me", headers=ha)).json()["karma"]
    await client.post(f"/api/v1/posts/{share['id']}/vote", json={"direction": 1}, headers=hc)
    after = (await client.get("/api/v1/users/me", headers=ha)).json()["karma"]
    # Original author earns +1 bonus
    assert after >= before + 1
