"""
Unit tests for app/federation/activity_handler.py.

Handlers are called directly (not through the HTTP inbox route) using
a real in-memory SQLite DB via the client fixture.  External HTTP calls
(fetch_remote_actor, deliver_activity) are mocked throughout.
"""
import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from tests.conftest import get_test_db, setup_user
from app.federation.activity_handler import dispatch, _get_or_create_remote_user
from app.models.follow import Follow
from app.models.post import Post
from app.models.user import User

# ---------------------------------------------------------------------------
# Shared constants / helpers
# ---------------------------------------------------------------------------

REMOTE_ACTOR_DOC = {
    "id": "https://remote.example/users/eve",
    "type": "Actor",
    "preferredUsername": "eve",
    "name": "Eve",
    "inbox": "https://remote.example/users/eve/inbox",
    "publicKey": {"publicKeyPem": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkq...\n-----END PUBLIC KEY-----\n"},
}

# fetch_remote_actor is lazily imported inside each handler function,
# so we must patch it at the source module, not on activity_handler.
PATCH_FETCH = "app.federation.fetcher.fetch_remote_actor"
PATCH_DELIVER = "app.federation.activity_handler.deliver_activity"


async def _make_local_user_with_ap_id(username: str) -> dict:
    """Return ap_id for the freshly-created local user (set via DB)."""
    async for session in get_test_db():
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user:
            ap_id = f"https://pimpam.example/users/{username}"
            user.ap_id = ap_id
            await session.commit()
            return {"id": user.id, "ap_id": ap_id}
    raise RuntimeError(f"user {username!r} not found")


# ---------------------------------------------------------------------------
# dispatch() — routing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dispatch_unknown_type_is_silent(client):
    """dispatch() must not raise on unknown activity types."""
    async for session in get_test_db():
        await dispatch({"type": "Banana", "actor": "https://x/u/1", "object": {}}, session)
        # If we got here without exception, the test passes


@pytest.mark.asyncio
async def test_dispatch_missing_type_is_silent(client):
    async for session in get_test_db():
        await dispatch({}, session)


# ---------------------------------------------------------------------------
# _handle_follow — remote actor follows local user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_follow_creates_follow_row(client):
    await setup_user(client, "alice")
    alice = await _make_local_user_with_ap_id("alice")

    activity = {
        "type": "Follow",
        "actor": REMOTE_ACTOR_DOC["id"],
        "object": alice["ap_id"],
    }

    with patch(PATCH_FETCH, new=AsyncMock(return_value=REMOTE_ACTOR_DOC)), \
         patch(PATCH_DELIVER, new=AsyncMock()):
        async for session in get_test_db():
            await dispatch(activity, session)

    async for session in get_test_db():
        # A remote user row should have been created
        remote = (await session.execute(
            select(User).where(User.ap_id == REMOTE_ACTOR_DOC["id"])
        )).scalar_one_or_none()
        assert remote is not None
        assert remote.is_remote is True

        # Follow row should exist
        follow = (await session.execute(
            select(Follow).where(
                Follow.follower_id == remote.id,
                Follow.followed_id == alice["id"],
            )
        )).scalar_one_or_none()
        assert follow is not None


@pytest.mark.asyncio
async def test_handle_follow_idempotent(client):
    """Sending the same Follow twice does not create duplicate Follow rows."""
    await setup_user(client, "alice")
    alice = await _make_local_user_with_ap_id("alice")

    activity = {
        "type": "Follow",
        "actor": REMOTE_ACTOR_DOC["id"],
        "object": alice["ap_id"],
    }

    with patch(PATCH_FETCH, new=AsyncMock(return_value=REMOTE_ACTOR_DOC)), \
         patch(PATCH_DELIVER, new=AsyncMock()):
        async for session in get_test_db():
            await dispatch(activity, session)
        async for session in get_test_db():
            await dispatch(activity, session)

    async for session in get_test_db():
        remote = (await session.execute(
            select(User).where(User.ap_id == REMOTE_ACTOR_DOC["id"])
        )).scalar_one_or_none()
        follows = (await session.execute(
            select(Follow).where(Follow.followed_id == alice["id"])
        )).scalars().all()
        assert len(follows) == 1


@pytest.mark.asyncio
async def test_handle_follow_unknown_local_user_ignored(client):
    """Follow addressed to an unknown ap_id is silently ignored."""
    activity = {
        "type": "Follow",
        "actor": REMOTE_ACTOR_DOC["id"],
        "object": "https://pimpam.example/users/nobody",
    }
    with patch(PATCH_FETCH, new=AsyncMock(return_value=REMOTE_ACTOR_DOC)), \
         patch(PATCH_DELIVER, new=AsyncMock()):
        async for session in get_test_db():
            await dispatch(activity, session)  # should not raise


@pytest.mark.asyncio
async def test_handle_follow_fetch_failure_ignored(client):
    """If fetching the remote actor fails, the Follow is silently dropped."""
    from app.federation.fetcher import FederationFetchError
    await setup_user(client, "alice")
    alice = await _make_local_user_with_ap_id("alice")

    activity = {
        "type": "Follow",
        "actor": "https://broken.example/users/eve",
        "object": alice["ap_id"],
    }
    with patch(PATCH_FETCH, new=AsyncMock(side_effect=FederationFetchError("timeout"))):
        async for session in get_test_db():
            await dispatch(activity, session)  # should not raise


# ---------------------------------------------------------------------------
# _handle_undo — remote actor unfollows local user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_undo_removes_follow(client):
    await setup_user(client, "alice")
    alice = await _make_local_user_with_ap_id("alice")

    # First establish a follow via _handle_follow
    follow_activity = {
        "type": "Follow",
        "actor": REMOTE_ACTOR_DOC["id"],
        "object": alice["ap_id"],
    }
    with patch(PATCH_FETCH, new=AsyncMock(return_value=REMOTE_ACTOR_DOC)), \
         patch(PATCH_DELIVER, new=AsyncMock()):
        async for session in get_test_db():
            await dispatch(follow_activity, session)

    undo_activity = {
        "type": "Undo",
        "actor": REMOTE_ACTOR_DOC["id"],
        "object": {
            "type": "Follow",
            "actor": REMOTE_ACTOR_DOC["id"],
            "object": alice["ap_id"],
        },
    }
    async for session in get_test_db():
        await dispatch(undo_activity, session)

    async for session in get_test_db():
        remote = (await session.execute(
            select(User).where(User.ap_id == REMOTE_ACTOR_DOC["id"])
        )).scalar_one_or_none()
        if remote:
            follow = (await session.execute(
                select(Follow).where(
                    Follow.follower_id == remote.id,
                    Follow.followed_id == alice["id"],
                )
            )).scalar_one_or_none()
            assert follow is None


@pytest.mark.asyncio
async def test_handle_undo_non_follow_object_ignored(client):
    """Undo with an object that is not a Follow is silently ignored."""
    activity = {
        "type": "Undo",
        "actor": "https://remote.example/users/eve",
        "object": {"type": "Like", "object": "https://pimpam.example/posts/1"},
    }
    async for session in get_test_db():
        await dispatch(activity, session)  # should not raise


# ---------------------------------------------------------------------------
# _handle_create — cache federated Note as local Post
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_create_note_cached(client):
    """A Create{Note} from a remote actor creates a Post row."""
    ap_post_id = "https://remote.example/notes/42"
    activity = {
        "type": "Create",
        "actor": REMOTE_ACTOR_DOC["id"],
        "object": {
            "type": "Note",
            "id": ap_post_id,
            "content": "Hello from the fediverse!",
        },
    }
    with patch(PATCH_FETCH, new=AsyncMock(return_value=REMOTE_ACTOR_DOC)), \
         patch(PATCH_DELIVER, new=AsyncMock()):
        async for session in get_test_db():
            await dispatch(activity, session)

    async for session in get_test_db():
        post = (await session.execute(
            select(Post).where(Post.ap_id == ap_post_id)
        )).scalar_one_or_none()
        assert post is not None
        assert post.content == "Hello from the fediverse!"


@pytest.mark.asyncio
async def test_handle_create_idempotent(client):
    """Creating the same Note twice does not create duplicate Posts."""
    ap_post_id = "https://remote.example/notes/99"
    activity = {
        "type": "Create",
        "actor": REMOTE_ACTOR_DOC["id"],
        "object": {"type": "Note", "id": ap_post_id, "content": "Once"},
    }
    with patch(PATCH_FETCH, new=AsyncMock(return_value=REMOTE_ACTOR_DOC)), \
         patch(PATCH_DELIVER, new=AsyncMock()):
        async for session in get_test_db():
            await dispatch(activity, session)
        async for session in get_test_db():
            await dispatch(activity, session)

    async for session in get_test_db():
        posts = (await session.execute(
            select(Post).where(Post.ap_id == ap_post_id)
        )).scalars().all()
        assert len(posts) == 1


@pytest.mark.asyncio
async def test_handle_create_non_note_ignored(client):
    """Create activities with an object type other than Note are ignored."""
    activity = {
        "type": "Create",
        "actor": REMOTE_ACTOR_DOC["id"],
        "object": {"type": "Article", "id": "https://remote.example/articles/1"},
    }
    with patch(PATCH_FETCH, new=AsyncMock(return_value=REMOTE_ACTOR_DOC)):
        async for session in get_test_db():
            await dispatch(activity, session)

    async for session in get_test_db():
        posts = (await session.execute(select(Post))).scalars().all()
        assert len(posts) == 0


@pytest.mark.asyncio
async def test_handle_create_missing_id_ignored(client):
    """Create{Note} with no id field is silently dropped."""
    activity = {
        "type": "Create",
        "actor": REMOTE_ACTOR_DOC["id"],
        "object": {"type": "Note", "content": "No ID"},
    }
    async for session in get_test_db():
        await dispatch(activity, session)


# ---------------------------------------------------------------------------
# _handle_delete — remove a cached federated post
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_delete_removes_cached_post(client):
    ap_post_id = "https://remote.example/notes/delete-me"
    # First cache the post via Create
    create_activity = {
        "type": "Create",
        "actor": REMOTE_ACTOR_DOC["id"],
        "object": {"type": "Note", "id": ap_post_id, "content": "Bye"},
    }
    with patch(PATCH_FETCH, new=AsyncMock(return_value=REMOTE_ACTOR_DOC)), \
         patch(PATCH_DELIVER, new=AsyncMock()):
        async for session in get_test_db():
            await dispatch(create_activity, session)

    delete_activity = {"type": "Delete", "object": ap_post_id}
    async for session in get_test_db():
        await dispatch(delete_activity, session)

    async for session in get_test_db():
        post = (await session.execute(
            select(Post).where(Post.ap_id == ap_post_id)
        )).scalar_one_or_none()
        assert post is None


@pytest.mark.asyncio
async def test_handle_delete_with_object_dict(client):
    """Delete where object is a dict with an id field."""
    ap_post_id = "https://remote.example/notes/dict-delete"
    create_activity = {
        "type": "Create",
        "actor": REMOTE_ACTOR_DOC["id"],
        "object": {"type": "Note", "id": ap_post_id, "content": "Gone soon"},
    }
    with patch(PATCH_FETCH, new=AsyncMock(return_value=REMOTE_ACTOR_DOC)), \
         patch(PATCH_DELIVER, new=AsyncMock()):
        async for session in get_test_db():
            await dispatch(create_activity, session)

    delete_activity = {"type": "Delete", "object": {"id": ap_post_id, "type": "Tombstone"}}
    async for session in get_test_db():
        await dispatch(delete_activity, session)

    async for session in get_test_db():
        post = (await session.execute(
            select(Post).where(Post.ap_id == ap_post_id)
        )).scalar_one_or_none()
        assert post is None


@pytest.mark.asyncio
async def test_handle_delete_unknown_post_ignored(client):
    """Deleting a post we never cached is silently ignored."""
    activity = {"type": "Delete", "object": "https://remote.example/notes/unknown"}
    async for session in get_test_db():
        await dispatch(activity, session)


# ---------------------------------------------------------------------------
# _handle_accept — remote server accepts our outgoing Follow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_accept_clears_pending_follow(client):
    """Accept{Follow} clears the is_pending flag so the follow becomes active."""
    await setup_user(client, "alice")
    alice = await _make_local_user_with_ap_id("alice")

    remote_ap_id = "https://remote.example/users/eve"

    # Insert remote user stub
    async for session in get_test_db():
        remote = User(
            username="eve@remote.example",
            email="eve@remote.invalid",
            hashed_password="",
            ap_id=remote_ap_id,
            ap_inbox="https://remote.example/users/eve/inbox",
            is_remote=True,
            is_active=True,
        )
        session.add(remote)
        await session.commit()
        await session.refresh(remote)
        remote_id = remote.id

        # Create a pending follow: alice → eve
        session.add(Follow(follower_id=alice["id"], followed_id=remote_id, is_pending=True))
        await session.commit()

    accept_activity = {
        "type": "Accept",
        "actor": remote_ap_id,
        "object": {
            "type": "Follow",
            "actor": alice["ap_id"],
            "object": remote_ap_id,
        },
    }
    async for session in get_test_db():
        await dispatch(accept_activity, session)

    async for session in get_test_db():
        result = await session.execute(
            select(Follow).where(Follow.follower_id == alice["id"])
        )
        follow = result.scalar_one_or_none()
        assert follow is not None
        assert follow.is_pending is False


@pytest.mark.asyncio
async def test_handle_accept_string_object_ignored(client):
    """Accept where object is a plain string ID (not a dict) is silently ignored."""
    activity = {
        "type": "Accept",
        "actor": "https://remote.example/users/eve",
        "object": "https://pimpam.example/activities/follow/1",
    }
    async for session in get_test_db():
        await dispatch(activity, session)  # should not raise


@pytest.mark.asyncio
async def test_handle_accept_non_follow_object_ignored(client):
    """Accept where object.type is not Follow is silently ignored."""
    activity = {
        "type": "Accept",
        "actor": "https://remote.example/users/eve",
        "object": {"type": "Like", "actor": "https://a/u/1", "object": "https://a/p/1"},
    }
    async for session in get_test_db():
        await dispatch(activity, session)


# ---------------------------------------------------------------------------
# _get_or_create_remote_user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_or_create_remote_user_creates_stub(client):
    ap_id = "https://remote.example/users/newactor"
    actor_doc = {
        **REMOTE_ACTOR_DOC,
        "id": ap_id,
        "preferredUsername": "newactor",
        "inbox": "https://remote.example/users/newactor/inbox",
    }
    with patch(PATCH_FETCH, new=AsyncMock(return_value=actor_doc)):
        async for session in get_test_db():
            user = await _get_or_create_remote_user(ap_id, session)
            assert user is not None
            assert user.is_remote is True
            assert user.ap_id == ap_id
            assert "newactor" in user.username


@pytest.mark.asyncio
async def test_get_or_create_remote_user_returns_existing(client):
    """Calling twice returns the same user without creating a duplicate."""
    ap_id = "https://remote.example/users/existing"
    actor_doc = {
        **REMOTE_ACTOR_DOC,
        "id": ap_id,
        "preferredUsername": "existing",
    }
    with patch(PATCH_FETCH, new=AsyncMock(return_value=actor_doc)):
        async for session in get_test_db():
            u1 = await _get_or_create_remote_user(ap_id, session)
        async for session in get_test_db():
            u2 = await _get_or_create_remote_user(ap_id, session)
        assert u1.id == u2.id
