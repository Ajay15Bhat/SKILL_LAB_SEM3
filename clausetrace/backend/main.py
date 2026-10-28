"""
ClauseTrace Core Backend Application Entrypoint.
FastAPI REST API with interactive Swagger documentation.
"""

from pathlib import Path
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
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

# Detailed error handler to display exact causes in Swagger UI instead of opaque 500
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    err_trace = traceback.format_exc()
    print(f"\n[SERVER ERROR] {request.method} {request.url}: {exc}\n{err_trace}\n")
    return JSONResponse(
        status_code=500,
        content={
            "error_type": type(exc).__name__,
            "message": str(exc),
            "hint": "Check database connection or input parameters.",
        },
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


# Mount Static Frontend Assets
static_dir = Path(__file__).parent / "app" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/app", response_class=FileResponse, tags=["Frontend"])
async def serve_frontend_app():
    """Serves the ClauseTrace Forest Green & Bronze Visual Dashboard."""
    return FileResponse(static_dir / "index.html")


@app.get("/", tags=["Frontend"])
async def root():
    """Root endpoint serving the Visual Dashboard."""
    return FileResponse(static_dir / "index.html")


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint confirming API is running."""
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }

