import secrets
from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db as _get_db

security = HTTPBasic(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    yield from _get_db()


def require_admin(credentials: HTTPBasicCredentials | None = Depends(security)) -> None:
    """Если заданы ADMIN_USERNAME и ADMIN_PASSWORD — защищает админские маршруты."""
    settings = get_settings()
    if not settings.admin_username or not settings.admin_password:
        return
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется базовая аутентификация",
            headers={"WWW-Authenticate": "Basic"},
        )
    user_ok = secrets.compare_digest(credentials.username, settings.admin_username)
    pass_ok = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учётные данные",
            headers={"WWW-Authenticate": "Basic"},
        )
