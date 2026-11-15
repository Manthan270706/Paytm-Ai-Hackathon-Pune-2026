import uuid
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError
from starlette.responses import Response

from app.api.v1.agent import router as agent_router
from app.api.v1.auth import router as auth_router
from app.api.v1.cases import router as cases_router
from app.api.v1.demo import router as demo_router
from app.api.v1.health import router as health_router
from app.api.v1.merchants import router as merchants_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.settlements import router as settlements_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.voice import router as voice_router
from app.api.v1.watchdog import router as watchdog_router
from app.api.v1.webhooks import router as webhooks_router
from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    OpsSaathiError,
    RateLimitError,
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationError,
)
from app.core.response import error_response

app = FastAPI(
    title="OpsSaathi AI API",
    version="1.1.0",
    description="Autonomous Merchant Operations Teammate for Paytm Merchants (Track 3)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
)


# ------------------------------------------------------------------------------
# Request ID Middleware
# ------------------------------------------------------------------------------
@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Callable[[Request], Any]) -> Response:
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = req_id
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


# ------------------------------------------------------------------------------
# CORS Restriction per PRD §13
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# Routers Mounted under /api/v1 per PRD §9
# ------------------------------------------------------------------------------
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(auth_router, prefix="/api/v1", tags=["Auth"])
app.include_router(merchants_router, prefix="/api/v1", tags=["Merchants"])
app.include_router(transactions_router, prefix="/api/v1", tags=["Transactions"])
app.include_router(settlements_router, prefix="/api/v1", tags=["Settlements"])
app.include_router(agent_router, prefix="/api/v1", tags=["Agent"])
app.include_router(voice_router, prefix="/api/v1", tags=["Voice"])
app.include_router(cases_router, prefix="/api/v1", tags=["Cases"])
app.include_router(demo_router, prefix="/api/v1", tags=["Demo"])
app.include_router(metrics_router, prefix="/api/v1", tags=["Metrics"])
app.include_router(watchdog_router, prefix="/api/v1", tags=["Watchdog"])
app.include_router(webhooks_router, prefix="/api/v1", tags=["Webhooks"])


@app.get("/")
async def root() -> dict:
    return {
        "name": "OpsSaathi AI API",
        "version": "1.1.0",
        "track": "Track 3: Autonomous AI Teammates",
        "docs": "/docs",
        "health": "/api/v1/health",
        "openapi": "/api/v1/openapi.json",
    }


# ------------------------------------------------------------------------------
# Exception Handlers Mapping Domain Errors to Standard Response Envelope
# ------------------------------------------------------------------------------
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=404,
        content=error_response(
            code="NOT_FOUND", message=exc.message, details=exc.details, request_id=req_id
        ),
    )


@app.exception_handler(ForbiddenError)
async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=403,
        content=error_response(
            code="FORBIDDEN", message=exc.message, details=exc.details, request_id=req_id
        ),
    )


@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=401,
        content=error_response(
            code="UNAUTHORIZED", message=exc.message, details=exc.details, request_id=req_id
        ),
    )


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=409,
        content=error_response(
            code="CONFLICT", message=exc.message, details=exc.details, request_id=req_id
        ),
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=400,
        content=error_response(
            code="VALIDATION_ERROR", message=exc.message, details=exc.details, request_id=req_id
        ),
    )


@app.exception_handler(RateLimitError)
async def rate_limit_handler(request: Request, exc: RateLimitError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=429,
        content=error_response(
            code="RATE_LIMITED", message=exc.message, details=exc.details, request_id=req_id
        ),
    )


@app.exception_handler(RequestValidationError)
async def pydantic_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=400,
        content=error_response(
            code="VALIDATION_ERROR",
            message="Request body or query parameter validation failed.",
            details=exc.errors(),
            request_id=req_id,
        ),
    )


@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_handler(
    request: Request, exc: ServiceUnavailableError
) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=503,
        content=error_response(
            code="SERVICE_UNAVAILABLE",
            message=exc.message,
            details=exc.details,
            request_id=req_id,
        ),
    )


@app.exception_handler(OperationalError)
async def db_operational_error_handler(
    request: Request, exc: OperationalError
) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=503,
        content=error_response(
            code="SERVICE_UNAVAILABLE",
            message="Database unavailable. Request could not be acknowledged or processed.",
            details={"service": "database"},
            request_id=req_id,
        ),
    )


@app.exception_handler(DBAPIError)
async def db_api_error_handler(request: Request, exc: DBAPIError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=503,
        content=error_response(
            code="SERVICE_UNAVAILABLE",
            message="Database connection error. Request could not be acknowledged or processed.",
            details={"service": "database"},
            request_id=req_id,
        ),
    )


@app.exception_handler(OpsSaathiError)
async def opssaathi_error_handler(request: Request, exc: OpsSaathiError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=400,
        content=error_response(
            code=exc.code, message=exc.message, details=exc.details, request_id=req_id
        ),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=500,
        content=error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred. Please try again or contact support.",
            details=str(exc) if settings.APP_ENV == "development" else None,
            request_id=req_id,
        ),
    )
