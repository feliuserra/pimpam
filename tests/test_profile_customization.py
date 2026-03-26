"""
Tests for profile customization: new fields, pin/unpin, community stats.
"""

import pytest

from tests.conftest import setup_user

# ---------------------------------------------------------------------------
# PATCH /users/me — new profile fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_cover_image_url(client):
    hdrs = await setup_user(client, "alice")
    r = await client.patch(
        "/api/v1/users/me",
        json={"cover_image_url": "https://example.com/cover.webp"},
        headers=hdrs,
    )
    assert r.status_code == 200
    assert r.json()["cover_image_url"] == "https://example.com/cover.webp"


@pytest.mark.asyncio
async def test_update_accent_color_valid(client):
    hdrs = await setup_user(client, "alice")
    r = await client.patch(
        "/api/v1/users/me", json={"accent_color": "#ff5500"}, headers=hdrs
    )
    assert r.status_code == 200
    assert r.json()["accent_color"] == "#ff5500"


@pytest.mark.asyncio
async def test_update_accent_color_invalid_format(client):
    hdrs = await setup_user(client, "alice")
    r = await client.patch(
        "/api/v1/users/me", json={"accent_color": "red"}, headers=hdrs
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_accent_color_too_light(client):
    hdrs = await setup_user(client, "alice")
    r = await client.patch(
        "/api/v1/users/me", json={"accent_color": "#ffffff"}, headers=hdrs
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_accent_color_clear(client):
    hdrs = await setup_user(client, "alice")
    # Set then clear
    await client.patch(
        "/api/v1/users/me", json={"accent_color": "#ff5500"}, headers=hdrs
    )
    r = await client.patch("/api/v1/users/me", json={"accent_color": ""}, headers=hdrs)
    assert r.status_code == 200
    assert r.json()["accent_color"] is None


@pytest.mark.asyncio
async def test_update_location(client):
    hdrs = await setup_user(client, "alice")
    r = await client.patch(
        "/api/v1/users/me", json={"location": "Barcelona, Spain"}, headers=hdrs
    )
    assert r.status_code == 200
    assert r.json()["location"] == "Barcelona, Spain"


@pytest.mark.asyncio
async def test_update_website_valid(client):
    hdrs = await setup_user(client, "alice")
    r = await client.patch(
        "/api/v1/users/me", json={"website": "https://pimpam.org"}, headers=hdrs
    )
    assert r.status_code == 200
    assert r.json()["website"] == "https://pimpam.org"


@pytest.mark.asyncio
async def test_update_website_invalid(client):
    hdrs = await setup_user(client, "alice")
    r = await client.patch(
        "/api/v1/users/me", json={"website": "not-a-url"}, headers=hdrs
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_website_clear(client):
    hdrs = await setup_user(client, "alice")
    await client.patch(
        "/api/v1/users/me", json={"website": "https://example.com"}, headers=hdrs
    )
    r = await client.patch("/api/v1/users/me", json={"website": ""}, headers=hdrs)
    assert r.status_code == 200
    assert r.json()["website"] is None


@pytest.mark.asyncio
async def test_update_pronouns(client):
    hdrs = await setup_user(client, "alice")
    r = await client.patch(
        "/api/v1/users/me", json={"pronouns": "they/them"}, headers=hdrs
    )
    assert r.status_code == 200
    assert r.json()["pronouns"] == "they/them"


@pytest.mark.asyncio
async def test_update_profile_layout_valid(client):
    hdrs = await setup_user(client, "alice")
    layout = ["community_stats", "bio", "pinned_post"]
    r = await client.patch(
        "/api/v1/users/me", json={"profile_layout": layout}, headers=hdrs
    )
    assert r.status_code == 200
    assert r.json()["profile_layout"] == layout


@pytest.mark.asyncio
async def test_update_profile_layout_invalid_section(client):
    hdrs = await setup_user(client, "alice")
    r = await client.patch(
        "/api/v1/users/me",
        json={"profile_layout": ["bio", "invalid_section"]},
        headers=hdrs,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_profile_layout_duplicates(client):
    hdrs = await setup_user(client, "alice")
    r = await client.patch(
        "/api/v1/users/me",
        json={"profile_layout": ["bio", "bio"]},
        headers=hdrs,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_show_community_stats(client):
    hdrs = await setup_user(client, "alice")
    r = await client.patch(
        "/api/v1/users/me", json={"show_community_stats": False}, headers=hdrs
    )
    assert r.status_code == 200
    assert r.json()["show_community_stats"] is False


@pytest.mark.asyncio
async def test_new_fields_in_public_profile(client):
    hdrs = await setup_user(client, "alice")
    await client.patch(
        "/api/v1/users/me",
        json={
            "location": "Berlin",
            "pronouns": "she/her",
            "accent_color": "#3b82f6",
        },
        headers=hdrs,
    )
    r = await client.get("/api/v1/users/alice")
    assert r.status_code == 200
    data = r.json()
    assert data["location"] == "Berlin"
    assert data["pronouns"] == "she/her"
    assert data["accent_color"] == "#3b82f6"


# ---------------------------------------------------------------------------
# Pin / Unpin post
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pin_own_post(client):
    hdrs = await setup_user(client, "alice")
    post = await client.post(
        "/api/v1/posts",
        json={"title": "My best post", "content": "Look at this"},
        headers=hdrs,
    )
    post_id = post.json()["id"]

    r = await client.post(f"/api/v1/users/me/pin/{post_id}", headers=hdrs)
    assert r.status_code == 204

    # Verify pinned_post_id in profile
    profile = await client.get("/api/v1/users/me", headers=hdrs)
    assert profile.json()["pinned_post_id"] == post_id


@pytest.mark.asyncio
async def test_pin_someone_elses_post_forbidden(client):
    hdrs_alice = await setup_user(client, "alice")
    hdrs_bob = await setup_user(client, "bob")

    post = await client.post(
        "/api/v1/posts",
        json={"title": "Bob's post", "content": "hi"},
        headers=hdrs_bob,
    )
    post_id = post.json()["id"]

    r = await client.post(f"/api/v1/users/me/pin/{post_id}", headers=hdrs_alice)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_pin_nonexistent_post(client):
    hdrs = await setup_user(client, "alice")
    r = await client.post("/api/v1/users/me/pin/99999", headers=hdrs)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_unpin_post(client):
    hdrs = await setup_user(client, "alice")
    post = await client.post(
        "/api/v1/posts",
        json={"title": "Pinned", "content": "content"},
        headers=hdrs,
    )
    post_id = post.json()["id"]
    await client.post(f"/api/v1/users/me/pin/{post_id}", headers=hdrs)

    r = await client.delete("/api/v1/users/me/pin", headers=hdrs)
    assert r.status_code == 204

    profile = await client.get("/api/v1/users/me", headers=hdrs)
    assert profile.json()["pinned_post_id"] is None


@pytest.mark.asyncio
async def test_unpin_when_nothing_pinned(client):
    hdrs = await setup_user(client, "alice")
    r = await client.delete("/api/v1/users/me/pin", headers=hdrs)
    assert r.status_code == 204  # idempotent


# ---------------------------------------------------------------------------
# Community stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_community_stats_empty(client):
    hdrs = await setup_user(client, "alice")
    r = await client.get("/api/v1/users/alice/community-stats", headers=hdrs)
    assert r.status_code == 200
    data = r.json()
    assert data["joined"] == 0
    assert data["moderating"] == 0
    assert data["owned"] == 0


@pytest.mark.asyncio
async def test_community_stats_with_memberships(client):
    hdrs = await setup_user(client, "alice")

    # Create a community (alice becomes owner)
    await client.post(
        "/api/v1/communities",
        json={"name": "testcom", "description": "test"},
        headers=hdrs,
    )

    r = await client.get("/api/v1/users/alice/community-stats", headers=hdrs)
    data = r.json()
    assert data["joined"] == 1
    assert data["owned"] == 1


@pytest.mark.asyncio
async def test_community_stats_hidden(client):
    hdrs_alice = await setup_user(client, "alice")
    hdrs_bob = await setup_user(client, "bob")

    # Alice hides community stats
    await client.patch(
        "/api/v1/users/me", json={"show_community_stats": False}, headers=hdrs_alice
    )

    # Bob can't see Alice's stats
    r = await client.get("/api/v1/users/alice/community-stats", headers=hdrs_bob)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_community_stats_hidden_visible_to_self(client):
    hdrs = await setup_user(client, "alice")

    await client.patch(
        "/api/v1/users/me", json={"show_community_stats": False}, headers=hdrs
    )

    # Alice can still see her own stats
    r = await client.get("/api/v1/users/alice/community-stats", headers=hdrs)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_community_stats_unauthenticated(client):
    await setup_user(client, "alice")
    r = await client.get("/api/v1/users/alice/community-stats")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# GDPR export includes new fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_export_includes_new_fields(client):
    hdrs = await setup_user(client, "alice")
    await client.patch(
        "/api/v1/users/me",
        json={
            "location": "Paris",
            "website": "https://example.com",
            "pronouns": "he/him",
        },
        headers=hdrs,
    )
    r = await client.get("/api/v1/users/me/data-export", headers=hdrs)
    assert r.status_code == 200
    profile = r.json()["profile"]
    assert profile["location"] == "Paris"
    assert profile["website"] == "https://example.com"
    assert profile["pronouns"] == "he/him"
    assert "cover_image_url" in profile
    assert "accent_color" in profile
