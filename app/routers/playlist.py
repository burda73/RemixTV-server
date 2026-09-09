import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud
from app.dependencies import get_db, require_admin
from app.schemas import (
    PlaylistItemCreate,
    PlaylistItemOut,
    PlaylistItemUpdate,
    PlaylistReorderBody,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["playlist"])


def _validate_period(start: datetime | None, end: datetime | None) -> None:
    if start and end and start > end:
        raise HTTPException(status_code=400, detail="start_date не может быть позже end_date")


@router.get("/api/playlist", response_model=list[PlaylistItemOut])
def get_playlist(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> list[PlaylistItemOut]:
    items = crud.list_playlist_items_with_video(db)
    return [PlaylistItemOut.model_validate(i) for i in items]


@router.post("/api/playlist", response_model=PlaylistItemOut)
def add_to_playlist(
    body: PlaylistItemCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> PlaylistItemOut:
    video = crud.get_video(db, body.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    _validate_period(body.start_date, body.end_date)
    try:
        item = crud.create_playlist_item(
            db,
            video_id=body.video_id,
            start_date=body.start_date,
            end_date=body.end_date,
            is_active=body.is_active,
        )
    except IntegrityError as e:
        logger.warning("Дубликат видео в плейлисте: %s", e)
        raise HTTPException(
            status_code=409,
            detail="Это видео уже добавлено в плейлист",
        ) from e
    item = crud.get_playlist_item(db, item.id)
    assert item is not None
    return PlaylistItemOut.model_validate(item)


@router.put("/api/playlist/{item_id}", response_model=PlaylistItemOut)
def update_playlist_item(
    item_id: int,
    body: PlaylistItemUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> PlaylistItemOut:
    item = crud.get_playlist_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Элемент плейлиста не найден")
    data = body.model_dump(exclude_unset=True)
    start = item.start_date
    end = item.end_date
    if "start_date" in data:
        start = data["start_date"]
    if "end_date" in data:
        end = data["end_date"]
    if "start_date" in data or "end_date" in data:
        _validate_period(start, end)
    kwargs: dict[str, object] = {}
    if "start_date" in data:
        kwargs["start_date"] = data["start_date"]
    if "end_date" in data:
        kwargs["end_date"] = data["end_date"]
    if "is_active" in data:
        if data["is_active"] is None:
            raise HTTPException(status_code=400, detail="is_active должен быть true или false")
        kwargs["is_active"] = data["is_active"]
    if not kwargs:
        return PlaylistItemOut.model_validate(item)
    updated = crud.update_playlist_item(db, item, **kwargs)
    refreshed = crud.get_playlist_item(db, updated.id)
    assert refreshed is not None
    return PlaylistItemOut.model_validate(refreshed)


@router.delete("/api/playlist/{item_id}")
def delete_playlist_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> dict[str, str]:
    item = crud.get_playlist_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Элемент плейлиста не найден")
    crud.delete_playlist_item(db, item)
    return {"detail": "Удалено"}


@router.post("/api/playlist/reorder")
def reorder_playlist(
    body: PlaylistReorderBody,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> dict[str, str]:
    mapping = {i.id: i.order for i in body.items}
    ids = list(mapping.keys())
    found = {row.id for row in crud.list_playlist_items_with_video(db)}
    missing = [i for i in ids if i not in found]
    if missing:
        raise HTTPException(status_code=400, detail=f"Неизвестные id элементов: {missing}")
    crud.reorder_playlist(db, mapping)
    return {"detail": "Порядок обновлён"}
