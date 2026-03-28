import logging

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.config import settings
from app.core.dependencies import CurrentUser, DBSession, OptionalUser
from app.core.limiter import limiter
from app.core.redis import publish_to_user
from app.core.search import deindex_post, index_post
from app.crud.friend_group import get_group, is_member
from app.crud.post import (
    annotate_post_with_user_vote,
    create_post,
    create_share,
    delete_post,
    edit_post,
    get_post,
)
from app.crud.user import (
    get_local_follower_ids,
    get_remote_follower_inboxes,
    get_user_by_id,
)
from app.crud.vote import cast_vote, retract_vote
from app.federation.actor import (
    build_announce,
    build_create,
    build_like,
    build_undo_like,
)
from app.federation.delivery import deliver_activity
from app.schemas.comment import ShareCreate
from app.schemas.post import LinkPreview, PostCreate, PostPublic, PostUpdate
from app.schemas.vote import VoteCreate, VotePublic

logger = logging.getLogger("pimpam.posts")

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("", response_model=PostPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create(
    request: Request, data: PostCreate, current_user: CurrentUser, db: DBSession
):
    """Create a new post, optionally within a community."""
    effective = (
        data.image_urls
        if data.image_urls
        else ([data.image_url] if data.image_url else [])
    )
    if len(effective) > 1 and not settings.multi_image_posts_enabled:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Multiple images per post is not enabled",
        )
    if effective and len(effective) > settings.post_max_images:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.post_max_images} images per post",
        )

    if data.visibility == "group":
        group = await get_group(db, data.friend_group_id)
        if group is None or group.owner_id != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your group")

    # Validate label belongs to target community
    if data.label_id is not None:
        if data.community_id is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Labels can only be set on community posts",
            )
        from app.crud.community_label import get_label

        label = await get_label(db, data.label_id)
        if label is None or label.community_id != data.community_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Label does not belong to this community",
            )

    post = await create_post(db, data, author_id=current_user.id)

    # Sync hashtags from title + content
    from app.crud.hashtag import sync_post_hashtags

    await sync_post_hashtags(db, post.id, post.content or "", post.title)
    await db.commit()

    if post.visibility == "public":
        await index_post(post)

        # Notify local followers in real time
        follower_ids = await get_local_follower_ids(db, current_user.id)
        for fid in follower_ids:
            await publish_to_user(
                fid,
                "new_post",
                {
                    "id": post.id,
                    "title": post.title,
                    "author": current_user.username,
                },
            )

        if settings.federation_enabled:
            try:
                inboxes = await get_remote_follower_inboxes(db, current_user.id)
                if inboxes:
                    activity = build_create(post, current_user)
                    await deliver_activity(activity, current_user, inboxes)
            except Exception:
                logger.exception(
                    "Failed to deliver federation activity for post %s", post.id
                )

    elif post.visibility == "followers":
        # Notify followers via WS (no search index, no federation)
        follower_ids = await get_local_follower_ids(db, current_user.id)
        for fid in follower_ids:
            await publish_to_user(
                fid,
                "new_post",
                {
                    "id": post.id,
                    "title": post.title,
                    "author": current_user.username,
                },
            )

    elif post.visibility == "close_friends":
        # Notify only close friends via WS
        from app.crud.friend_group import get_close_friends_member_ids

        cf_ids = await get_close_friends_member_ids(db, current_user.id)
        for fid in cf_ids:
            await publish_to_user(
                fid,
                "new_post",
                {
                    "id": post.id,
                    "title": post.title,
                    "author": current_user.username,
                },
            )

    return await annotate_post_with_user_vote(db, post, current_user.id)


@router.get("/link-preview", response_model=LinkPreview)
@limiter.limit("30/minute")
async def link_preview(
    request: Request,
    current_user: CurrentUser,
    url: str = Query(..., description="URL to fetch OpenGraph metadata from"),
) -> LinkPreview:
    """Fetch OpenGraph metadata from a URL and return a link preview."""
    from app.core.og_parser import fetch_og_metadata

    meta = await fetch_og_metadata(url)
    return LinkPreview(
        url=url,
        title=meta.get("title"),
        description=meta.get("description"),
        image=meta.get("image"),
        site_name=meta.get("site_name"),
    )


