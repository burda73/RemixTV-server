import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import crud
from app.dependencies import get_db
from app.schemas import ClientStatusBody, SyncResponse, SyncVideoItem

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sync"])


@router.get("/api/sync", response_model=SyncResponse)
def sync_playlist(
    client_id: str = Query(..., min_length=36, max_length=36),
    db: Session = Depends(get_db),
) -> SyncResponse:
    client = crud.get_or_create_client(db, client_id)
    crud.touch_client_sync(db, client)
    if not client.is_active:
        raise HTTPException(status_code=403, detail="Клиент не активирован. Обратитесь к оператору.")
    now = datetime.now(timezone.utc)
    items = crud.get_active_playlist(db, now)
    version = crud.get_playlist_revision(db)
    out_items: list[SyncVideoItem] = []
    for it in items:
        v = it.video
        out_items.append(
            SyncVideoItem(
                playlist_item_id=it.id,
                video_id=v.id,
                filename=v.filename,
                download_path=f"/api/download/{v.id}?client_id={client_id}",
                file_hash=v.file_hash,
                version=v.version,
                file_size=v.file_size,
                order=it.sort_order,
            )
        )
    return SyncResponse(playlist_version=version, items=out_items)


@router.get("/api/download/{video_id}")
def download_video(
    video_id: int,
    client_id: str = Query(..., min_length=36, max_length=36),
    db: Session = Depends(get_db),
) -> FileResponse:
    client = crud.get_or_create_client(db, client_id)
    if not client.is_active:
        raise HTTPException(status_code=403, detail="Клиент не активирован. Обратитесь к оператору.")
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    from app.config import get_upload_path
    path = get_upload_path(video.file_path)
    if not path.is_file():
        logger.error("Файл отсутствует на диске: %s", path)
        raise HTTPException(status_code=404, detail="Файл не найден на сервере")
    return FileResponse(
        path=str(path.resolve()),
        filename=video.filename,
        media_type="application/octet-stream",
        headers={"X-Video-MD5": video.file_hash, "X-Video-Version": str(video.version)},
    )


@router.post("/api/client/status")
def client_status(
    client_id: str = Query(..., min_length=36, max_length=36),
    body: ClientStatusBody | None = None,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    client = crud.get_or_create_client(db, client_id)
    if not client.is_active:
        raise HTTPException(status_code=403, detail="Клиент не активирован. Обратитесь к оператору.")
    crud.update_client_status(
        db,
        client,
        detail=body.detail if body else None,
        synced_playlist_version=body.synced_playlist_version if body else None,
    )
    return {"detail": "Статус обновлён"}
