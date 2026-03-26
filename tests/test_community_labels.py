"""Tests for community labels CRUD and API endpoints."""

import pytest

from tests.conftest import setup_user


@pytest.fixture
async def mod_community(client):
    """Create a community and return (owner_headers, community_name)."""
    owner = await setup_user(client, "labelowner")
    r = await client.post(
        "/api/v1/communities",
        json={"name": "labeltest", "description": "Label testing community"},
        headers=owner,
    )
    assert r.status_code == 201
    return owner, "labeltest"


# --- List labels (public) ---


@pytest.mark.asyncio
async def test_list_labels_empty(client, mod_community):
    _, name = mod_community
    r = await client.get(f"/api/v1/communities/{name}/labels")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_labels_returns_ordered(client, mod_community):
    owner, name = mod_community
    await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "Discussion"},
        headers=owner,
    )
    await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "Question", "color": "#00ff00"},
        headers=owner,
    )
    r = await client.get(f"/api/v1/communities/{name}/labels")
    assert r.status_code == 200
    labels = r.json()
    assert len(labels) == 2
    assert labels[0]["name"] == "Discussion"
    assert labels[1]["name"] == "Question"
    assert labels[1]["color"] == "#00ff00"
    assert labels[0]["position"] < labels[1]["position"]


# --- Create label ---


@pytest.mark.asyncio
async def test_create_label(client, mod_community):
    owner, name = mod_community
    r = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={
            "name": "Announcement",
            "color": "#ff0000",
            "description": "Official posts",
        },
        headers=owner,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Announcement"
    assert data["color"] == "#ff0000"
    assert data["description"] == "Official posts"
    assert "id" in data
    assert "position" in data


@pytest.mark.asyncio
async def test_create_label_duplicate_name_rejected(client, mod_community):
    owner, name = mod_community
    await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "Discussion"},
        headers=owner,
    )
    r = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "Discussion"},
        headers=owner,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_create_label_non_mod_forbidden(client, mod_community):
    _, name = mod_community
    member = await setup_user(client, "labelmember")
    r = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "Forbidden"},
        headers=member,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_create_label_strips_whitespace(client, mod_community):
    owner, name = mod_community
    r = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "  Padded  "},
        headers=owner,
    )
    assert r.status_code == 201
    assert r.json()["name"] == "Padded"


# --- Update label ---


@pytest.mark.asyncio
async def test_update_label(client, mod_community):
    owner, name = mod_community
    create_r = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "Old Name"},
        headers=owner,
    )
    label_id = create_r.json()["id"]
    r = await client.patch(
        f"/api/v1/communities/{name}/labels/{label_id}",
        json={"name": "New Name", "color": "#0000ff"},
        headers=owner,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"
    assert r.json()["color"] == "#0000ff"


@pytest.mark.asyncio
async def test_update_label_duplicate_name_rejected(client, mod_community):
    owner, name = mod_community
    await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "Alpha"},
        headers=owner,
    )
    create_r = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "Beta"},
        headers=owner,
    )
    label_id = create_r.json()["id"]
    r = await client.patch(
        f"/api/v1/communities/{name}/labels/{label_id}",
        json={"name": "Alpha"},
        headers=owner,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_update_label_wrong_community_404(client, mod_community):
    owner, name = mod_community
    # Create a second community
    await client.post(
        "/api/v1/communities",
        json={"name": "other", "description": "Other community"},
        headers=owner,
    )
    create_r = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "InOriginal"},
        headers=owner,
    )
    label_id = create_r.json()["id"]
    # Try to update via wrong community
    r = await client.patch(
        f"/api/v1/communities/other/labels/{label_id}",
        json={"name": "Hacked"},
        headers=owner,
    )
    assert r.status_code == 404


# --- Delete label ---


@pytest.mark.asyncio
async def test_delete_label(client, mod_community):
    owner, name = mod_community
    create_r = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "ToDelete"},
        headers=owner,
    )
    label_id = create_r.json()["id"]
    r = await client.delete(
        f"/api/v1/communities/{name}/labels/{label_id}",
        headers=owner,
    )
    assert r.status_code == 204
    # Verify it's gone
    list_r = await client.get(f"/api/v1/communities/{name}/labels")
    assert len(list_r.json()) == 0


