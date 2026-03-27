from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.follow import Follow
from app.models.friend_group import FriendGroupMember
from app.models.post import Post
from app.models.post_image import PostImage
from app.schemas.comment import ShareCreate
from app.schemas.post import PostCreate, PostPublic, PostUpdate

EDIT_WINDOW = timedelta(hours=1)


async def create_post(db: AsyncSession, data: PostCreate, author_id: int) -> Post:
    effective = (
        data.image_urls
        if data.image_urls
        else ([data.image_url] if data.image_url else [])
    )
    post_data = data.model_dump(exclude={"image_url", "image_urls"})
    post = Post(
        **post_data,
        author_id=author_id,
        karma=1,
        image_url=effective[0] if effective else None,
    )
    db.add(post)
    await db.flush()  # get post.id before creating images and the vote

    for i, url in enumerate(effective):
        db.add(PostImage(post_id=post.id, url=url, display_order=i))

    # Author's implicit +1 — cannot be changed or retracted
    from app.crud.vote import create_initial_vote

    await create_initial_vote(db, user_id=author_id, post_id=post.id)

    await db.commit()
    await db.refresh(post)
    return post


async def get_post(db: AsyncSession, post_id: int) -> Post | None:
    result = await db.execute(select(Post).where(Post.id == post_id))
    return result.scalar_one_or_none()


async def edit_post(db: AsyncSession, post: Post, data: PostUpdate) -> Post:
    """
    Edit a post within the 1-hour edit window.
    Raises ValueError if the window has passed.
    Edit history is intentionally not stored — only the edited flag is public.
    """
    created = (
        post.created_at.replace(tzinfo=timezone.utc)
        if post.created_at.tzinfo is None
        else post.created_at
    )
    if datetime.now(timezone.utc) - created > EDIT_WINDOW:
        raise ValueError("Edit window has closed (1 hour after posting)")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(post, field, value)
    post.is_edited = True
    post.edited_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(post)
    return post


async def get_chronological_feed(
    db: AsyncSession,
    user_id: int,
    limit: int = 20,
    before_id: int | None = None,
) -> list[Post]:
    """
    Returns posts from users the viewer follows AND communities they have joined,
    merged into a single chronological stream, newest first.

    Uses cursor-based pagination (before_id) — never offset-based.
    No ranking, no ML, no algorithmic ordering. Chronological only.
    Removed posts are excluded. A post that matches both conditions (followed
    author AND joined community) appears only once via the OR condition.
    """
    from app.crud.block import get_blocked_user_ids, get_blocker_ids
    from app.models.community import CommunityMember

    followed_ids = select(Follow.followed_id).where(
        Follow.follower_id == user_id,
        Follow.is_pending == False,  # noqa: E712 — exclude pending federated follows
    )

    joined_community_ids = select(CommunityMember.community_id).where(
        CommunityMember.user_id == user_id
    )

    viewer_group_ids = select(FriendGroupMember.group_id).where(
        FriendGroupMember.member_id == user_id
    )

    # Authors whose close-friends group includes the viewer
    from app.models.friend_group import FriendGroup

    close_friend_author_ids = (
        select(FriendGroup.owner_id)
        .join(FriendGroupMember, FriendGroupMember.group_id == FriendGroup.id)
        .where(
            FriendGroup.is_close_friends == True,  # noqa: E712
            FriendGroupMember.member_id == user_id,
        )
    )

    # Exclude blocked users (both directions) from the feed
    blocked_ids = await get_blocked_user_ids(db, user_id)
    blocker_ids = await get_blocker_ids(db, user_id)
    hidden_user_ids = blocked_ids | blocker_ids

    query = (
        select(Post)
        .where(
            or_(
                Post.author_id == user_id,
                Post.author_id.in_(followed_ids),
                Post.community_id.in_(joined_community_ids),
            ),
            Post.is_removed == False,  # noqa: E712
            or_(
                Post.visibility == "public",
                Post.author_id == user_id,
                and_(
                    Post.visibility == "followers",
                    Post.author_id.in_(followed_ids),
                ),
                and_(
                    Post.visibility == "close_friends",
                    Post.author_id.in_(close_friend_author_ids),
                ),
                and_(
                    Post.visibility == "group",
                    Post.friend_group_id.in_(viewer_group_ids),
                ),
            ),
        )
        .order_by(Post.created_at.desc())
        .limit(limit)
    )

    if hidden_user_ids:
        query = query.where(Post.author_id.not_in(hidden_user_ids))
    if before_id is not None:
        subq = select(Post.created_at).where(Post.id == before_id).scalar_subquery()
        query = query.where(Post.created_at < subq)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_community_posts(
    db: AsyncSession,
    community_id: int,
    limit: int = 20,
    before_id: int | None = None,
    include_removed: bool = False,
) -> list[Post]:
    """
    Chronological posts for a community.
    Moderators pass include_removed=True to see hidden posts.
    """
    query = select(Post).where(Post.community_id == community_id)

    if not include_removed:
        query = query.where(Post.is_removed == False)  # noqa: E712

    query = query.order_by(Post.created_at.desc()).limit(limit)

    if before_id is not None:
        subq = select(Post.created_at).where(Post.id == before_id).scalar_subquery()
        query = query.where(Post.created_at < subq)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_user_posts(
    db: AsyncSession,
    user_id: int,
    limit: int = 20,
    before_id: int | None = None,
    viewer_id: int | None = None,
) -> list[Post]:
    """Posts by user_id visible to viewer, newest-first, cursor-paginated.

    - Own profile: show all non-removed posts
    - Follower: public + followers + applicable group/close_friends
    - Non-follower: public only
    """
    from app.models.friend_group import FriendGroup

    base = select(Post).where(
        Post.author_id == user_id,
        Post.is_removed == False,  # noqa: E712
    )

    if viewer_id is not None and viewer_id == user_id:
        # Own profile — see everything
        query = base
    elif viewer_id is not None:
        # Check if viewer follows this user
        follows_author = (
            select(Follow.id)
            .where(
                Follow.follower_id == viewer_id,
                Follow.followed_id == user_id,
                Follow.is_pending == False,  # noqa: E712
            )
            .exists()
        )

        viewer_group_ids = select(FriendGroupMember.group_id).where(
            FriendGroupMember.member_id == viewer_id
        )
        close_friend_author_ids = (
            select(FriendGroup.owner_id)
            .join(FriendGroupMember, FriendGroupMember.group_id == FriendGroup.id)
            .where(
                FriendGroup.is_close_friends == True,  # noqa: E712
                FriendGroupMember.member_id == viewer_id,
                FriendGroup.owner_id == user_id,
            )
        )

        query = base.where(
            or_(
                Post.visibility == "public",
                and_(Post.visibility == "followers", follows_author),
                and_(
                    Post.visibility == "close_friends",
                    Post.author_id.in_(close_friend_author_ids),
                ),
                and_(
                    Post.visibility == "group",
                    Post.friend_group_id.in_(viewer_group_ids),
                ),
            )
        )
    else:
        # Anonymous — public only
        query = base.where(Post.visibility == "public")

    query = query.order_by(Post.created_at.desc()).limit(limit)
    if before_id is not None:
        subq = select(Post.created_at).where(Post.id == before_id).scalar_subquery()
        query = query.where(Post.created_at < subq)
    result = await db.execute(query)
    return list(result.scalars().all())


