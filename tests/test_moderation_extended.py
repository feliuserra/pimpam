"""
Extended moderation system tests.

Covers:
- Ban appeals: submit, cooldown, pending conflict, vote, overturn
- Ownership transfer: propose, re-propose cancels old, accept, reject
- Trusted member: auto-promote at karma 50, can vote on ban proposal
- Mod nomination with karma check (200 required)
- Community karma: updated on vote
"""
from datetime import datetime, timedelta, timezone

from tests.conftest import get_test_db, setup_user
from app.models.community import CommunityMember
from app.models.community_karma import CommunityKarma
from app.models.moderation import Ban, BanAppeal, OwnershipTransfer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _setup(client):
    """
    alice creates a community (making her owner).
    bob joins the community and creates a post.
    Returns (alice_h, bob_h, community, post).
    """
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    await client.post("/api/v1/communities", headers=alice_h, json={
        "name": "general", "description": "Test community"
    })
    community_r = await client.get("/api/v1/communities/general")
    community = community_r.json()

    await client.post("/api/v1/communities/general/join", headers=bob_h)
    post_r = await client.post("/api/v1/posts", headers=bob_h, json={
        "title": "Bob's post", "content": "Hello", "community_id": community["id"]
    })
    return alice_h, bob_h, community, post_r.json()


async def _get_user_id(client, username: str) -> int:
    r = await client.get(f"/api/v1/users/{username}")
    return r.json()["id"]


async def _seed_community_karma(user_id: int, community_id: int, karma: int) -> None:
    """Directly seed community karma for a user via DB session."""
    from sqlalchemy import select
    async for session in get_test_db():
        result = await session.execute(
            select(CommunityKarma).where(
                CommunityKarma.user_id == user_id,
                CommunityKarma.community_id == community_id,
            )
        )
        ck = result.scalar_one_or_none()
        if ck is None:
            session.add(CommunityKarma(user_id=user_id, community_id=community_id, karma=karma))
        else:
            ck.karma = karma
        await session.commit()


async def _set_member_role(user_id: int, community_id: int, role: str) -> None:
    """Directly set a community member's role via DB session."""
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


async def _create_active_ban(user_id: int, community_id: int) -> int:
    """Directly insert an active ban for the user. Returns ban id."""
    from sqlalchemy import select
    async for session in get_test_db():
        ban = Ban(
            community_id=community_id,
            user_id=user_id,
            reason="Test ban",
            coc_violation="spam",
            is_permanent=True,
            status="active",
        )
        session.add(ban)
        await session.commit()
        await session.refresh(ban)
        return ban.id
    raise RuntimeError("unreachable")


# ---------------------------------------------------------------------------
# Community karma: updated on vote
# ---------------------------------------------------------------------------

async def test_community_karma_updated_on_vote(client):
    """Voting on a community post updates the post author's community karma."""
    alice_h, bob_h, community, post = await _setup(client)
    # charlie votes on bob's community post
    charlie_h = await setup_user(client, "charlie")
    await client.post("/api/v1/communities/general/join", headers=charlie_h)

    r = await client.post(
        f"/api/v1/posts/{post['id']}/vote", headers=charlie_h, json={"direction": 1}
    )
    assert r.status_code == 200

    bob_id = await _get_user_id(client, "bob")
    from sqlalchemy import select
    async for session in get_test_db():
        result = await session.execute(
            select(CommunityKarma).where(
                CommunityKarma.user_id == bob_id,
                CommunityKarma.community_id == community["id"],
            )
        )
        ck = result.scalar_one_or_none()
        assert ck is not None
        assert ck.karma == 1


