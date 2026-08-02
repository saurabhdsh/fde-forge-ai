"""FastAPI application entrypoint."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api.responses import failure
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

REQUEST_COUNT = Counter(
    "fde_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    logger.info("app_starting", app=settings.app_name, env=settings.app_env)
    logger.info(
        "ai_provider_status",
        default_provider=settings.ai_default_provider,
        openai_configured=settings.openai_configured,
        bedrock_enabled=settings.bedrock_enabled,
        bedrock_configured=settings.bedrock_configured,
        bedrock_model=settings.bedrock_model_id,
        aws_region=settings.aws_region,
        ai_configured=settings.ai_configured,
    )
    if settings.bedrock_enabled and not settings.bedrock_configured:
        logger.warning(
            "bedrock_enabled_but_credentials_missing",
            hint="Mac: aws configure + mount ~/.aws; AWS: attach IAM role with bedrock:InvokeModel",
        )
    yield
    logger.info("app_stopping")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_tagline,
        version=__version__,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    @app.middleware("http")
    async def correlation_and_security_headers(request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        path = request.url.path
        REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=failure(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                correlation_id=getattr(request.state, "correlation_id", None),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=failure(
                code="validation_error",
                message="Request validation failed",
                details={"errors": exc.errors()},
                correlation_id=getattr(request.state, "correlation_id", None),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=failure(
                code="http_error",
                message=str(exc.detail),
                correlation_id=getattr(request.state, "correlation_id", None),
            ),
        )

    # Health at root for Docker healthchecks
    @app.get("/health")
    async def root_health():
        return {"status": "ok", "app": settings.app_name}

    @app.get("/metrics")
    async def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    app.include_router(api_router, prefix=settings.api_prefix)
    # Also expose /health under API prefix via router
    return app


app = create_app()
