import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from api.router import api_router
from db.db_base import close_all_connections, init_connection_pool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database connection pool...")
    init_connection_pool()
    logger.info("Backend API Services for Sistem Distribusi Pupuk Gratis is running")
    yield
    logger.info("Closing database connections...")
    close_all_connections()


app = FastAPI(
    title="SIPUPUK API",
    version="1.0.0",
    description="API Backend Service for Sistem Informasi Distribusi Pupuk Gratis",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Auth", "description": "Authentication routes"},
        {"name": "Petani", "description": "Petani routes"},
        {"name": "Distributor", "description": "Distributor routes"},
        {"name": "Admin", "description": "Admin routes"},
        {"name": "Super Admin", "description": "Super Admin routes"},
    ],
)

# CORS configuration - restrict in production
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://jti-si-distribusi-pupuk-fe.vercel.app").split(",")
if os.getenv("ENVIRONMENT") == "production":
    # In production, MUST specify allowed origins explicitly
    logger.warning("CORS_ORIGINS in production: %s", CORS_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(api_router)

# Serve uploaded files
# In serverless/production environments, use /tmp (read-write allowed)
# In development, use local uploads directory
if os.getenv("ENVIRONMENT") == "production" or os.getenv("VERCEL"):
    UPLOAD_DIR = Path("/tmp/uploads")
else:
    UPLOAD_DIR = Path("uploads")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}
