import hashlib
import re
import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from app.config import get_settings


def sanitize_filename(name: str) -> str:
    base = Path(name).name
    base = re.sub(r"[^\w.\-]", "_", base, flags=re.UNICODE)
    if not base or base in {".", ".."}:
        base = f"video_{uuid.uuid4().hex}.bin"
    return base[:255]


async def save_upload_with_md5(file: UploadFile, dest_dir: Path, max_size: int) -> tuple[Path, str, int]:
    """
    Потоковая запись на диск с подсчётом MD5 и размера (без загрузки всего файла в память).
    Возвращает (путь, md5_hex, размер).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe = sanitize_filename(file.filename or "upload.bin")
    tmp_path = dest_dir / f".tmp_{uuid.uuid4().hex}_{safe}"

    md5 = hashlib.md5()
    total = 0
    chunk_size = 1024 * 1024

    try:
        async with aiofiles.open(tmp_path, "wb") as out:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size:
                    raise ValueError(f"Превышен максимальный размер файла ({max_size} байт)")
                md5.update(chunk)
                await out.write(chunk)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise

    final_path = dest_dir / safe
    if final_path.exists() and final_path != tmp_path:
        final_path.unlink()
    tmp_path.rename(final_path)
    return final_path, md5.hexdigest(), total
