from __future__ import annotations

from pathlib import Path
import io
import shutil
import uuid

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse

from app.core.config import get_settings

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
PDF_SUFFIXES = {".pdf"}


def ensure_upload_dirs() -> Path:
    root = Path(get_settings().upload_dir)
    for sub in ("photos", "reports", "quotes", "invoices", "templates"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def _s3_client():
    settings = get_settings()
    if not settings.s3_enabled:
        return None
    import boto3
    from botocore.config import Config

    kwargs = {
        "aws_access_key_id": settings.s3_access_key,
        "aws_secret_access_key": settings.s3_secret_key,
        "region_name": settings.s3_region or "auto",
        "config": Config(signature_version="s3v4"),
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return boto3.client("s3", **kwargs)


def _s3_key(category: str, filename: str) -> str:
    prefix = get_settings().s3_prefix.strip("/")
    return f"{prefix}/{category}/{filename}" if prefix else f"{category}/{filename}"


def save_upload(
    file: UploadFile,
    category: str,
    *,
    allowed_suffixes: set[str] | None = None,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> tuple[str, str]:
    ensure_upload_dirs()
    suffix = Path(file.filename or "file").suffix.lower() or ".bin"
    if allowed_suffixes and suffix not in allowed_suffixes:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non accepté ({suffix}). Formats : {', '.join(sorted(allowed_suffixes))}",
        )

    stored = f"{uuid.uuid4().hex}{suffix}"
    size = 0
    buffer = io.BytesIO()
    while True:
        chunk = file.file.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"Fichier trop volumineux (max {max_bytes // (1024 * 1024)} Mo)",
            )
        buffer.write(chunk)
    data = buffer.getvalue()

    settings = get_settings()
    client = _s3_client()
    if client:
        client.put_object(
            Bucket=settings.s3_bucket,
            Key=_s3_key(category, stored),
            Body=data,
            ContentType=file.content_type or "application/octet-stream",
        )
    else:
        dest = Path(settings.upload_dir) / category / stored
        dest.write_bytes(data)
    return stored, file.filename or stored


def save_bytes(data: bytes, category: str, filename: str, content_type: str = "application/pdf") -> str:
    """Persiste des bytes générés (PDF devis/facture) en local ou S3."""
    ensure_upload_dirs()
    settings = get_settings()
    client = _s3_client()
    if client:
        client.put_object(
            Bucket=settings.s3_bucket,
            Key=_s3_key(category, filename),
            Body=data,
            ContentType=content_type,
        )
    else:
        dest = Path(settings.upload_dir) / category / filename
        dest.write_bytes(data)
    return filename


def resolve_path(category: str, filename: str) -> Path:
    if not filename or Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Nom de fichier invalide")
    root = Path(get_settings().upload_dir).resolve()
    path = (root / category / filename).resolve()
    if not str(path).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Chemin de fichier invalide")
    return path


def read_bytes(category: str, filename: str) -> bytes:
    settings = get_settings()
    client = _s3_client()
    if client:
        try:
            obj = client.get_object(Bucket=settings.s3_bucket, Key=_s3_key(category, filename))
            return obj["Body"].read()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=404, detail="Fichier introuvable") from exc
    path = resolve_path(category, filename)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return path.read_bytes()


def materialize_path(category: str, filename: str) -> Path:
    """Retourne un chemin local utilisable (télécharge depuis S3 si besoin)."""
    settings = get_settings()
    if not settings.s3_enabled:
        path = resolve_path(category, filename)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Fichier introuvable")
        return path
    import tempfile

    data = read_bytes(category, filename)
    suffix = Path(filename).suffix or ".bin"
    tmp = Path(tempfile.gettempdir()) / f"auta-{uuid.uuid4().hex}{suffix}"
    tmp.write_bytes(data)
    return tmp


def file_response_or_404(category: str, filename: str, download_name: str | None = None):
    settings = get_settings()
    name = download_name or filename
    client = _s3_client()
    if client:
        data = read_bytes(category, filename)
        return Response(
            content=data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )
    path = resolve_path(category, filename)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(path, filename=name)
