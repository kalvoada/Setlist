"""Opening shared music on the listener's own streaming service."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import music as music_links
from .. import presenters
from ..database import schemas
from ..database.crud import posts as posts_crud
from ..dependencies import CurrentUser, DBSession

router = APIRouter(prefix="/music", tags=["music"])


@router.get("/{music_id}/native-link", response_model=schemas.NativeLink)
def read_native_link(music_id: int, current_user: CurrentUser, db: DBSession):
    """Where this item opens on your service, looking it up if nobody has yet."""
    item = posts_crud.get_music_item(db, music_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Music not found")

    native = presenters.native_link(item, current_user.native_provider)
    if native is None:
        raise HTTPException(
            status_code=400, detail="Choose your music service in Settings first."
        )
    if native.status != "pending":
        return native

    try:
        links = music_links.resolve_links(item.url)
    except music_links.LinkResolutionError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Couldn't look this up on {native.provider_name} right now. "
            "Try again in a moment.",
        ) from exc

    posts_crud.save_provider_links(db, item, links)
    return presenters.native_link(item, current_user.native_provider)
