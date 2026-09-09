from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent


def resolve_db_url(url: str, base_dir: Path = BASE_DIR) -> str:
    """Делает относительный sqlite-путь абсолютным относительно каталога проекта.

    Иначе путь считается от текущего рабочего каталога, что ломает запуск
    под systemd/демонами с другим cwd.
    """
    prefix = "sqlite:///"
    if url.startswith(prefix):
        rel = url[len(prefix):]
        if rel and rel != ":memory:" and not Path(rel).is_absolute():
            db_path = base_dir / rel
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{db_path}"
    return url


_settings = get_settings()
_database_url = resolve_db_url(_settings.database_url)

connect_args = {}
if _database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    _database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
