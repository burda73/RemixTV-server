import mimetypes
from pathlib import Path

from fastapi import UploadFile

ALLOWED_MIME_TYPES = frozenset(
    {
        "video/mp4",
        "video/webm",
        "video/x-matroska",
        "application/octet-stream",  # часто приходит с Android/TV — проверяем расширением
    }
)


def _magic_mime(path: Path) -> str | None:
    try:
        import magic  # type: ignore[import-untyped]

        return magic.from_file(str(path), mime=True)
    except Exception:
        return None


def validate_upload_mime(path: Path, declared: str | None) -> None:
    """
    Проверка MIME: python-magic при наличии libmagic, иначе — по расширению + declared.
    """
    ext = path.suffix.lower()
    guessed, _ = mimetypes.guess_type(str(path))
    magic_mime = _magic_mime(path)
    candidates = {declared, guessed, magic_mime}
    candidates.discard(None)
    candidates = {c for c in candidates if c}

    if magic_mime and magic_mime in ALLOWED_MIME_TYPES:
        return
    if declared in ALLOWED_MIME_TYPES and ext in {".mp4", ".mkv", ".webm"}:
        return
    if guessed in ALLOWED_MIME_TYPES and ext in {".mp4", ".mkv", ".webm"}:
        return
    if ext in {".mp4", ".mkv", ".webm"} and (not magic_mime or magic_mime == "application/octet-stream"):
        return

    raise ValueError(
        f"Недопустимый тип файла. Ожидаются video/mp4, video/webm, video/x-matroska. "
        f"Получено: declared={declared!r}, guessed={guessed!r}, magic={magic_mime!r}"
    )


def assert_upload_file_meta(file: UploadFile, allowed_ext: set[str], max_size: int) -> None:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed_ext:
        raise ValueError(f"Недопустимое расширение файла: {suffix!r}. Допустимо: {sorted(allowed_ext)}")
    size = getattr(file, "size", None)
    if size is not None and size > max_size:
        raise ValueError(f"Файл слишком большой: {size} байт (лимит {max_size})")
