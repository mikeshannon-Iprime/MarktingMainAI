import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.openapi_meta import API_DESCRIPTION, OPENAPI_TAGS
from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.db.database import init_sql_tables

settings = get_settings()
setup_logging(settings)
logger = get_logger("app.main")


def _warm_embedding_backend() -> None:
    try:
        from app.services.embedding_service import get_embedding_status

        status = get_embedding_status()
        if status.get("available"):
            logger.info(
                "Embeddings ready (backend=%s, model=%s)",
                status.get("backend"),
                status.get("model"),
            )
        else:
            logger.warning("Embeddings unavailable: %s", status.get("error", "unknown"))
    except Exception:
        logger.exception("Embedding warmup failed")


def _ensure_playwright_env() -> None:
    """Point Playwright at the local browser cache (Windows-friendly)."""
    import os
    from pathlib import Path

    configured = (settings.playwright_browsers_path or "").strip()
    if not configured:
        return
    browsers_path = Path(configured)
    if not browsers_path.is_absolute():
        browsers_path = Path.cwd() / browsers_path
    browsers_path.mkdir(parents=True, exist_ok=True)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path.resolve())


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (environment=%s)", settings.app_name, settings.environment)
    _ensure_playwright_env()

    try:
        init_sql_tables()
        logger.info("SQL database tables ready")
        from app.services.pg_auth import ensure_auth_ready

        ensure_auth_ready()
        logger.info("Auth/workspace seed verified")
    except Exception:
        logger.exception("SQL database initialization failed")
        if settings.environment == "production":
            raise

    warmup_thread = threading.Thread(target=_warm_embedding_backend, daemon=True)
    warmup_thread.start()

    yield

    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="1.1.0",
    description=API_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={"name": "MarketingMind AI", "email": "admin@marketingmind.ai"},
    servers=[
        {"url": "http://127.0.0.1:8002", "description": "Local development"},
        {"url": "/", "description": "Current host"},
    ],
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code >= 500:
        logger.error(
            "HTTP %s on %s %s: %s",
            exc.status_code,
            request.method,
            request.url.path,
            exc.detail,
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )


app.include_router(router)
