"""
Integration tests for community karma accrual and trusted_member auto-promotion.

Scenario:
- alice creates a community and is its owner
- bob joins the community and creates posts inside it
- charlie votes on bob's posts
- Each upvote should increase bob's community karma by 1 and decrease by 1 on retract/downvote
- At 50 community karma points bob's role should be auto-promoted to trusted_member
"""

from tests.conftest import setup_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_community(client, headers, name="testcommunity"):
    r = await client.post(
        "/api/v1/communities",
        headers=headers,
        json={"name": name, "description": "Test community"},
    )
    assert r.status_code == 201
    return r.json()


async def _post_in_community(client, headers, community_name, title="A post"):
    # Resolve community name → id
    cr = await client.get(f"/api/v1/communities/{community_name}")
    assert cr.status_code == 200, f"Community {community_name!r} not found"
    community_id = cr.json()["id"]

    r = await client.post(
        "/api/v1/posts",
        headers=headers,
        json={
            "title": title,
            "content": "Post content.",
            "community_id": community_id,
        },
    )
    assert r.status_code == 201
    return r.json()


async def _get_member_karma(client, community_name, username):
    r = await client.get(
        f"/api/v1/communities/{community_name}/members/{username}/karma"
    )
    assert r.status_code == 200
    return r.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_karma_endpoint_requires_member(client):
    """Querying karma for a non-member returns 404."""
    alice_h = await setup_user(client, "alice")
    await setup_user(client, "bob")  # registers bob but he never joins
    await _create_community(client, alice_h, "general")

    r = await client.get("/api/v1/communities/general/members/bob/karma")
    assert r.status_code == 404


async def test_member_starts_at_zero_karma(client):
    """A freshly joined member has 0 community karma."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await _create_community(client, alice_h, "general")
    await client.post("/api/v1/communities/general/join", headers=bob_h)

    data = await _get_member_karma(client, "general", "bob")
    assert data["karma"] == 0
    assert data["role"] == "member"


async def test_upvote_accrues_community_karma(client):
    """An upvote on a community post adds +1 to the author's community karma."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    charlie_h = await setup_user(client, "charlie")

    await _create_community(client, alice_h, "general")
    await client.post("/api/v1/communities/general/join", headers=bob_h)
    await client.post("/api/v1/communities/general/join", headers=charlie_h)

    post = await _post_in_community(client, bob_h, "general")
    r = await client.post(
        f"/api/v1/posts/{post['id']}/vote", headers=charlie_h, json={"direction": 1}
    )
    assert r.status_code == 200

    data = await _get_member_karma(client, "general", "bob")
    assert data["karma"] == 1


async def test_downvote_decreases_community_karma(client):
    """A downvote on a community post subtracts 1 from the author's community karma."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    charlie_h = await setup_user(client, "charlie")

    await _create_community(client, alice_h, "general")
    await client.post("/api/v1/communities/general/join", headers=bob_h)
    await client.post("/api/v1/communities/general/join", headers=charlie_h)

    post = await _post_in_community(client, bob_h, "general")
    await client.post(
        f"/api/v1/posts/{post['id']}/vote", headers=charlie_h, json={"direction": -1}
    )

    data = await _get_member_karma(client, "general", "bob")
    assert data["karma"] == -1


async def test_retract_vote_reverses_community_karma(client):
    """Retracting an upvote removes the +1 from community karma."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    charlie_h = await setup_user(client, "charlie")

    await _create_community(client, alice_h, "general")
    await client.post("/api/v1/communities/general/join", headers=bob_h)
    await client.post("/api/v1/communities/general/join", headers=charlie_h)

    post = await _post_in_community(client, bob_h, "general")
    await client.post(
        f"/api/v1/posts/{post['id']}/vote", headers=charlie_h, json={"direction": 1}
    )
    await client.delete(f"/api/v1/posts/{post['id']}/vote", headers=charlie_h)

    data = await _get_member_karma(client, "general", "bob")
    assert data["karma"] == 0