async def test_community_karma_not_updated_for_non_community_post(client):
    """Voting on a non-community post does NOT create a community_karma row."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    post_r = await client.post("/api/v1/posts", headers=alice_h, json={
        "title": "Plain post", "content": "No community"
    })
    post = post_r.json()

    await client.post(f"/api/v1/posts/{post['id']}/vote", headers=bob_h, json={"direction": 1})

    alice_id = await _get_user_id(client, "alice")
    from sqlalchemy import select
    async for session in get_test_db():
        result = await session.execute(
            select(CommunityKarma).where(CommunityKarma.user_id == alice_id)
        )
        rows = result.scalars().all()
        assert len(rows) == 0


# ---------------------------------------------------------------------------
# Trusted member: auto-promotion at karma 50
# ---------------------------------------------------------------------------

async def test_auto_promote_to_trusted_member_at_threshold(client):
    """Member auto-promotes to trusted_member when community karma reaches 50."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")

    # Seed karma to just below threshold
    await _seed_community_karma(bob_id, community["id"], 49)

    # One more upvote triggers threshold
    charlie_h = await setup_user(client, "charlie")
    await client.post("/api/v1/communities/general/join", headers=charlie_h)
    await client.post(f"/api/v1/posts/{post['id']}/vote", headers=charlie_h, json={"direction": 1})

    from sqlalchemy import select
    async for session in get_test_db():
        result = await session.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community["id"],
                CommunityMember.user_id == bob_id,
            )
        )
        member = result.scalar_one_or_none()
        assert member is not None
        assert member.role == "trusted_member"


async def test_auto_demote_from_trusted_member_below_threshold(client):
    """trusted_member reverts to member when community karma drops below 50."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")

    # Seed karma to 50 and set role to trusted_member
    await _seed_community_karma(bob_id, community["id"], 50)
    await _set_member_role(bob_id, community["id"], "trusted_member")

    # A downvote (by charlie) should drop karma to 49 and revert role
    charlie_h = await setup_user(client, "charlie")
    await client.post("/api/v1/communities/general/join", headers=charlie_h)
    await client.post(f"/api/v1/posts/{post['id']}/vote", headers=charlie_h, json={"direction": -1})

    from sqlalchemy import select
    async for session in get_test_db():
        result = await session.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community["id"],
                CommunityMember.user_id == bob_id,
            )
        )
        member = result.scalar_one_or_none()
        assert member is not None
        assert member.role == "member"


async def test_trusted_member_can_vote_on_ban_proposal(client):
    """A trusted_member can vote on a ban proposal."""
    alice_h, bob_h, community, post = await _setup(client)
    charlie_h = await setup_user(client, "charlie")
    await client.post("/api/v1/communities/general/join", headers=charlie_h)

    # Make charlie a trusted_member directly
    charlie_id = await _get_user_id(client, "charlie")
    await _set_member_role(charlie_id, community["id"], "trusted_member")

    # Alice proposes banning bob
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

    # Charlie votes on the proposal
    r = await client.post(
        f"/api/v1/communities/general/bans/{proposal_id}/vote", headers=charlie_h
    )
    assert r.status_code == 200
    assert r.json()["vote_count"] == 2


async def test_member_cannot_vote_on_ban_proposal(client):
    """A plain member (role='member') cannot vote on a ban proposal."""
    alice_h, bob_h, community, post = await _setup(client)
    charlie_h = await setup_user(client, "charlie")
    await client.post("/api/v1/communities/general/join", headers=charlie_h)
    # charlie is plain 'member'

    proposal_r = await client.post(
        "/api/v1/communities/general/bans", headers=alice_h, json={
            "target_username": "bob",
            "reason": "Spam",
            "coc_violation": "spam",
            "is_permanent": True,
        }
    )
    proposal_id = proposal_r.json()["id"]

    r = await client.post(
        f"/api/v1/communities/general/bans/{proposal_id}/vote", headers=charlie_h
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Mod nomination with karma check
# ---------------------------------------------------------------------------

async def test_propose_mod_requires_200_karma(client):
    """Nominating a user as moderator requires 200+ community karma."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")

    # bob has 0 community karma — should fail
    r = await client.post(
        "/api/v1/communities/general/moderators", headers=alice_h, json={
            "target_username": "bob",
            "target_role": "moderator",
        }
    )
    assert r.status_code == 400
    assert "200" in r.json()["detail"]


async def test_propose_senior_mod_requires_500_karma(client):
    """Nominating a user as senior_mod requires 500+ community karma."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")
    await _seed_community_karma(bob_id, community["id"], 400)

    r = await client.post(
        "/api/v1/communities/general/moderators", headers=alice_h, json={
            "target_username": "bob",
            "target_role": "senior_mod",
        }
    )
    assert r.status_code == 400
    assert "500" in r.json()["detail"]


async def test_propose_mod_promotion_with_valid_karma(client):
    """Proposing a moderator with 200+ community karma succeeds."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")
    await _seed_community_karma(bob_id, community["id"], 200)

    r = await client.post(
        "/api/v1/communities/general/moderators", headers=alice_h, json={
            "target_username": "bob",
            "target_role": "moderator",
        }
    )
    assert r.status_code == 201
    assert r.json()["target_role"] == "moderator"


