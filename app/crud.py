from datetime import datetime, timezone

from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.models import ClientSync, PlaylistItem, ServerState, Video


def _ensure_server_state(db: Session) -> ServerState:
    row = db.scalar(select(ServerState).where(ServerState.id == 1))
    if row is None:
        row = ServerState(id=1, playlist_revision=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def bump_playlist_revision(db: Session) -> int:
    st = _ensure_server_state(db)
    st.playlist_revision += 1
    db.add(st)
    db.commit()
    db.refresh(st)
    return st.playlist_revision


def get_playlist_revision(db: Session) -> int:
    st = _ensure_server_state(db)
    return st.playlist_revision


def list_videos(db: Session) -> list[Video]:
    return list(db.scalars(select(Video).order_by(Video.upload_date.desc())).all())


def get_video(db: Session, video_id: int) -> Video | None:
    return db.get(Video, video_id)


def get_video_by_filename(db: Session, filename: str) -> Video | None:
    return db.scalar(select(Video).where(Video.filename == filename))


def create_video(
    db: Session,
    *,
    filename: str,
    file_path: str,
    file_size: int,
    file_hash: str,
    duration: float = 0.0,
) -> Video:
    now = datetime.now(timezone.utc)
    v = Video(
        filename=filename,
        file_path=file_path,
        duration=duration,
        upload_date=now,
        file_size=file_size,
        file_hash=file_hash,
        version=1,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def update_video_file(
    db: Session,
    video: Video,
    *,
    file_path: str,
    file_size: int,
    file_hash: str,
    duration: float = 0.0,
) -> Video:
    video.file_path = file_path
    video.file_size = file_size
    video.file_hash = file_hash
    video.duration = duration
    video.version = video.version + 1
    video.upload_date = datetime.now(timezone.utc)
    db.add(video)
    db.commit()
    db.refresh(video)
    bump_playlist_revision(db)
    return video


def rename_video(db: Session, video: Video, new_filename: str) -> Video:
    video.filename = new_filename
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def delete_video(db: Session, video: Video) -> None:
    db.delete(video)
    db.commit()


def delete_all_videos(db: Session) -> int:
    count = db.query(Video).delete()
    db.commit()
    return count


def _next_playlist_order(db: Session) -> int:
    m = db.scalar(select(func.max(PlaylistItem.sort_order)))
    return (m or -1) + 1


def append_video_to_playlist(
    db: Session,
    video_id: int,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    is_active: bool = True,
) -> PlaylistItem | None:
    """Добавляет видео в конец, если ещё нет в плейлисте."""
    existing = db.scalar(select(PlaylistItem).where(PlaylistItem.video_id == video_id))
    if existing:
        return None
    item = PlaylistItem(
        video_id=video_id,
        sort_order=_next_playlist_order(db),
        start_date=start_date,
        end_date=end_date,
        is_active=is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    bump_playlist_revision(db)
    return item


def list_playlist_items_with_video(db: Session) -> list[PlaylistItem]:
    stmt: Select[tuple[PlaylistItem]] = (
        select(PlaylistItem)
        .options(joinedload(PlaylistItem.video))
        .order_by(PlaylistItem.sort_order)
    )
    return list(db.scalars(stmt).unique().all())


def active_playlist_query(now: datetime):
    return (
        select(PlaylistItem)
        .options(joinedload(PlaylistItem.video))
        .where(PlaylistItem.is_active.is_(True))
        .where(
            or_(
                PlaylistItem.start_date.is_(None),
                PlaylistItem.start_date <= now,
            )
        )
        .where(
            or_(
                PlaylistItem.end_date.is_(None),
                PlaylistItem.end_date >= now,
            )
        )
        .order_by(PlaylistItem.sort_order)
    )


def get_active_playlist(db: Session, now: datetime | None = None) -> list[PlaylistItem]:
    if now is None:
        now = datetime.now(timezone.utc)
    stmt = active_playlist_query(now)
    return list(db.scalars(stmt).unique().all())


def get_playlist_item(db: Session, item_id: int) -> PlaylistItem | None:
    return db.scalar(
        select(PlaylistItem)
        .options(joinedload(PlaylistItem.video))
        .where(PlaylistItem.id == item_id)
    )


def create_playlist_item(
    db: Session,
    *,
    video_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    is_active: bool = True,
) -> PlaylistItem:
    item = PlaylistItem(
        video_id=video_id,
        sort_order=_next_playlist_order(db),
        start_date=start_date,
        end_date=end_date,
        is_active=is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    bump_playlist_revision(db)
    return item


_UNSET = object()


def update_playlist_item(
    db: Session,
    item: PlaylistItem,
    *,
    start_date: object = _UNSET,
    end_date: object = _UNSET,
    is_active: object = _UNSET,
) -> PlaylistItem:
    if start_date is not _UNSET:
        item.start_date = start_date  # type: ignore[assignment]
    if end_date is not _UNSET:
        item.end_date = end_date  # type: ignore[assignment]
    if is_active is not _UNSET:
        item.is_active = is_active  # type: ignore[assignment]
    db.add(item)
    db.commit()
    db.refresh(item)
    bump_playlist_revision(db)
    return item


def delete_playlist_item(db: Session, item: PlaylistItem) -> None:
    db.delete(item)
    db.commit()
    bump_playlist_revision(db)


def reorder_playlist(db: Session, id_to_order: dict[int, int]) -> None:
    for pid, ord_ in id_to_order.items():
        db.execute(update(PlaylistItem).where(PlaylistItem.id == pid).values(sort_order=ord_))
    db.commit()
    bump_playlist_revision(db)


def get_or_create_client(db: Session, client_id: str) -> ClientSync:
    row = db.scalar(select(ClientSync).where(ClientSync.client_id == client_id))
    if row:
        return row
    row = ClientSync(client_id=client_id, last_sync=None, synced_playlist_version=0)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def touch_client_sync(db: Session, client: ClientSync) -> ClientSync:
    client.last_sync = datetime.now(timezone.utc)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def update_client_status(
    db: Session,
    client: ClientSync,
    *,
    detail: str | None = None,
    synced_playlist_version: int | None = None,
) -> ClientSync:
    client.last_sync = datetime.now(timezone.utc)
    if detail is not None:
        client.last_status = detail[:512]
    if synced_playlist_version is not None:
        client.synced_playlist_version = synced_playlist_version
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def list_clients(db: Session) -> list[ClientSync]:
    return list(db.scalars(select(ClientSync).order_by(ClientSync.id.desc())).all())


def get_client_by_id(db: Session, client_id: int) -> ClientSync | None:
    return db.get(ClientSync, client_id)


def toggle_client_active(db: Session, client: ClientSync, is_active: bool) -> ClientSync:
    client.is_active = is_active
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def is_client_online(client: ClientSync) -> bool:
    if not client.last_sync:
        return False
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    last = client.last_sync
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return now - last < timedelta(minutes=10)
