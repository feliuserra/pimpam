"""
Additional moderation tests covering:
- mod_remove_comment / mod_restore_comment endpoints
- Ban vote threshold (10 votes → auto-ban + list_bans returns the ban)
- Edge cases: wrong community, 404 paths, invalid target_role
"""
import pytest

from tests.conftest import get_test_db, setup_user, register
from app.models.community import CommunityMember
from app.models.community_karma import CommunityKarma
from app.models.moderation import Ban


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

async def _setup(client):
    """
    alice creates a community (owner).
    bob joins and creates a post + comment.
    Returns (alice_h, bob_h, community, post, comment).
    """
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    await client.post("/api/v1/communities", headers=alice_h, json={
        "name": "general", "description": "Test"
    })
    comm_r = await client.get("/api/v1/communities/general")
    community = comm_r.json()

    await client.post("/api/v1/communities/general/join", headers=bob_h)
    post_r = await client.post("/api/v1/posts", headers=bob_h, json={
        "title": "Post", "content": "body", "community_id": community["id"]
    })
    post = post_r.json()

    comment_r = await client.post(
        f"/api/v1/posts/{post['id']}/comments", headers=bob_h, json={"content": "A comment"}
    )
    comment = comment_r.json()
    return alice_h, bob_h, community, post, comment


async def _get_user_id(client, username):
    return (await client.get(f"/api/v1/users/{username}")).json()["id"]


async def _set_role(user_id, community_id, role):
    from sqlalchemy import select
    async for session in get_test_db():
        result = await session.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community_id,
                CommunityMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if member:
            member.role = role
        await session.commit()


# ---------------------------------------------------------------------------
# Comment moderation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mod_remove_comment(client):
    alice_h, bob_h, community, post, comment = await _setup(client)
    r = await client.delete(
        f"/api/v1/communities/general/comments/{comment['id']}", headers=alice_h
    )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_removed_comment_hidden_in_thread(client):
    alice_h, bob_h, community, post, comment = await _setup(client)
    await client.delete(
        f"/api/v1/communities/general/comments/{comment['id']}", headers=alice_h
    )
    r = await client.get(f"/api/v1/posts/{post['id']}/comments")
    assert r.status_code == 200
    c = next((c for c in r.json() if c["id"] == comment["id"]), None)
    assert c is not None
    assert c["is_removed"] is True
    assert c["content"] == "[deleted]"


@pytest.mark.asyncio
async def test_mod_restore_comment(client):
    alice_h, bob_h, community, post, comment = await _setup(client)
    await client.delete(
        f"/api/v1/communities/general/comments/{comment['id']}", headers=alice_h
    )
    r = await client.post(
        f"/api/v1/communities/general/comments/{comment['id']}/restore", headers=alice_h
    )
    assert r.status_code == 204

    # Content visible again
    thread = (await client.get(f"/api/v1/posts/{post['id']}/comments")).json()
    c = next(c for c in thread if c["id"] == comment["id"])
    assert c["is_removed"] is False
    assert c["content"] == "A comment"


