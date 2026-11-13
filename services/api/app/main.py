from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
from app.api.v1.webhooks import router as webhooks_router
from app.core.config import settings
from app.core.response import error_response

app = FastAPI(
    title="OpsSaathi AI API",
    version="1.1.0",
    description="Autonomous Merchant Operations Teammate for Paytm Merchants (Track 3)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
)

# CORS restriction
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include All Routers under /api/v1 per PRD §9
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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred. Please try again or contact support.",
            details=str(exc) if settings.APP_ENV == "development" else None,
        ),
    )