async def delete_post(db: AsyncSession, post: Post) -> None:
    await db.delete(post)
    await db.commit()


async def create_share(
    db: AsyncSession,
    original: Post,
    author_id: int,
    data: ShareCreate,
) -> Post:
    """
    Create a share (reshare) of an existing post.
    - Traces through share chains: sharing a share links to the root original.
    - Enforces one share per user per original post.
    Raises ValueError('already_shared') if the user has already shared this post.
    """
    # Trace to root original so shares of shares still point to the root
    root_id = (
        original.shared_from_id if original.shared_from_id is not None else original.id
    )

    existing_q = select(Post).where(
        Post.author_id == author_id,
        Post.shared_from_id == root_id,
    )
    # When sharing to a community, check per-community; otherwise check profile-level
    if data.community_id:
        existing_q = existing_q.where(Post.community_id == data.community_id)
    else:
        existing_q = existing_q.where(Post.community_id.is_(None))
    existing = await db.execute(existing_q)
    if existing.scalar_one_or_none() is not None:
        raise ValueError("already_shared")

    root = await get_post(db, root_id) if root_id != original.id else original

    post = Post(
        title=root.title,
        content=root.content,
        url=root.url,
        image_url=root.image_url,
        author_id=author_id,
        community_id=data.community_id,
        karma=1,
        shared_from_id=root_id,
        share_comment=data.comment,
    )
    db.add(post)
    await db.flush()

    from app.crud.vote import create_initial_vote

    await create_initial_vote(db, user_id=author_id, post_id=post.id)

    await db.commit()
    await db.refresh(post)
    return post