@router.get("/{post_id}", response_model=PostPublic)
async def get(post_id: int, db: DBSession, current_user: OptionalUser = None):
    """Fetch a single post by ID. Removed posts are hidden unless you are a moderator."""
    post = await get_post(db, post_id)
    if post is None or post.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    viewer_id = current_user.id if current_user else None
    if post.visibility != "public" and post.author_id != viewer_id:
        if post.visibility == "group":
            if viewer_id is None or not await is_member(
                db, post.friend_group_id, viewer_id
            ):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Not authorised to view this post",
                )
        elif post.visibility == "followers":
            if viewer_id is None:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Not authorised to view this post",
                )
            from app.crud.user import check_is_following

            if not await check_is_following(db, viewer_id, post.author_id):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Not authorised to view this post",
                )
        elif post.visibility == "close_friends":
            if viewer_id is None:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Not authorised to view this post",
                )
            from app.crud.friend_group import get_close_friends_member_ids

            cf_ids = await get_close_friends_member_ids(db, post.author_id)
            if viewer_id not in cf_ids:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Not authorised to view this post",
                )
    return await annotate_post_with_user_vote(db, post, viewer_id)


@router.patch("/{post_id}", response_model=PostPublic)
@limiter.limit("20/minute")
async def edit(
    request: Request,
    post_id: int,
    data: PostUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Edit a post. Only the author may edit, and only within 1 hour of posting.
    The edit is flagged publicly (is_edited=True) but the edit history is not stored.
    After the 1-hour window, the post can only be deleted.
    """
    post = await get_post(db, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your post")

    # Validate label_id if being changed
    if data.label_id is not None:
        if post.community_id is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Labels can only be set on community posts",
            )
        from app.crud.community_label import get_label

        label = await get_label(db, data.label_id)
        if label is None or label.community_id != post.community_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Label does not belong to this community",
            )

    try:
        post = await edit_post(db, post, data)
    except ValueError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e))

    # Re-sync hashtags after edit
    from app.crud.hashtag import sync_post_hashtags

    await sync_post_hashtags(db, post.id, post.content or "", post.title)
    await db.commit()

    await index_post(post)
    return await annotate_post_with_user_vote(db, post, current_user.id)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(post_id: int, current_user: CurrentUser, db: DBSession):
    """Delete a post. Only the author may delete their own post."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.models.pending_deletion import PendingDeletion
    from app.models.post_image import PostImage

    post = await get_post(db, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your post")

    # Schedule image deletion (1-hour grace period)
    now = datetime.now(timezone.utc)
    keys_to_delete: list[str] = []
    if post.image_url and not post.image_url.startswith("http"):
        keys_to_delete.append(post.image_url)

    # Collect PostImage keys
    img_rows = await db.execute(
        select(PostImage.url).where(PostImage.post_id == post.id)
    )
    for (url,) in img_rows:
        if url and not url.startswith("http"):
            keys_to_delete.append(url)

    if keys_to_delete:
        from fastapi.concurrency import run_in_threadpool

        from app.core.storage import get_object_size

        for key in keys_to_delete:
            size = await run_in_threadpool(get_object_size, key)
            db.add(
                PendingDeletion(
                    s3_key=key,
                    scheduled_at=now,
                    delete_after=now + timedelta(hours=1),
                    user_id=current_user.id,
                    bytes_to_reclaim=size,
                )
            )
        await db.flush()

    await deindex_post(post_id)
    await delete_post(db, post)


@router.post("/{post_id}/vote", response_model=VotePublic)
@limiter.limit("30/minute")
async def vote(
    request: Request,
    post_id: int,
    data: VoteCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Cast or change a vote on a post (+1 or -1).
    You cannot vote on your own post — authors receive an automatic +1 at post creation.
    Changing an existing vote updates it and adjusts karma accordingly.
    """
    post = await get_post(db, post_id)
    if post is None or post.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id == current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Cannot vote on your own post"
        )

    vote_obj = await cast_vote(db, current_user.id, post, data.direction)

    # Grouped vote notification for post author
    try:
        from app.crud.notification import notify as _notify

        await _notify(
            db,
            post.author_id,
            "vote",
            actor_id=current_user.id,
            post_id=post_id,
            group_key=f"vote:post:{post_id}",
        )
    except Exception:
        logger.exception("Failed to send vote notification for post %s", post_id)

    author = await get_user_by_id(db, post.author_id)
    await publish_to_user(
        post.author_id,
        "karma_update",
        {
            "post_id": post_id,
            "post_karma": post.karma,
            "user_karma": author.karma if author else None,
        },
    )

    # Send AP Like for +1 votes on federated posts
    if settings.federation_enabled and data.direction == 1 and post.ap_id:
        try:
            author = await get_user_by_id(db, post.author_id)
            if author and author.ap_inbox:
                activity = build_like(current_user.username, post.ap_id)
                await deliver_activity(activity, current_user, [author.ap_inbox])
        except Exception:
            logger.exception("Failed to deliver AP Like for post %s", post_id)

    return vote_obj


@router.delete("/{post_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def retract(
    request: Request, post_id: int, current_user: CurrentUser, db: DBSession
):
    """
    Retract your vote on a post.
    You cannot retract the author's automatic initial vote.
    """
    post = await get_post(db, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id == current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Cannot retract your author vote"
        )

    try:
        await retract_vote(db, current_user.id, post)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No vote to retract")

    author = await get_user_by_id(db, post.author_id)
    await publish_to_user(
        post.author_id,
        "karma_update",
        {
            "post_id": post_id,
            "post_karma": post.karma,
            "user_karma": author.karma if author else None,
        },
    )

    # Send AP Undo{Like} for federated posts
    if settings.federation_enabled and post.ap_id:
        try:
            author = await get_user_by_id(db, post.author_id)
            if author and author.ap_inbox:
                activity = build_undo_like(current_user.username, post.ap_id)
                await deliver_activity(activity, current_user, [author.ap_inbox])
        except Exception:
            logger.exception("Failed to deliver AP Undo{Like} for post %s", post_id)


@router.post("/{post_id}/boost", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def boost(
    request: Request, post_id: int, current_user: CurrentUser, db: DBSession
):
    """
    Boost (Announce) a federated post to your followers.
    Only works for posts that originated from a remote server (have an ap_id).
    When federation is disabled, returns 503.
    """
    if not settings.federation_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="Federation is disabled"
        )

    post = await get_post(db, post_id)
    if post is None or post.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if not post.ap_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Cannot boost a local post over federation",
        )

    try:
        inboxes = await get_remote_follower_inboxes(db, current_user.id)
        if inboxes:
            activity = build_announce(current_user.username, post.ap_id)
            await deliver_activity(activity, current_user, inboxes)
    except Exception:
        logger.exception("Failed to deliver AP Announce for post %s", post_id)


@router.post(
    "/{post_id}/share", response_model=PostPublic, status_code=status.HTTP_201_CREATED
)
@limiter.limit("20/minute")
async def share(
    request: Request,
    post_id: int,
    data: ShareCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Reshare a post to your followers (and optionally into a community).
    The share appears as a new post authored by you, preserving a reference to the original.
    You can only share a given post once. Sharing a share is not allowed — the original is linked instead.
    """
    original = await get_post(db, post_id)
    if original is None or original.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if original.visibility != "public":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Only public posts can be shared",
        )
    # Allow sharing your own post only when cross-posting to a community
    if original.author_id == current_user.id and not data.community_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot share your own post"
        )

    try:
        post = await create_share(db, original, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e))

    # Notify the original post author
    try:
        from app.crud.notification import notify as _notify

        await _notify(
            db,
            original.author_id,
            "share",
            actor_id=current_user.id,
            post_id=original.id,
        )
    except Exception:
        logger.exception("Failed to send share notification for post %s", original.id)

    # Notify local followers
    follower_ids = await get_local_follower_ids(db, current_user.id)
    for fid in follower_ids:
        await publish_to_user(
            fid,
            "new_post",
            {
                "id": post.id,
                "title": post.title,
                "author": current_user.username,
                "shared_from_id": post.shared_from_id,
            },
        )

    return await annotate_post_with_user_vote(db, post, current_user.id)
