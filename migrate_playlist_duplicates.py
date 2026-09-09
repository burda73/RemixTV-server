"""
Миграция БД: снять ограничение UNIQUE(video_id) с playlist_items,
чтобы одно видео могло встречаться в плейлисте несколько раз.

Для SQLite таблица пересоздаётся (ALTER ... DROP CONSTRAINT не поддерживается).
Данные сохраняются. Для PostgreSQL выполните вручную:
    ALTER TABLE playlist_items DROP CONSTRAINT uq_playlist_video;

Запуск: python3 migrate_playlist_duplicates.py [путь_к_базе]
"""
import os
import sqlite3
import sys
from pathlib import Path


def _db_path() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    database_url = os.getenv("DATABASE_URL", "sqlite:///./playlist.db")
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return Path("playlist.db")
    p = database_url[len(prefix):]
    return Path(p)


def migrate() -> bool:
    path = _db_path()
    if not path.is_file():
        print(f"База не найдена: {path!s}. Миграция не требуется.")
        return False

    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='playlist_items'"
        ).fetchone()
        if not row:
            print("Таблица playlist_items не найдена. Миграция не требуется.")
            return False
        if "uq_playlist_video" not in row[0]:
            print("Ограничение uq_playlist_video уже снято. Миграция не требуется.")
            return False

        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN")
        conn.execute("ALTER TABLE playlist_items RENAME TO playlist_items_old")
        conn.execute(
            """
            CREATE TABLE playlist_items (
                id INTEGER NOT NULL,
                video_id INTEGER NOT NULL,
                sort_order INTEGER NOT NULL,
                start_date DATETIME,
                end_date DATETIME,
                is_active BOOLEAN NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(video_id) REFERENCES videos (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            INSERT INTO playlist_items (id, video_id, sort_order, start_date, end_date, is_active)
            SELECT id, video_id, sort_order, start_date, end_date, is_active
            FROM playlist_items_old
            """
        )
        conn.execute("DROP TABLE playlist_items_old")
        conn.execute("COMMIT")
        conn.execute("PRAGMA foreign_keys=ON")
        print(f"Миграция выполнена: {path!s}")
        return True
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        sys.exit(0 if migrate() else 1)
    except Exception as e:  # noqa: BLE001
        print(f"Ошибка миграции: {e}", file=sys.stderr)
        sys.exit(2)