async def _enrich_posts(db: AsyncSession, posts: list[Post]) -> dict[int, dict]:
    """Batch-fetch author, community, and comment-count data for a list of posts.

    Returns a dict keyed by post id with the extra fields to merge into PostPublic.
    """
    from sqlalchemy import func as sa_func

    from app.models.comment import Comment
    from app.models.community import Community
    from app.models.user import User

    if not posts:
        return {}

    post_ids = [p.id for p in posts]

    # -- authors (cached per user, 5 min TTL) --
    from app.core.cache import cache_get, cache_set

    author_ids = {p.author_id for p in posts if p.author_id is not None}
    authors: dict[int, tuple[str | None, str | None]] = {}
    uncached_author_ids: set[int] = set()
    for aid in author_ids:
        cached = await cache_get(f"user:{aid}")
        if cached is not None:
            authors[aid] = (cached.get("username"), cached.get("avatar_url"))
        else:
            uncached_author_ids.add(aid)
    if uncached_author_ids:
        rows = await db.execute(
            select(User.id, User.username, User.avatar_url).where(
                User.id.in_(uncached_author_ids)
            )
        )
        for r in rows:
            authors[r.id] = (r.username, r.avatar_url)
            await cache_set(
                f"user:{r.id}",
                {"username": r.username, "avatar_url": r.avatar_url},
                ttl=300,
            )

    # -- communities (cached per community, 10 min TTL) --
    community_ids = {p.community_id for p in posts if p.community_id is not None}
    communities: dict[int, str] = {}
    uncached_comm_ids: set[int] = set()
    for cid in community_ids:
        cached = await cache_get(f"community:{cid}")
        if cached is not None:
            communities[cid] = cached.get("name", "")
        else:
            uncached_comm_ids.add(cid)
    if uncached_comm_ids:
        rows = await db.execute(
            select(Community.id, Community.name).where(
                Community.id.in_(uncached_comm_ids)
            )
        )
        for r in rows:
            communities[r.id] = r.name
            await cache_set(f"community:{r.id}", {"name": r.name}, ttl=600)

    # -- comment counts --
    count_rows = await db.execute(
        select(Comment.post_id, sa_func.count())
        .where(Comment.post_id.in_(post_ids), Comment.is_removed == False)  # noqa: E712
        .group_by(Comment.post_id)
    )
    comment_counts: dict[int, int] = dict(count_rows.all())

    # -- hashtags --
    from app.models.hashtag import Hashtag, PostHashtag

    hashtag_rows = await db.execute(
        select(PostHashtag.post_id, Hashtag.name)
        .join(Hashtag, PostHashtag.hashtag_id == Hashtag.id)
        .where(PostHashtag.post_id.in_(post_ids))
    )
    post_hashtags: dict[int, list[str]] = {pid: [] for pid in post_ids}
    for pid, name in hashtag_rows.all():
        post_hashtags[pid].append(name)

    # -- labels --
    from app.models.community_label import CommunityLabel
    from app.schemas.community_label import LabelPublic

    label_ids = {p.label_id for p in posts if p.label_id is not None}
    labels: dict[int, LabelPublic] = {}
    if label_ids:
        rows = await db.execute(
            select(CommunityLabel).where(CommunityLabel.id.in_(label_ids))
        )
        for lbl in rows.scalars().all():
            labels[lbl.id] = LabelPublic.model_validate(lbl, from_attributes=True)

    extras: dict[int, dict] = {}
    for p in posts:
        author_data = (
            authors.get(p.author_id, (None, None)) if p.author_id else (None, None)
        )
        extras[p.id] = {
            "author_username": author_data[0],
            "author_avatar_url": author_data[1],
            "community_name": communities.get(p.community_id)
            if p.community_id
            else None,
            "comment_count": comment_counts.get(p.id, 0),
            "hashtags": post_hashtags.get(p.id, []),
            "label_id": p.label_id,
            "label": labels.get(p.label_id) if p.label_id else None,
        }
    return extras


async def annotate_posts_with_user_vote(
    db: AsyncSession, posts: list[Post], user_id: int | None
) -> list[PostPublic]:
    """Convert Post ORM objects to PostPublic with the viewer's vote attached.

    If user_id is None (unauthenticated), user_vote is None for all posts.
    """
    from app.crud.vote import get_user_votes_for_posts

    post_ids = [p.id for p in posts]
    votes = await get_user_votes_for_posts(db, user_id, post_ids) if user_id else {}
    extras = await _enrich_posts(db, posts)
    return [
        PostPublic.model_validate(p, from_attributes=True).model_copy(
            update={"user_vote": votes.get(p.id), **extras.get(p.id, {})}
        )
        for p in posts
    ]


async def annotate_post_with_user_vote(
    db: AsyncSession, post: Post, user_id: int | None
) -> PostPublic:
    """Convert a single Post ORM object to PostPublic with the viewer's vote."""
    from app.crud.vote import get_vote

    vote = await get_vote(db, user_id, post.id) if user_id else None
    extras = await _enrich_posts(db, [post])
    return PostPublic.model_validate(post, from_attributes=True).model_copy(
        update={
            "user_vote": vote.direction if vote else None,
            **extras.get(post.id, {}),
        }
    )
