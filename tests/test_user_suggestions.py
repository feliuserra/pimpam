from tests.conftest import register, setup_user


async def test_suggestions_requires_auth(client):
    r = await client.get("/api/v1/users/me/suggestions")
    assert r.status_code == 401


async def test_suggestions_empty_when_no_follows(client):
    h = await setup_user(client, "alice")
    r = await client.get("/api/v1/users/me/suggestions", headers=h)
    assert r.status_code == 200
    assert r.json() == []


async def test_suggestions_returns_friends_of_friends(client):
    """alice -> bob -> carol: carol should be suggested to alice."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await register(client, "carol")

    # alice follows bob
    await client.post("/api/v1/users/bob/follow", headers=alice_h)
    # bob follows carol
    await client.post("/api/v1/users/carol/follow", headers=bob_h)

    r = await client.get("/api/v1/users/me/suggestions", headers=alice_h)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["username"] == "carol"
    assert data[0]["is_following"] is False


async def test_suggestions_excludes_already_followed(client):
    """alice -> bob, alice -> carol, bob -> carol: carol should NOT appear."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await register(client, "carol")

    # alice follows bob and carol
    await client.post("/api/v1/users/bob/follow", headers=alice_h)
    await client.post("/api/v1/users/carol/follow", headers=alice_h)
    # bob also follows carol
    await client.post("/api/v1/users/carol/follow", headers=bob_h)

    r = await client.get("/api/v1/users/me/suggestions", headers=alice_h)
    assert r.status_code == 200
    assert r.json() == []


async def test_suggestions_excludes_self(client):
    """alice -> bob, bob -> alice: alice should NOT appear in her own suggestions."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    # mutual follow
    await client.post("/api/v1/users/bob/follow", headers=alice_h)
    await client.post("/api/v1/users/alice/follow", headers=bob_h)

    r = await client.get("/api/v1/users/me/suggestions", headers=alice_h)
    assert r.status_code == 200
    assert all(u["username"] != "alice" for u in r.json())


async def test_suggestions_ordered_by_mutual_count(client):
    """carol is followed by 2 of alice's followees, dave by 1: carol first."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    eve_h = await setup_user(client, "eve")
    await register(client, "carol")
    await register(client, "dave")

    # alice follows bob and eve
    await client.post("/api/v1/users/bob/follow", headers=alice_h)
    await client.post("/api/v1/users/eve/follow", headers=alice_h)

    # bob follows carol and dave
    await client.post("/api/v1/users/carol/follow", headers=bob_h)
    await client.post("/api/v1/users/dave/follow", headers=bob_h)
    # eve follows carol only
    await client.post("/api/v1/users/carol/follow", headers=eve_h)

    r = await client.get("/api/v1/users/me/suggestions", headers=alice_h)
    assert r.status_code == 200
    data = r.json()
    usernames = [u["username"] for u in data]
    assert usernames == ["carol", "dave"]


async def test_suggestions_max_20(client):
    """Even with many friends-of-friends, only 20 are returned."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    # alice follows bob
    await client.post("/api/v1/users/bob/follow", headers=alice_h)

    # bob follows 25 other users
    for i in range(25):
        await register(client, f"user{i}")
        await client.post(f"/api/v1/users/user{i}/follow", headers=bob_h)

    r = await client.get("/api/v1/users/me/suggestions", headers=alice_h)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 20


async def test_suggestions_ignores_pending_follows(client):
    """Pending follows should not produce suggestions."""
    from tests.conftest import get_test_db

    alice_h = await setup_user(client, "alice")
    await register(client, "bob")
    await register(client, "carol")

    # Create a pending follow: alice -> bob (simulating federated pending)
    from app.models.follow import Follow

    async for session in get_test_db():
        from sqlalchemy import select

        from app.models.user import User

        alice = (
            await session.execute(select(User).where(User.username == "alice"))
        ).scalar_one()
        bob = (
            await session.execute(select(User).where(User.username == "bob"))
        ).scalar_one()
        carol = (
            await session.execute(select(User).where(User.username == "carol"))
        ).scalar_one()
        # alice -> bob (pending)
        session.add(Follow(follower_id=alice.id, followed_id=bob.id, is_pending=True))
        # bob -> carol (confirmed)
        session.add(Follow(follower_id=bob.id, followed_id=carol.id, is_pending=False))
        await session.commit()

    r = await client.get("/api/v1/users/me/suggestions", headers=alice_h)
    assert r.status_code == 200
    # alice's follow of bob is pending, so bob's follows shouldn't produce suggestions
    assert r.json() == []
