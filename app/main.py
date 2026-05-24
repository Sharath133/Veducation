"""
FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
import logging
from pathlib import Path

from app.config import settings
from app.database import engine, Base, ensure_postgres_database_exists
from app.api.v1 import (
    auth,
    user,
    duel,
    leaderboard,
    payment,
    rewards,
    referral,
    loyalty,
    pyqs,
    admin,
    support,
    feedback,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    logger.info("Starting up V Education API...")
    ensure_postgres_database_exists(settings.DATABASE_URL)
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    yield
    # Shutdown
    logger.info("Shutting down V Education API...")


# Create FastAPI app
app = FastAPI(
    title="V Education API",
    description="Quiz/Duel Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/api/v1/user", tags=["User"])
app.include_router(duel.router, prefix="/api/v1/duel", tags=["Duel"])
app.include_router(leaderboard.router, prefix="/api/v1/leaderboard", tags=["Leaderboard"])
app.include_router(payment.router, prefix="/api/v1/payment", tags=["Payment"])
app.include_router(rewards.router, prefix="/api/v1/rewards", tags=["Rewards"])
app.include_router(referral.router, prefix="/api/v1/referral", tags=["Referral"])
app.include_router(loyalty.router, prefix="/api/v1/loyalty", tags=["Loyalty"])
app.include_router(pyqs.router, prefix="/api/v1/pyqs", tags=["PYQs"])
app.include_router(support.router, prefix="/api/v1/support", tags=["Support"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["Feedback"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
upload_dir = Path(__file__).resolve().parents[1] / settings.UPLOAD_DIR
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount(f"/{settings.UPLOAD_DIR}", StaticFiles(directory=upload_dir), name="uploads")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "V Education API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    errors = exc.errors()
    logger.error(f"Validation error: {errors}, body: {await request.body()}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": f"Validation error: {errors[0].get('msg', 'Invalid request')}",
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

