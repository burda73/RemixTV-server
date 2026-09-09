import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    database_url: str = "sqlite:///./playlist.db"

    upload_dir: str = "uploads"
    max_file_size: int = 2_147_483_648
    allowed_extensions: str = ".mp4,.mkv,.webm"

    secret_key: str = "change-me-in-production"
    cors_origins: str = '["*"]'

    admin_username: str | None = None
    admin_password: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: Any) -> str:
        if isinstance(v, list):
            return json.dumps(v)
        return str(v)

    def cors_origins_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            pass
        return [o.strip() for o in raw.split(",") if o.strip()]

    def allowed_ext_set(self) -> set[str]:
        return {
            e.strip().lower()
            for e in self.allowed_extensions.split(",")
            if e.strip()
        }


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    base = Path(__file__).resolve().parent.parent
    if s.upload_dir and not Path(s.upload_dir).is_absolute():
        s.upload_dir = str(base / s.upload_dir)
    Path(s.upload_dir).mkdir(parents=True, exist_ok=True)
    return s


def get_upload_path(relative_path: str) -> Path:
    return Path(get_settings().upload_dir) / relative_path
