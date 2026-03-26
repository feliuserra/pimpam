"""Community label endpoints — mod-created labels for organizing posts."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DBSession
from app.crud.community import get_community_by_name
from app.crud.community_label import (
    create_label,
    delete_label,
    get_label,
    list_labels,
    reorder_labels,
    update_label,
)
from app.crud.moderation import _is_moderator
from app.models.community_label import CommunityLabel
from app.schemas.community_label import (
    LabelCreate,
    LabelPublic,
    LabelReorder,
    LabelUpdate,
)

router = APIRouter(prefix="/communities", tags=["community-labels"])


async def _get_community_or_404(db: DBSession, name: str):
    community = await get_community_by_name(db, name)
    if community is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Community not found")
    return community


async def _require_mod(db: DBSession, community_id: int, user_id: int):
    if not await _is_moderator(db, community_id, user_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Moderator access required"
        )


@router.get("/{name}/labels", response_model=list[LabelPublic])
async def get_labels(name: str, db: DBSession):
    """List labels for a community. Public endpoint."""
    community = await _get_community_or_404(db, name)
    return await list_labels(db, community.id)


@router.post(
    "/{name}/labels",
    response_model=LabelPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_label_endpoint(
    name: str, data: LabelCreate, current_user: CurrentUser, db: DBSession
):
    """Create a new label. Moderator+ only."""
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)

    # Check duplicate name
    existing = await db.execute(
        select(CommunityLabel).where(
            CommunityLabel.community_id == community.id,
            CommunityLabel.name == data.name.strip(),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Label with this name already exists"
        )

    return await create_label(db, community.id, data)


@router.patch("/{name}/labels/{label_id}", response_model=LabelPublic)
async def update_label_endpoint(
    name: str,
    label_id: int,
    data: LabelUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Update a label. Moderator+ only."""
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)

    label = await get_label(db, label_id)
    if label is None or label.community_id != community.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Label not found")

    # Check duplicate name if renaming
    if data.name is not None:
        existing = await db.execute(
            select(CommunityLabel).where(
                CommunityLabel.community_id == community.id,
                CommunityLabel.name == data.name.strip(),
                CommunityLabel.id != label_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="Label with this name already exists"
            )

    return await update_label(db, label, data)


@router.delete("/{name}/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label_endpoint(
    name: str, label_id: int, current_user: CurrentUser, db: DBSession
):
    """Delete a label. Posts with this label will have label_id set to NULL. Moderator+ only."""
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)

    label = await get_label(db, label_id)
    if label is None or label.community_id != community.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Label not found")

    await delete_label(db, label)


@router.put("/{name}/labels/reorder", response_model=list[LabelPublic])
async def reorder_labels_endpoint(
    name: str, data: LabelReorder, current_user: CurrentUser, db: DBSession
):
    """Reorder labels by passing an ordered list of IDs. Moderator+ only."""
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)
    return await reorder_labels(db, community.id, data.ids)
