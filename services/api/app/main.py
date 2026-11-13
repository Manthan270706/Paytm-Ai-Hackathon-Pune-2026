from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.health import router as health_router
from app.core.config import settings
from app.core.response import error_response

app = FastAPI(
    title="OpsSaathi AI API",
    version="1.1.0",
    description="Autonomous Merchant Operations Teammate for Paytm Merchants (Track 3)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json"
)

# CORS restriction
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health_router, prefix="/api/v1", tags=["Health"])


@app.get("/")
async def root() -> dict:
    return {
        "name": "OpsSaathi AI API",
        "version": "1.1.0",
        "track": "Track 3: Autonomous AI Teammates",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred. Please try again or contact support.",
            details=str(exc) if settings.APP_ENV == "development" else None
        )
    )
