from __future__ import annotations

from pathlib import Path
import io
import uuid

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from app.core.config import get_settings

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
PDF_SUFFIXES = {".pdf"}


def ensure_upload_dirs() -> Path:
    root = Path(get_settings().upload_dir)
    for sub in ("photos", "reports", "quotes", "invoices", "templates"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def _object_key(category: str, filename: str) -> str:
    prefix = get_settings().s3_prefix.strip("/")
    return f"{prefix}/{category}/{filename}" if prefix else f"{category}/{filename}"


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


def _supabase_headers(content_type: str | None = None) -> dict[str, str]:
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def ensure_supabase_bucket() -> None:
    """Crée le bucket privé si besoin (idempotent)."""
    settings = get_settings()
    if not settings.supabase_enabled:
        return
    import httpx

    url = f"{settings.supabase_url.rstrip('/')}/storage/v1/bucket"
    payload = {
        "id": settings.supabase_bucket,
        "name": settings.supabase_bucket,
        "public": False,
        "file_size_limit": MAX_UPLOAD_BYTES,
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, headers=_supabase_headers("application/json"), json=payload)
        # 200/201 created, 409 already exists
        if resp.status_code not in (200, 201, 409):
            # Bucket may already exist under list — ignore duplicate-ish errors
            if "already exists" not in resp.text.lower() and "Duplicate" not in resp.text:
                raise RuntimeError(f"Supabase bucket: HTTP {resp.status_code} {resp.text[:300]}")


def _supabase_put(key: str, data: bytes, content_type: str) -> None:
    settings = get_settings()
    import httpx

    ensure_supabase_bucket()
    url = (
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/"
        f"{settings.supabase_bucket}/{key}"
    )
    headers = _supabase_headers(content_type)
    headers["x-upsert"] = "true"
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, headers=headers, content=data)
        if resp.status_code not in (200, 201):
            raise HTTPException(
                status_code=502,
                detail=f"Échec upload Supabase ({resp.status_code})",
            )


def _supabase_get(key: str) -> bytes:
    settings = get_settings()
    import httpx

    url = (
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/"
        f"{settings.supabase_bucket}/{key}"
    )
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(url, headers=_supabase_headers())
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Fichier introuvable")
        return resp.content


def _remote_put(key: str, data: bytes, content_type: str) -> bool:
    """True si écriture remote effectuée."""
    settings = get_settings()
    if settings.supabase_enabled:
        _supabase_put(key, data, content_type)
        return True
    client = _s3_client()
    if client:
        client.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return True
    return False


def _remote_get(key: str) -> bytes | None:
    settings = get_settings()
    if settings.supabase_enabled:
        return _supabase_get(key)
    client = _s3_client()
    if client:
        try:
            obj = client.get_object(Bucket=settings.s3_bucket, Key=key)
            return obj["Body"].read()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=404, detail="Fichier introuvable") from exc
    return None


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
    content_type = file.content_type or "application/octet-stream"
    key = _object_key(category, stored)
    if not _remote_put(key, data, content_type):
        dest = Path(get_settings().upload_dir) / category / stored
        dest.write_bytes(data)
    return stored, file.filename or stored


def save_bytes(data: bytes, category: str, filename: str, content_type: str = "application/pdf") -> str:
    """Persiste des bytes générés (PDF devis/facture) en local, Supabase ou S3."""
    ensure_upload_dirs()
    key = _object_key(category, filename)
    if not _remote_put(key, data, content_type):
        dest = Path(get_settings().upload_dir) / category / filename
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
    key = _object_key(category, filename)
    if settings.remote_storage_enabled:
        data = _remote_get(key)
        if data is None:
            raise HTTPException(status_code=404, detail="Fichier introuvable")
        return data
    path = resolve_path(category, filename)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return path.read_bytes()


def materialize_path(category: str, filename: str) -> Path:
    """Retourne un chemin local utilisable (télécharge depuis remote si besoin)."""
    settings = get_settings()
    if not settings.remote_storage_enabled:
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
    if settings.remote_storage_enabled:
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
