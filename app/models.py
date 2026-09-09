from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ServerState(Base):
    """Одна строка: монотонный номер ревизии плейлиста для клиентов."""

    __tablename__ = "server_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    playlist_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    upload_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    playlist_items: Mapped[list["PlaylistItem"]] = relationship(
        "PlaylistItem", back_populates="video", cascade="all, delete-orphan"
    )


class PlaylistItem(Base):
    __tablename__ = "playlist_items"
    __table_args__ = (UniqueConstraint("video_id", name="uq_playlist_video"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    # `order` зарезервировано в SQL — в БД колонка sort_order, в API — поле order
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    video: Mapped["Video"] = relationship("Video", back_populates="playlist_items")

    @property
    def order(self) -> int:  # noqa: A003 — имя поля в API
        return self.sort_order


class ClientSync(Base):
    __tablename__ = "client_sync"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    client_secret: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    synced_playlist_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_status: Mapped[str | None] = mapped_column(String(512), nullable=True)