async def test_mod_promotion_approves_and_sets_role(client):
    """When a mod proposal reaches required_votes, the member is promoted."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")
    await _seed_community_karma(bob_id, community["id"], 200)

    # required_votes = max(2, ceil(1 / 2)) = 2 with 1 mod
    # Add a second senior_mod so we can vote
    carol_h = await setup_user(client, "carol")
    await client.post("/api/v1/communities/general/join", headers=carol_h)
    carol_id = await _get_user_id(client, "carol")
    await _set_member_role(carol_id, community["id"], "senior_mod")

    # required_votes = max(2, ceil(2 / 2)) = max(2, 1) = 2
    proposal_r = await client.post(
        "/api/v1/communities/general/moderators", headers=alice_h, json={
            "target_username": "bob",
            "target_role": "moderator",
        }
    )
    assert proposal_r.status_code == 201
    proposal = proposal_r.json()
    assert proposal["required_votes"] == 2

    # Carol votes — reaches threshold
    vote_r = await client.post(
        f"/api/v1/communities/general/moderators/{proposal['id']}/vote", headers=carol_h
    )
    assert vote_r.status_code == 200
    assert vote_r.json()["status"] == "approved"

    # Bob's role should now be "moderator"
    from sqlalchemy import select
    async for session in get_test_db():
        result = await session.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community["id"],
                CommunityMember.user_id == bob_id,
            )
        )
        member = result.scalar_one_or_none()
        assert member is not None
        assert member.role == "moderator"


# ---------------------------------------------------------------------------
# Ban appeals
# ---------------------------------------------------------------------------

async def test_submit_ban_appeal(client):
    """A banned user can submit a ban appeal."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")
    ban_id = await _create_active_ban(bob_id, community["id"])

    r = await client.post(
        "/api/v1/communities/general/appeals", headers=bob_h, json={
            "ban_id": ban_id,
            "reason": "I was not spamming",
        }
    )
    assert r.status_code == 201
    body = r.json()
    assert body["ban_id"] == ban_id
    assert body["status"] == "pending"
    assert body["vote_count"] == 0
    assert body["required_votes"] == 10


async def test_submit_appeal_no_active_ban(client):
    """Submitting an appeal for a non-existent ban returns 404."""
    alice_h, bob_h, community, post = await _setup(client)

    r = await client.post(
        "/api/v1/communities/general/appeals", headers=bob_h, json={
            "ban_id": 999,
            "reason": "No ban here",
        }
    )
    assert r.status_code == 404


async def test_submit_appeal_pending_conflict(client):
    """Cannot submit a second appeal while one is already pending."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")
    ban_id = await _create_active_ban(bob_id, community["id"])

    await client.post(
        "/api/v1/communities/general/appeals", headers=bob_h, json={
            "ban_id": ban_id, "reason": "First appeal"
        }
    )
    r = await client.post(
        "/api/v1/communities/general/appeals", headers=bob_h, json={
            "ban_id": ban_id, "reason": "Second appeal"
        }
    )
    assert r.status_code == 409


async def test_submit_appeal_cooldown(client):
    """Cannot resubmit an appeal within 1 week of the last one."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")
    ban_id = await _create_active_ban(bob_id, community["id"])

    # Submit first appeal
    r1 = await client.post(
        "/api/v1/communities/general/appeals", headers=bob_h, json={
            "ban_id": ban_id, "reason": "First"
        }
    )
    assert r1.status_code == 201
    appeal_id = r1.json()["id"]

    # Backdate appeal so it's not pending (simulate resolved)
    from sqlalchemy import select
    async for session in get_test_db():
        result = await session.execute(select(BanAppeal).where(BanAppeal.id == appeal_id))
        appeal = result.scalar_one_or_none()
        if appeal:
            appeal.status = "rejected"
            # Keep created_at recent (within cooldown)
        await session.commit()

    # Try to submit another — should hit cooldown
    r2 = await client.post(
        "/api/v1/communities/general/appeals", headers=bob_h, json={
            "ban_id": ban_id, "reason": "Second within week"
        }
    )
    assert r2.status_code == 429