@pytest.mark.asyncio
async def test_delete_label_non_mod_forbidden(client, mod_community):
    owner, name = mod_community
    create_r = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "Protected"},
        headers=owner,
    )
    label_id = create_r.json()["id"]
    member = await setup_user(client, "notmod")
    r = await client.delete(
        f"/api/v1/communities/{name}/labels/{label_id}",
        headers=member,
    )
    assert r.status_code == 403


# --- Reorder labels ---


@pytest.mark.asyncio
async def test_reorder_labels(client, mod_community):
    owner, name = mod_community
    r1 = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "First"},
        headers=owner,
    )
    r2 = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "Second"},
        headers=owner,
    )
    r3 = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "Third"},
        headers=owner,
    )
    id1, id2, id3 = r1.json()["id"], r2.json()["id"], r3.json()["id"]

    # Reverse order
    r = await client.put(
        f"/api/v1/communities/{name}/labels/reorder",
        json={"ids": [id3, id2, id1]},
        headers=owner,
    )
    assert r.status_code == 200
    labels = r.json()
    assert labels[0]["name"] == "Third"
    assert labels[1]["name"] == "Second"
    assert labels[2]["name"] == "First"


# --- Post with label ---


@pytest.mark.asyncio
async def test_post_with_label(client, mod_community):
    owner, name = mod_community
    # Join community
    await client.post(f"/api/v1/communities/{name}/join", headers=owner)
    # Create label
    label_r = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "Discussion"},
        headers=owner,
    )
    label_id = label_r.json()["id"]
    # Get community ID
    comm_r = await client.get(f"/api/v1/communities/{name}")
    community_id = comm_r.json()["id"]
    # Create post with label
    post_r = await client.post(
        "/api/v1/posts",
        json={
            "title": "Labeled post",
            "content": "Has a label",
            "community_id": community_id,
            "label_id": label_id,
        },
        headers=owner,
    )
    assert post_r.status_code == 201
    data = post_r.json()
    assert data["label_id"] == label_id
    assert data["label"]["name"] == "Discussion"


@pytest.mark.asyncio
async def test_post_with_wrong_community_label_rejected(client, mod_community):
    owner, name = mod_community
    await client.post(f"/api/v1/communities/{name}/join", headers=owner)
    # Create label in labeltest community
    label_r = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "WrongLabel"},
        headers=owner,
    )
    label_id = label_r.json()["id"]
    # Create second community
    await client.post(
        "/api/v1/communities",
        json={"name": "other2", "description": "Other"},
        headers=owner,
    )
    await client.post("/api/v1/communities/other2/join", headers=owner)
    comm_r = await client.get("/api/v1/communities/other2")
    other_id = comm_r.json()["id"]
    # Try to use label from first community on second community's post
    post_r = await client.post(
        "/api/v1/posts",
        json={
            "title": "Cross community",
            "content": "Wrong label",
            "community_id": other_id,
            "label_id": label_id,
        },
        headers=owner,
    )
    assert post_r.status_code == 400


@pytest.mark.asyncio
async def test_label_on_non_community_post_rejected(client, mod_community):
    owner, name = mod_community
    label_r = await client.post(
        f"/api/v1/communities/{name}/labels",
        json={"name": "NoComm"},
        headers=owner,
    )
    label_id = label_r.json()["id"]
    # Post without community_id but with label_id
    post_r = await client.post(
        "/api/v1/posts",
        json={
            "title": "No community",
            "content": "Has label but no community",
            "label_id": label_id,
        },
        headers=owner,
    )
    assert post_r.status_code == 400


# --- Community reports, removed, team endpoints ---


@pytest.mark.asyncio
async def test_community_team_endpoint(client, mod_community):
    owner, name = mod_community
    r = await client.get(f"/api/v1/communities/{name}/team")
    assert r.status_code == 200
    team = r.json()
    assert len(team) >= 1
    assert any(m["role"] == "owner" for m in team)


@pytest.mark.asyncio
async def test_community_reports_requires_mod(client, mod_community):
    _, name = mod_community
    member = await setup_user(client, "reportmember")
    r = await client.get(f"/api/v1/communities/{name}/reports", headers=member)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_community_reports_as_mod(client, mod_community):
    owner, name = mod_community
    r = await client.get(f"/api/v1/communities/{name}/reports", headers=owner)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_community_removed_as_mod(client, mod_community):
    owner, name = mod_community
    r = await client.get(f"/api/v1/communities/{name}/removed", headers=owner)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_community_not_found(client):
    r = await client.get("/api/v1/communities/nonexistent/labels")
    assert r.status_code == 404
