from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHttpException

from app.api.response import ApiError
from app.api.routes import admin, ai, analytics, auth, public
from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.logging import configure_logging
from app.models import Project, SiteSetting
from app.security.network import public_base_url

settings = get_settings()
configure_logging(settings.DEBUG)
logger = logging.getLogger(__name__)

ERROR_MESSAGES_EN = {
    "VALIDATION_ERROR": "Request validation failed",
    "INTERNAL_ERROR": "The server could not process the request",
    "PROJECT_NOT_FOUND": "The project does not exist or is not published",
    "ASSET_NOT_FOUND": "The resource does not exist",
    "CERTIFICATE_NOT_FOUND": "The credential does not exist or is not public",
    "RESUME_NOT_FOUND": "The résumé does not exist or is not public",
    "INVALID_CREDENTIALS": "Incorrect username or password",
    "LOGIN_RATE_LIMITED": "Too many failed attempts. Please try again later",
    "AI_NOT_CONFIGURED": "Configure and enable AI first",
    "AI_KEY_MISSING": "The AI API key is not configured",
}


def localized_error(request: Request, code: str, fallback: str) -> str:
    if request.headers.get("accept-language", "").lower().startswith("en"):
        return ERROR_MESSAGES_EN.get(code, "The request could not be completed")
    return fallback


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    for subdir in ["images", "videos", "documents", "resumes", "text", "thumbnails", "temp"]:
        (settings.UPLOAD_ROOT / subdir).mkdir(parents=True, exist_ok=True)
    test_file = settings.UPLOAD_ROOT / "temp" / ".write-test"
    test_file.write_text("ok", encoding="utf-8")
    test_file.unlink(missing_ok=True)
    logger.info("Portfolio API started")
    yield
    logger.info("Portfolio API stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
    )


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    message = localized_error(request, exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "message": message,
            "error": {"code": exc.code, "message": message, "fields": exc.fields},
            "request_id": getattr(request.state, "request_id", ""),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [
        {"field": ".".join(str(part) for part in error["loc"][1:]), "message": error["msg"]}
        for error in exc.errors()
    ]
    message = localized_error(request, "VALIDATION_ERROR", "请求参数校验失败")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "data": None,
            "message": message,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": message,
                "fields": fields,
            },
            "request_id": getattr(request.state, "request_id", ""),
        },
    )


@app.exception_handler(StarletteHttpException)
async def http_error_handler(request: Request, exc: StarletteHttpException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "message": str(exc.detail),
            "error": {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail)},
            "request_id": getattr(request.state, "request_id", ""),
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception", extra={"request_id": request.state.request_id})
    message = localized_error(request, "INTERNAL_ERROR", "服务器处理请求时发生错误")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "message": message,
            "error": {"code": "INTERNAL_ERROR", "message": message},
            "request_id": request.state.request_id,
        },
    )


app.include_router(public.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(auth.setup_router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")


@app.get("/api/health")
def health() -> dict:
    return {"status": "healthy", "service": settings.APP_NAME}


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots(request: Request) -> str:
    return f"User-agent: *\nAllow: /\nDisallow: /admin\nSitemap: {public_base_url(request)}/sitemap.xml\n"


@app.get("/sitemap.xml")
def sitemap(request: Request) -> PlainTextResponse:
    base = public_base_url(request)
    with get_session_factory()() as db:
        project_uuids = list(
            db.scalars(select(Project.uuid).where(Project.status == "published"))
        )
    urls = ["", "/projects", "/certificates", "/resumes", "/contact"] + [
        f"/projects/{project_uuid}" for project_uuid in project_uuids
    ]
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{base}{path}</loc></url>" for path in urls)
        + "</urlset>"
    )
    return PlainTextResponse(body, media_type="application/xml")
