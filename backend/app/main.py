from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.api import (
    auth,
    catalog,
    dashboard,
    dossiers,
    expertise,
    invoices,
    notifications,
    quotes,
    settings,
    templates,
    workshop,
)
from app.core.config import get_settings
from app.core.database import Base, engine
from app.services.bootstrap import ensure_demo_user
from app.services.storage import ensure_upload_dirs

logger = logging.getLogger("auta")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

settings_cfg = get_settings()

if settings_cfg.sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(dsn=settings_cfg.sentry_dsn, integrations=[FastApiIntegration()], traces_sample_rate=0.1)
        logger.info("Sentry initialisé")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sentry non initialisé: %s", exc)

if settings_cfg.secret_key == "auta-dev-secret-key":
    logger.warning("SECRET_KEY par défaut — changez-la en production (SECRET_KEY)")

app = FastAPI(title="AUTA Gestion API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_cfg.cors_origin_list,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(settings.router)
app.include_router(dossiers.router)
app.include_router(expertise.router)
app.include_router(quotes.router)
app.include_router(invoices.router)
app.include_router(workshop.router)
app.include_router(dashboard.router)
app.include_router(catalog.router)
app.include_router(notifications.router)
app.include_router(templates.router)


@app.on_event("startup")
def on_startup():
    ensure_upload_dirs()
    Base.metadata.create_all(bind=engine)
    ensure_demo_user()
    logger.info("AUTA Gestion démarré — DB + uploads OK")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    messages = []
    for err in exc.errors():
        loc = " → ".join(str(x) for x in err.get("loc", []) if x != "body")
        msg = err.get("msg", "valeur invalide")
        messages.append(f"{loc}: {msg}" if loc else msg)
    return JSONResponse(
        status_code=422,
        content={"detail": " ; ".join(messages) or "Données invalides"},
    )


@app.get("/")
def root():
    return RedirectResponse(url="http://127.0.0.1:5173/")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "product": "AUTA Gestion",
        "openai": False,
        "grok": bool(settings_cfg.grok_api_key),
        "s3": settings_cfg.s3_enabled,
        "redis": bool(settings_cfg.redis_url),
        "registration_open": settings_cfg.allow_open_registration,
    }