@pytest.mark.asyncio
async def test_non_mod_cannot_remove_comment(client):
    alice_h, bob_h, community, post, comment = await _setup(client)
    # bob is not a mod
    r = await client.delete(
        f"/api/v1/communities/general/comments/{comment['id']}", headers=bob_h
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_remove_comment_wrong_community(client):
    alice_h, bob_h, community, post, comment = await _setup(client)

    # Create a second community owned by alice
    await client.post("/api/v1/communities", headers=alice_h, json={
        "name": "other", "description": "Other"
    })

    # Try to remove the comment through the wrong community
    r = await client.delete(
        f"/api/v1/communities/other/comments/{comment['id']}", headers=alice_h
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_remove_comment_not_found(client):
    alice_h, _, _, _, _ = await _setup(client)
    r = await client.delete(
        "/api/v1/communities/general/comments/9999", headers=alice_h
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_restore_comment_wrong_community(client):
    alice_h, bob_h, community, post, comment = await _setup(client)
    await client.delete(
        f"/api/v1/communities/general/comments/{comment['id']}", headers=alice_h
    )
    await client.post("/api/v1/communities", headers=alice_h, json={
        "name": "other", "description": "Other"
    })
    r = await client.post(
        f"/api/v1/communities/other/comments/{comment['id']}/restore", headers=alice_h
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Ban vote threshold → auto-ban + list_bans
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ban_proposal_auto_bans_at_threshold(client):
    """When 10 votes are cast, the ban proposal is approved and a Ban row is created."""
    alice_h, bob_h, community, post, comment = await _setup(client)

    proposal_r = await client.post(
        "/api/v1/communities/general/bans", headers=alice_h, json={
            "target_username": "bob",
            "reason": "Spam",
            "coc_violation": "spam",
            "is_permanent": True,
        }
    )
    assert proposal_r.status_code == 201
    proposal_id = proposal_r.json()["id"]

    # Create 9 more trusted_member voters (proposer already counted as vote 1)
    voter_headers = []
    for i in range(9):
        username = f"voter{i}"
        h = await setup_user(client, username)
        await client.post("/api/v1/communities/general/join", headers=h)
        uid = await _get_user_id(client, username)
        await _set_role(uid, community["id"], "trusted_member")
        voter_headers.append(h)

    for i, h in enumerate(voter_headers):
        r = await client.post(
            f"/api/v1/communities/general/bans/{proposal_id}/vote", headers=h
        )
        assert r.status_code == 200

    # Final vote count = 10 → approved
    last = r.json()
    assert last["vote_count"] == 10
    assert last["status"] == "approved"


@pytest.mark.asyncio
async def test_list_bans_shows_active_ban(client):
    """After a ban proposal reaches threshold, the ban appears in GET /bans."""
    alice_h, bob_h, community, post, comment = await _setup(client)

    proposal_r = await client.post(
        "/api/v1/communities/general/bans", headers=alice_h, json={
            "target_username": "bob",
            "reason": "Spam",
            "coc_violation": "spam",
            "is_permanent": True,
        }
    )
    proposal_id = proposal_r.json()["id"]

    # 9 more voters (names must be ≥3 chars)
    voter_headers = []
    for i in range(9):
        username = f"usr{i}"
        h = await setup_user(client, username)
        await client.post("/api/v1/communities/general/join", headers=h)
        uid = await _get_user_id(client, username)
        await _set_role(uid, community["id"], "trusted_member")
        voter_headers.append(h)

    for h in voter_headers:
        await client.post(f"/api/v1/communities/general/bans/{proposal_id}/vote", headers=h)

    r = await client.get("/api/v1/communities/general/bans", headers=alice_h)
    assert r.status_code == 200
    bans = r.json()
    assert len(bans) == 1
    assert bans[0]["is_permanent"] is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_propose_ban_target_not_found(client):
    alice_h, bob_h, community, post, comment = await _setup(client)
    r = await client.post(
        "/api/v1/communities/general/bans", headers=alice_h, json={
            "target_username": "ghost",
            "reason": "Test",
            "coc_violation": "spam",
            "is_permanent": False,
        }
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_vote_ban_proposal_not_found(client):
    alice_h, _, _, _, _ = await _setup(client)
    r = await client.post(
        "/api/v1/communities/general/bans/9999/vote", headers=alice_h
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_vote_mod_proposal_not_found(client):
    alice_h, _, _, _, _ = await _setup(client)
    r = await client.post(
        "/api/v1/communities/general/moderators/9999/vote", headers=alice_h
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_propose_mod_target_not_found(client):
    alice_h, _, _, _, _ = await _setup(client)
    r = await client.post(
        "/api/v1/communities/general/moderators", headers=alice_h, json={
            "target_username": "ghost"
        }
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_propose_mod_invalid_role(client):
    alice_h, bob_h, community, post, comment = await _setup(client)
    bob_id = await _get_user_id(client, "bob")
    # Seed enough karma
    async for session in get_test_db():
        session.add(CommunityKarma(user_id=bob_id, community_id=community["id"], karma=200))
        await session.commit()

    r = await client.post(
        "/api/v1/communities/general/moderators", headers=alice_h, json={
            "target_username": "bob",
            "target_role": "god",  # invalid
        }
    )
    assert r.status_code == 400
    assert "target_role" in r.json()["detail"]


@pytest.mark.asyncio
async def test_vote_appeal_not_found(client):
    alice_h, _, _, _, _ = await _setup(client)
    r = await client.post(
        "/api/v1/communities/general/appeals/9999/vote", headers=alice_h
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_community_not_found_returns_404(client):
    hdrs = await setup_user(client, "alice")
    r = await client.get("/api/v1/communities/nonexistent/bans", headers=hdrs)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_propose_mod_cannot_propose_self(client):
    alice_h, _, _, _, _ = await _setup(client)
    r = await client.post(
        "/api/v1/communities/general/moderators", headers=alice_h, json={
            "target_username": "alice"
        }
    )
    assert r.status_code == 400