async def test_vote_on_non_community_post_does_not_affect_community_karma(client):
    """Votes on posts outside any community do not create a community karma row."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    charlie_h = await setup_user(client, "charlie")

    await _create_community(client, alice_h, "general")
    await client.post("/api/v1/communities/general/join", headers=bob_h)

    # Post NOT inside any community
    r = await client.post(
        "/api/v1/posts",
        headers=bob_h,
        json={"title": "Off-topic", "content": "No community"},
    )
    assert r.status_code == 201
    post = r.json()

    await client.post(
        f"/api/v1/posts/{post['id']}/vote", headers=charlie_h, json={"direction": 1}
    )

    # bob's community karma should still be 0
    data = await _get_member_karma(client, "general", "bob")
    assert data["karma"] == 0


async def test_community_karma_is_scoped_per_community(client):
    """Karma earned in one community does not affect another community's karma."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    charlie_h = await setup_user(client, "charlie")

    await _create_community(client, alice_h, "alpha")
    await _create_community(client, alice_h, "beta")
    await client.post("/api/v1/communities/alpha/join", headers=bob_h)
    await client.post("/api/v1/communities/beta/join", headers=bob_h)
    await client.post("/api/v1/communities/alpha/join", headers=charlie_h)

    post = await _post_in_community(client, bob_h, "alpha")
    await client.post(
        f"/api/v1/posts/{post['id']}/vote", headers=charlie_h, json={"direction": 1}
    )

    alpha_data = await _get_member_karma(client, "alpha", "bob")
    beta_data = await _get_member_karma(client, "beta", "bob")

    assert alpha_data["karma"] == 1
    assert beta_data["karma"] == 0


async def test_trusted_member_promotion_at_threshold(client):
    """
    When a member's community karma reaches 50, their role is automatically
    promoted to trusted_member.
    """
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await _create_community(client, alice_h, "general")
    await client.post("/api/v1/communities/general/join", headers=bob_h)

    # Register 50 unique voters and have each cast an upvote on a separate post.
    # Using one voter per post avoids the "cannot vote twice" constraint.
    for i in range(50):
        voter_name = f"voter{i}"
        voter_h = await setup_user(client, voter_name)
        await client.post("/api/v1/communities/general/join", headers=voter_h)
        post = await _post_in_community(client, bob_h, "general", title=f"Post {i}")
        r = await client.post(
            f"/api/v1/posts/{post['id']}/vote", headers=voter_h, json={"direction": 1}
        )
        assert r.status_code == 200

    data = await _get_member_karma(client, "general", "bob")
    assert data["karma"] == 50
    assert data["role"] == "trusted_member"


async def test_role_reverted_when_karma_drops_below_threshold(client):
    """
    If a trusted_member's karma falls back below 50, their role reverts to member.
    """
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await _create_community(client, alice_h, "general")
    await client.post("/api/v1/communities/general/join", headers=bob_h)

    # Get bob to exactly 50 karma (trusted_member)
    posts_and_voters = []
    for i in range(50):
        voter_name = f"voter{i}"
        voter_h = await setup_user(client, voter_name)
        await client.post("/api/v1/communities/general/join", headers=voter_h)
        post = await _post_in_community(client, bob_h, "general", title=f"Post {i}")
        await client.post(
            f"/api/v1/posts/{post['id']}/vote", headers=voter_h, json={"direction": 1}
        )
        posts_and_voters.append((post, voter_h))

    data = await _get_member_karma(client, "general", "bob")
    assert data["role"] == "trusted_member"

    # One voter retracts their vote — drops karma back to 49
    last_post, last_voter_h = posts_and_voters[-1]
    r = await client.delete(
        f"/api/v1/posts/{last_post['id']}/vote", headers=last_voter_h
    )
    assert r.status_code == 204

    data = await _get_member_karma(client, "general", "bob")
    assert data["karma"] == 49
    assert data["role"] == "member"


async def test_karma_endpoint_community_not_found(client):
    r = await client.get("/api/v1/communities/nonexistent/members/alice/karma")
    assert r.status_code == 404


async def test_karma_endpoint_user_not_found(client):
    alice_h = await setup_user(client, "alice")
    await _create_community(client, alice_h, "general")
    r = await client.get("/api/v1/communities/general/members/ghost/karma")
    assert r.status_code == 404
