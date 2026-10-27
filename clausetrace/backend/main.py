"""
ClauseTrace Core Backend Application Entrypoint.
FastAPI REST API with interactive Swagger documentation.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.approvals import router as approvals_router
from app.api.audit import router as audit_router
from app.api.contracts import router as contracts_router
from app.api.diff import router as diff_router
from app.api.requirements import router as requirements_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Evidence-Grounded Contract Review and Change-Impact Platform.\n\n"
        "Core Capabilities:\n"
        "- Immutable Versioning with SHA-256 fingerprinting\n"
        "- Page-aware clause segmentation (PyMuPDF)\n"
        "- Deterministic Full-Text Search (PostgreSQL tsvector) + Gemini Flash reasoning\n"
        "- Deterministic clause diffing and automated requirement impact analysis\n"
        "- Version-tied approval state machine and tamper-proof audit trail"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration for Next.js Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(contracts_router, prefix=settings.API_V1_STR)
app.include_router(requirements_router, prefix=settings.API_V1_STR)
app.include_router(diff_router, prefix=settings.API_V1_STR)
app.include_router(approvals_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint confirming API is running."""
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint redirecting to interactive documentation."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "documentation": "/docs",
        "version": "1.0.0",
    }

