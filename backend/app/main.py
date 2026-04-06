"""
AutoCloud Architect - FastAPI Main Application
"""
# Fix SSL certificates — use certifi's CA bundle instead of potentially
# outdated system certificates (critical on Python 3.14 / Windows)
import os
try:
    import certifi
    os.environ.setdefault('AWS_CA_BUNDLE', certifi.where())
    os.environ.setdefault('SSL_CERT_FILE', certifi.where())
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import get_settings
from app.api.routes import router as api_router
from app.api.websocket import router as ws_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("🚀 Starting AutoCloud Architect Backend...")
    logger.info(f"📡 SageMaker Endpoint: {settings.sagemaker_endpoint_name}")
    logger.info(f"🌍 Region: {settings.aws_default_region}")
    yield
    logger.info("👋 Shutting down AutoCloud Architect Backend...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Intelligent AWS Infrastructure Recommendation and Automated Deployment System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix=f"/api/{settings.api_version}")
app.include_router(ws_router, prefix="/ws")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name
    }
