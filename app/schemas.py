from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator


class VideoBase(BaseModel):
    filename: str
    duration: float = 0.0
    file_size: int
    file_hash: str
    version: int


class VideoOut(VideoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    upload_date: datetime


class VideoRenameBody(BaseModel):
    filename: str


class PlaylistItemCreate(BaseModel):
    video_id: int
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def validate_period(self) -> "PlaylistItemCreate":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date не может быть позже end_date")
        return self


class PlaylistItemUpdate(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_active: bool | None = None


class PlaylistReorderEntry(BaseModel):
    id: int
    order: int


class PlaylistReorderBody(BaseModel):
    items: list[PlaylistReorderEntry]


class PlaylistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    order: int
    start_date: datetime | None
    end_date: datetime | None
    is_active: bool
    video: VideoOut


class SyncVideoItem(BaseModel):
    playlist_item_id: int
    video_id: int
    filename: str
    download_path: str
    file_hash: str
    version: int
    file_size: int
    order: int


class SyncResponse(BaseModel):
    playlist_version: int
    items: list[SyncVideoItem]


class ClientStatusBody(BaseModel):
    """Опционально: текст статуса и версия, которую клиент считает синхронизированной."""

    detail: str | None = None
    synced_playlist_version: int | None = None


class ClientRegisterResponse(BaseModel):
    client_id: str
    client_secret: str


class ClientLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: str
    name: str | None
    is_active: bool
    is_online: bool = False
    last_sync: datetime | None
    synced_playlist_version: int
    current_playlist_version: int
    last_status: str | None


class ClientCreateBody(BaseModel):
    name: str | None = None


class ClientToggleBody(BaseModel):
    is_active: bool


class ClientUpdateBody(BaseModel):
    name: str | None = None
