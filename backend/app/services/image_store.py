"""
Image upload validation and ephemeral storage.

Privacy contract:
- Logs contain only image_ref (path slug) and file format/size.
- Raw image bytes are NEVER written to logs.
- PII (height, weight) is NEVER written to logs at INFO or below.
"""

import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

logger = logging.getLogger(__name__)

# Magic-byte signatures
_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_HEADER_READ_BYTES = 8


class ImageValidationError(ValueError):
    """Raised when an uploaded file fails format or size checks."""


def _detect_format(header: bytes) -> str:
    """Return 'jpeg' or 'png', or raise ImageValidationError."""
    if header[:3] == _JPEG_MAGIC:
        return "jpeg"
    if header[:8] == _PNG_MAGIC:
        return "png"
    raise ImageValidationError(
        "Desteklenmeyen dosya formatı. Yalnızca JPEG ve PNG kabul edilmektedir."
    )


async def validate_and_store(
    upload: UploadFile,
    subfolder: str,
    *,
    storage_dir: str,
    max_upload_mb: int,
) -> str:
    """
    Validate image format (magic bytes) and size, then write to storage.
    Returns the image_ref (relative path slug) — never returns bytes.
    """
    max_bytes = max_upload_mb * 1024 * 1024

    header = await upload.read(_HEADER_READ_BYTES)
    if len(header) < _HEADER_READ_BYTES:
        raise ImageValidationError("Dosya çok küçük veya boş.")

    fmt = _detect_format(header)

    # Read the remainder; read one byte over budget to detect oversize
    rest = await upload.read(max_bytes + 1)
    total_size = len(header) + len(rest)

    if total_size > max_bytes:
        raise ImageValidationError(
            f"Dosya boyutu çok büyük. Maksimum {max_upload_mb} MB izin verilmektedir."
        )

    ext = "jpg" if fmt == "jpeg" else "png"
    filename = f"{uuid.uuid4()}.{ext}"
    dest_dir = Path(storage_dir) / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    dest.write_bytes(header + rest)

    image_ref = f"{subfolder}/{filename}"
    # Log ref and metadata only — no image bytes, no PII
    logger.info(
        "image_stored ref=%s fmt=%s size_bytes=%d", image_ref, fmt, total_size
    )
    return image_ref


def delete_image(image_ref: str, *, storage_dir: str) -> None:
    path = Path(storage_dir) / image_ref
    if path.exists():
        path.unlink()
        logger.info("image_deleted ref=%s", image_ref)


def image_exists(image_ref: str, *, storage_dir: str) -> bool:
    return (Path(storage_dir) / image_ref).exists()


def read_image_bytes(image_ref: str, *, storage_dir: str) -> Optional[bytes]:
    """
    Read image bytes for downstream AI processing only.
    Callers MUST NOT log the return value.
    """
    path = Path(storage_dir) / image_ref
    if not path.exists():
        return None
    return path.read_bytes()
