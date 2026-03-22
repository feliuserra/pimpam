from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DBSession
from app.crud.post import create_post, delete_post, edit_post, get_post
from app.crud.vote import cast_vote, retract_vote
from app.schemas.post import PostCreate, PostPublic, PostUpdate
from app.schemas.vote import VoteCreate, VotePublic

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("", response_model=PostPublic, status_code=status.HTTP_201_CREATED)
async def create(data: PostCreate, current_user: CurrentUser, db: DBSession):
    """Create a new post, optionally within a community."""
    return await create_post(db, data, author_id=current_user.id)


@router.get("/{post_id}", response_model=PostPublic)
async def get(post_id: int, db: DBSession):
    """Fetch a single post by ID. Removed posts are hidden unless you are a moderator."""
    post = await get_post(db, post_id)
    if post is None or post.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post


@router.patch("/{post_id}", response_model=PostPublic)
async def edit(post_id: int, data: PostUpdate, current_user: CurrentUser, db: DBSession):
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
    try:
        return await edit_post(db, post, data)
    except ValueError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(post_id: int, current_user: CurrentUser, db: DBSession):
    """Delete a post. Only the author may delete their own post."""
    post = await get_post(db, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your post")
    await delete_post(db, post)


@router.post("/{post_id}/vote", response_model=VotePublic)
async def vote(post_id: int, data: VoteCreate, current_user: CurrentUser, db: DBSession):
    """
    Cast or change a vote on a post (+1 or -1).
    You cannot vote on your own post — authors receive an automatic +1 at post creation.
    Changing an existing vote updates it and adjusts karma accordingly.
    """
    post = await get_post(db, post_id)
    if post is None or post.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id == current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Cannot vote on your own post")

    vote_obj, karma_delta = await cast_vote(db, current_user.id, post_id, data.direction)

    if karma_delta != 0:
        post.karma += karma_delta
        # Reflect on the author's total karma too
        from app.crud.user import get_user_by_id
        author = await get_user_by_id(db, post.author_id)
        if author:
            author.karma += karma_delta
        await db.commit()

    return vote_obj


@router.delete("/{post_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def retract(post_id: int, current_user: CurrentUser, db: DBSession):
    """
    Retract your vote on a post.
    You cannot retract the author's automatic initial vote.
    """
    post = await get_post(db, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id == current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Cannot retract your author vote")

    try:
        karma_delta = await retract_vote(db, current_user.id, post_id)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No vote to retract")

    post.karma += karma_delta
    from app.crud.user import get_user_by_id
    author = await get_user_by_id(db, post.author_id)
    if author:
        author.karma += karma_delta
    await db.commit()
