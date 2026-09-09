import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Path as PathParam, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud
from app.config import get_settings, get_upload_path
from app.dependencies import get_db, require_admin
from app.models import PlaylistItem
from app.schemas import VideoOut, VideoRenameBody
from app.utils.file_handler import save_upload_with_md5
from app.utils.validators import assert_upload_file_meta, validate_upload_mime

logger = logging.getLogger(__name__)

router = APIRouter(tags=["videos"])


def _get_video_path(video: "Video") -> Path:
    return get_upload_path(video.file_path)


@router.get("/api/videos", response_model=list[VideoOut])
def list_videos(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> list[VideoOut]:
    return [VideoOut.model_validate(v) for v in crud.list_videos(db)]


@router.patch("/api/videos/{video_id}", response_model=VideoOut)
def rename_video(
    video_id: int,
    body: VideoRenameBody,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> VideoOut:
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    new_filename = body.filename.strip()
    if not new_filename:
        raise HTTPException(status_code=400, detail="Имя файла не может быть пустым")
    if "/" in new_filename or "\\" in new_filename:
        raise HTTPException(status_code=400, detail="Имя файла не может содержать / или \\")
    updated = crud.rename_video(db, video, new_filename)
    return VideoOut.model_validate(updated)


@router.delete("/api/videos/{video_id}")
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> dict[str, str]:
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    path = _get_video_path(video)
    if path.exists():
        path.unlink(missing_ok=True)
    crud.delete_video(db, video)
    return {"detail": "Видео удалено"}


@router.delete("/api/videos")
def delete_all_videos(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> dict[str, str]:
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
    count = crud.delete_all_videos(db)
    return {"detail": f"Удалено видео: {count}"}


@router.post("/upload", response_model=VideoOut)
async def upload_video(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
    file: UploadFile = File(...),
) -> VideoOut:
    settings = get_settings()
    allowed = settings.allowed_ext_set()
    try:
        assert_upload_file_meta(file, allowed, settings.max_file_size)
        dest = Path(settings.upload_dir)
        path, md5_hex, size = await save_upload_with_md5(file, dest, settings.max_file_size)
        validate_upload_mime(path, file.content_type)
    except ValueError as e:
        logger.warning("Ошибка валидации загрузки: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Ошибка сохранения файла")
        raise HTTPException(status_code=500, detail=f"Не удалось сохранить файл: {e}") from e

    filename = path.name
    existing = crud.get_video_by_filename(db, filename)
    try:
        if existing:
            old_path = _get_video_path(existing)
            if old_path.resolve() != path.resolve() and old_path.exists():
                old_path.unlink(missing_ok=True)
            updated = crud.update_video_file(
                db,
                existing,
                file_path=filename,
                file_size=size,
                file_hash=md5_hex,
            )
            if not db.scalar(
                select(PlaylistItem).where(PlaylistItem.video_id == existing.id)
            ):
                crud.append_video_to_playlist(db, existing.id)
            return VideoOut.model_validate(updated)
        created = crud.create_video(
            db,
            filename=filename,
            file_path=filename,
            file_size=size,
            file_hash=md5_hex,
        )
        crud.append_video_to_playlist(db, created.id)
        return VideoOut.model_validate(created)
    except Exception as e:
        logger.exception("Ошибка записи в БД после загрузки")
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {e}") from e


@router.get("/api/videos/{video_id}/preview")
def preview_video(
    video_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> FileResponse:
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    path = _get_video_path(video)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Файл не найден на сервере")
    ext = path.suffix.lower()
    media_types = {
        ".mp4": "video/mp4",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        ".avi": "video/x-msvideo",
        ".mov": "video/quicktime",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    return FileResponse(
        path=str(path.resolve()),
        media_type=media_type,
        filename=video.filename,
    )


@router.get("/api/videos/{video_id}/download")
def download_video_admin(
    video_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> FileResponse:
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    path = _get_video_path(video)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Файл не найден на сервере")
    return FileResponse(
        path=str(path.resolve()),
        filename=video.filename,
        media_type="application/octet-stream",
        headers={
            "X-Video-MD5": video.file_hash,
            "X-Video-Version": str(video.version),
        },
    )
