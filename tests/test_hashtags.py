"""Tests for hashtag extraction, CRUD, and API endpoints."""


from app.crud.hashtag import extract_hashtags

from tests.conftest import setup_user

# --- Unit tests for hashtag extraction ---


def test_extract_basic():
    assert extract_hashtags("Hello #world") == ["world"]


def test_extract_multiple():
    tags = extract_hashtags("#python is great #coding #dev")
    assert tags == ["python", "coding", "dev"]


def test_extract_normalized_lowercase():
    assert extract_hashtags("#Python #PYTHON #python") == ["python"]


def test_extract_underscores():
    assert extract_hashtags("#open_source") == ["open_source"]


def test_extract_from_empty_string():
    assert extract_hashtags("") == []


def test_extract_no_hashtags():
    assert extract_hashtags("Just a normal sentence") == []


def test_extract_ignores_bare_hash():
    assert extract_hashtags("# not a tag") == []


def test_extract_with_numbers():
    assert extract_hashtags("Check out #web3 and #2024trends") == ["web3", "2024trends"]


def test_extract_max_length():
    long_tag = "a" * 100
    assert extract_hashtags(f"#{long_tag}") == [long_tag]
    # 101 chars — regex only captures first 100
    too_long = "a" * 101
    result = extract_hashtags(f"#{too_long}")
    assert len(result) == 1
    assert len(result[0]) <= 100


# --- Integration tests for post + hashtag sync ---


async def test_post_creation_extracts_hashtags(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/posts",
        headers=h,
        json={"title": "My #first post", "content": "About #python and #coding"},
    )
    assert r.status_code == 201
    body = r.json()
    assert set(body["hashtags"]) == {"first", "python", "coding"}


async def test_post_without_hashtags(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/posts",
        headers=h,
        json={"title": "No tags", "content": "Just plain text"},
    )
    assert r.status_code == 201
    assert r.json()["hashtags"] == []


async def test_edit_post_updates_hashtags(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/posts",
        headers=h,
        json={"title": "#oldtag post", "content": "content"},
    )
    post_id = r.json()["id"]

    # Edit to change hashtags
    r = await client.patch(
        f"/api/v1/posts/{post_id}",
        headers=h,
        json={"title": "#newtag post"},
    )
    assert r.status_code == 200
    assert "newtag" in r.json()["hashtags"]


async def test_get_post_includes_hashtags(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/posts",
        headers=h,
        json={"title": "Hello", "content": "#test #demo"},
    )
    post_id = r.json()["id"]

    r = await client.get(f"/api/v1/posts/{post_id}")
    assert r.status_code == 200
    assert set(r.json()["hashtags"]) == {"test", "demo"}


# --- Hashtag API endpoint tests ---


async def test_trending_empty(client):
    r = await client.get("/api/v1/hashtags/trending")
    assert r.status_code == 200
    assert r.json() == []


async def test_trending_with_posts(client):
    h = await setup_user(client, "alice")
    # Create posts with hashtags
    await client.post(
        "/api/v1/posts",
        headers=h,
        json={"title": "#python rocks", "content": "#python is great"},
    )
    await client.post(
        "/api/v1/posts",
        headers=h,
        json={"title": "#python again", "content": "more #coding"},
    )

    r = await client.get("/api/v1/hashtags/trending")
    assert r.status_code == 200
    tags = r.json()
    names = [t["name"] for t in tags]
    assert "python" in names
    # python should be first (2 posts) over coding (1 post)
    python_tag = next(t for t in tags if t["name"] == "python")
    assert python_tag["post_count"] == 2


async def test_get_hashtag(client):
    h = await setup_user(client, "alice")
    await client.post(
        "/api/v1/posts",
        headers=h,
        json={"title": "#music post", "content": "about music"},
    )

    r = await client.get("/api/v1/hashtags/music")
    assert r.status_code == 200
    assert r.json()["name"] == "music"
    assert r.json()["post_count"] == 1


async def test_get_hashtag_not_found(client):
    r = await client.get("/api/v1/hashtags/nonexistent")
    assert r.status_code == 404


async def test_posts_by_hashtag(client):
    h = await setup_user(client, "alice")
    r1 = await client.post(
        "/api/v1/posts",
        headers=h,
        json={"title": "#tech post 1", "content": "first"},
    )
    r2 = await client.post(
        "/api/v1/posts",
        headers=h,
        json={"title": "#tech post 2", "content": "second"},
    )
    await client.post(
        "/api/v1/posts",
        headers=h,
        json={"title": "No hashtag", "content": "unrelated"},
    )

    r = await client.get("/api/v1/hashtags/tech/posts")
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) == 2
    post_ids = {p["id"] for p in posts}
    assert r1.json()["id"] in post_ids
    assert r2.json()["id"] in post_ids


async def test_posts_by_hashtag_not_found(client):
    r = await client.get("/api/v1/hashtags/nonexistent/posts")
    assert r.status_code == 404


# --- Search integration tests ---


async def test_search_hashtags(client):
    h = await setup_user(client, "alice")
    await client.post(
        "/api/v1/posts",
        headers=h,
        json={"title": "#design tips", "content": "about design"},
    )

    r = await client.get("/api/v1/search", params={"q": "des", "type": "hashtag"})
    assert r.status_code == 200
    hits = r.json()["hits"]
    assert len(hits) >= 1
    assert hits[0]["type"] == "hashtag"
    assert hits[0]["name"] == "design"


async def test_search_hashtags_no_results(client):
    r = await client.get("/api/v1/search", params={"q": "zzz", "type": "hashtag"})
    assert r.status_code == 200
    assert r.json()["hits"] == []
