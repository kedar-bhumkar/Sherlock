"""Sherlock API - Image Knowledge Extraction System."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from exceptions.base import AppException
from settings.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings = get_settings()
    if settings.debug:
        print("Starting Sherlock API in debug mode...")
    yield
    # Shutdown
    if settings.debug:
        print("Shutting down Sherlock API...")


app = FastAPI(
    title="Sherlock API",
    description="Image Knowledge Extraction System",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "sherlock-api"}


# Import and include routers after app is created to avoid circular imports
from api.routes import ingest, knowledge, config, auth, images, mcp

app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(ingest.router, prefix="/api", tags=["Ingestion"])
app.include_router(knowledge.router, prefix="/api", tags=["Knowledge"])
app.include_router(config.router, prefix="/api", tags=["Config"])
app.include_router(images.router, prefix="/api", tags=["Images"])
app.include_router(mcp.router, prefix="/api", tags=["MCP"])