async def test_submit_appeal_after_cooldown(client):
    """Can resubmit after the 1-week cooldown has passed."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")
    ban_id = await _create_active_ban(bob_id, community["id"])

    # Submit first appeal
    r1 = await client.post(
        "/api/v1/communities/general/appeals", headers=bob_h, json={
            "ban_id": ban_id, "reason": "First"
        }
    )
    assert r1.status_code == 201
    appeal_id = r1.json()["id"]

    # Backdate by 8 days and mark rejected
    old_date = datetime.now(timezone.utc) - timedelta(days=8)
    from sqlalchemy import select
    async for session in get_test_db():
        result = await session.execute(select(BanAppeal).where(BanAppeal.id == appeal_id))
        appeal = result.scalar_one_or_none()
        if appeal:
            appeal.status = "rejected"
            appeal.created_at = old_date
        await session.commit()

    # Now can resubmit
    r2 = await client.post(
        "/api/v1/communities/general/appeals", headers=bob_h, json={
            "ban_id": ban_id, "reason": "After cooldown"
        }
    )
    assert r2.status_code == 201


async def test_vote_ban_appeal(client):
    """A moderator can vote on a ban appeal."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")
    ban_id = await _create_active_ban(bob_id, community["id"])

    appeal_r = await client.post(
        "/api/v1/communities/general/appeals", headers=bob_h, json={
            "ban_id": ban_id, "reason": "I was not spamming"
        }
    )
    appeal_id = appeal_r.json()["id"]

    # Alice is the owner (moderator+) and can vote
    r = await client.post(
        f"/api/v1/communities/general/appeals/{appeal_id}/vote", headers=alice_h
    )
    assert r.status_code == 200
    assert r.json()["vote_count"] == 1


async def test_vote_ban_appeal_duplicate(client):
    """Cannot vote twice on the same appeal."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")
    ban_id = await _create_active_ban(bob_id, community["id"])

    appeal_r = await client.post(
        "/api/v1/communities/general/appeals", headers=bob_h, json={
            "ban_id": ban_id, "reason": "Please"
        }
    )
    appeal_id = appeal_r.json()["id"]

    await client.post(f"/api/v1/communities/general/appeals/{appeal_id}/vote", headers=alice_h)
    r = await client.post(f"/api/v1/communities/general/appeals/{appeal_id}/vote", headers=alice_h)
    assert r.status_code == 409


async def test_ban_appeal_overturn(client):
    """When an appeal reaches 10 votes, the ban is overturned."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")
    ban_id = await _create_active_ban(bob_id, community["id"])

    appeal_r = await client.post(
        "/api/v1/communities/general/appeals", headers=bob_h, json={
            "ban_id": ban_id, "reason": "Wrongly banned"
        }
    )
    appeal_id = appeal_r.json()["id"]

    # Create 10 moderator users, each voting on the appeal
    voter_headers = []
    for i in range(10):
        username = f"mod{i}"
        h = await setup_user(client, username)
        await client.post("/api/v1/communities/general/join", headers=h)
        uid = await _get_user_id(client, username)
        await _set_member_role(uid, community["id"], "moderator")
        voter_headers.append(h)

    for i, h in enumerate(voter_headers):
        r = await client.post(
            f"/api/v1/communities/general/appeals/{appeal_id}/vote", headers=h
        )
        assert r.status_code == 200

    # Final state: appeal approved, ban overturned
    from sqlalchemy import select
    async for session in get_test_db():
        appeal_result = await session.execute(
            select(BanAppeal).where(BanAppeal.id == appeal_id)
        )
        appeal = appeal_result.scalar_one_or_none()
        assert appeal is not None
        assert appeal.status == "approved"

        ban_result = await session.execute(
            select(Ban).where(Ban.id == ban_id)
        )
        ban = ban_result.scalar_one_or_none()
        assert ban is not None
        assert ban.status == "overturned"


async def test_list_appeals(client):
    """Moderators can list pending ban appeals."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")
    ban_id = await _create_active_ban(bob_id, community["id"])

    await client.post(
        "/api/v1/communities/general/appeals", headers=bob_h, json={
            "ban_id": ban_id, "reason": "My appeal"
        }
    )

    r = await client.get("/api/v1/communities/general/appeals", headers=alice_h)
    assert r.status_code == 200
    assert len(r.json()) == 1


async def test_non_mod_cannot_list_appeals(client):
    """Regular members cannot list appeals."""
    alice_h, bob_h, community, post = await _setup(client)

    r = await client.get("/api/v1/communities/general/appeals", headers=bob_h)
    assert r.status_code == 403


async def test_voter_who_proposed_ban_cannot_vote_appeal(client):
    """A voter on the original ban proposal cannot vote on the appeal."""
    alice_h, bob_h, community, post = await _setup(client)
    bob_id = await _get_user_id(client, "bob")

    # Alice proposes a ban (auto-vote counted)
    proposal_r = await client.post(
        "/api/v1/communities/general/bans", headers=alice_h, json={
            "target_username": "bob",
            "reason": "Spam",
            "coc_violation": "spam",
            "is_permanent": True,
        }
    )
    proposal = proposal_r.json()

    # Manually create a Ban linked to the proposal (simulating approval)
    from sqlalchemy import select
    async for session in get_test_db():
        ban = Ban(
            community_id=community["id"],
            user_id=bob_id,
            reason="Spam",
            coc_violation="spam",
            is_permanent=True,
            status="active",
            proposal_id=proposal["id"],
        )
        session.add(ban)
        await session.commit()
        await session.refresh(ban)
        ban_id = ban.id

    # Bob submits appeal
    appeal_r = await client.post(
        "/api/v1/communities/general/appeals", headers=bob_h, json={
            "ban_id": ban_id, "reason": "I disagree"
        }
    )
    appeal_id = appeal_r.json()["id"]

    # Alice (who voted on original ban) tries to vote on appeal — should be 403
    r = await client.post(
        f"/api/v1/communities/general/appeals/{appeal_id}/vote", headers=alice_h
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Ownership transfer
# ---------------------------------------------------------------------------

async def test_propose_ownership_transfer(client):
    """A senior_mod+ can propose ownership transfer."""
    alice_h, bob_h, community, post = await _setup(client)

    r = await client.post(
        "/api/v1/communities/general/ownership-transfer", headers=alice_h, json={
            "recipient_username": "bob"
        }
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"


async def test_propose_transfer_to_self_fails(client):
    """Cannot propose ownership transfer to yourself."""
    alice_h, bob_h, community, post = await _setup(client)

    r = await client.post(
        "/api/v1/communities/general/ownership-transfer", headers=alice_h, json={
            "recipient_username": "alice"
        }
    )
    assert r.status_code == 400


async def test_propose_transfer_to_nonexistent_user(client):
    """Proposing transfer to a non-existent user returns 404."""
    alice_h, bob_h, community, post = await _setup(client)

    r = await client.post(
        "/api/v1/communities/general/ownership-transfer", headers=alice_h, json={
            "recipient_username": "ghost"
        }
    )
    assert r.status_code == 404


async def test_repropose_transfer_cancels_old(client):
    """Re-proposing an ownership transfer cancels the previous pending one."""
    alice_h, bob_h, community, post = await _setup(client)
    carol_h = await setup_user(client, "carol")
    await client.post("/api/v1/communities/general/join", headers=carol_h)

    # First proposal to bob
    r1 = await client.post(
        "/api/v1/communities/general/ownership-transfer", headers=alice_h, json={
            "recipient_username": "bob"
        }
    )
    assert r1.status_code == 201
    old_transfer_id = r1.json()["id"]

    # New proposal to carol — cancels the old one
    r2 = await client.post(
        "/api/v1/communities/general/ownership-transfer", headers=alice_h, json={
            "recipient_username": "carol"
        }
    )
    assert r2.status_code == 201

    from sqlalchemy import select
    async for session in get_test_db():
        result = await session.execute(
            select(OwnershipTransfer).where(OwnershipTransfer.id == old_transfer_id)
        )
        old = result.scalar_one_or_none()
        assert old is not None
        assert old.status == "rejected"


async def test_non_senior_mod_cannot_propose_transfer(client):
    """Only senior_mod+ can propose an ownership transfer."""
    alice_h, bob_h, community, post = await _setup(client)
    # Bob is a plain member
    r = await client.post(
        "/api/v1/communities/general/ownership-transfer", headers=bob_h, json={
            "recipient_username": "alice"
        }
    )
    assert r.status_code == 403


async def test_accept_ownership_transfer(client):
    """Recipient accepts: old owner becomes moderator, recipient becomes owner."""
    alice_h, bob_h, community, post = await _setup(client)

    transfer_r = await client.post(
        "/api/v1/communities/general/ownership-transfer", headers=alice_h, json={
            "recipient_username": "bob"
        }
    )
    transfer_id = transfer_r.json()["id"]

    r = await client.post(
        f"/api/v1/communities/general/ownership-transfer/{transfer_id}/respond",
        headers=bob_h, json={"accept": True}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"

    alice_id = await _get_user_id(client, "alice")
    bob_id = await _get_user_id(client, "bob")

    from sqlalchemy import select
    from app.models.community import Community
    async for session in get_test_db():
        # alice is now moderator
        result = await session.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community["id"],
                CommunityMember.user_id == alice_id,
            )
        )
        alice_member = result.scalar_one_or_none()
        assert alice_member is not None
        assert alice_member.role == "moderator"

        # bob is now owner
        result2 = await session.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community["id"],
                CommunityMember.user_id == bob_id,
            )
        )
        bob_member = result2.scalar_one_or_none()
        assert bob_member is not None
        assert bob_member.role == "owner"

        # community.owner_id updated
        c_result = await session.execute(
            select(Community).where(Community.id == community["id"])
        )
        c = c_result.scalar_one_or_none()
        assert c is not None
        assert c.owner_id == bob_id


async def test_reject_ownership_transfer(client):
    """Recipient rejects: status becomes rejected, no role changes."""
    alice_h, bob_h, community, post = await _setup(client)

    transfer_r = await client.post(
        "/api/v1/communities/general/ownership-transfer", headers=alice_h, json={
            "recipient_username": "bob"
        }
    )
    transfer_id = transfer_r.json()["id"]

    r = await client.post(
        f"/api/v1/communities/general/ownership-transfer/{transfer_id}/respond",
        headers=bob_h, json={"accept": False}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"

    alice_id = await _get_user_id(client, "alice")
    from sqlalchemy import select
    async for session in get_test_db():
        result = await session.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community["id"],
                CommunityMember.user_id == alice_id,
            )
        )
        alice_member = result.scalar_one_or_none()
        assert alice_member is not None
        assert alice_member.role == "owner"  # unchanged


async def test_non_recipient_cannot_respond_to_transfer(client):
    """Only the designated recipient can respond to an ownership transfer."""
    alice_h, bob_h, community, post = await _setup(client)
    carol_h = await setup_user(client, "carol")
    await client.post("/api/v1/communities/general/join", headers=carol_h)

    transfer_r = await client.post(
        "/api/v1/communities/general/ownership-transfer", headers=alice_h, json={
            "recipient_username": "bob"
        }
    )
    transfer_id = transfer_r.json()["id"]

    # Carol tries to respond — not the recipient
    r = await client.post(
        f"/api/v1/communities/general/ownership-transfer/{transfer_id}/respond",
        headers=carol_h, json={"accept": True}
    )
    assert r.status_code == 403


async def test_ownership_transfer_recipient_not_yet_member(client):
    """Transfer to a user who is not yet a community member still works on accept."""
    alice_h = await setup_user(client, "alice")
    dave_h = await setup_user(client, "dave")

    await client.post("/api/v1/communities", headers=alice_h, json={
        "name": "solo", "description": "Alice's community"
    })
    community_r = await client.get("/api/v1/communities/solo")
    community = community_r.json()

    # dave is not a member
    transfer_r = await client.post(
        "/api/v1/communities/solo/ownership-transfer", headers=alice_h, json={
            "recipient_username": "dave"
        }
    )
    assert transfer_r.status_code == 201
    transfer_id = transfer_r.json()["id"]

    r = await client.post(
        f"/api/v1/communities/solo/ownership-transfer/{transfer_id}/respond",
        headers=dave_h, json={"accept": True}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"

    dave_id = await _get_user_id(client, "dave")
    from sqlalchemy import select
    async for session in get_test_db():
        result = await session.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community["id"],
                CommunityMember.user_id == dave_id,
            )
        )
        dave_member = result.scalar_one_or_none()
        assert dave_member is not None
        assert dave_member.role == "owner"
