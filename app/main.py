from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from app.db.session import Base, engine
from app.api import auth, company, tender, bids, users, notifications, admin_jobs, qa, documents
from app.services.scheduler_service import scheduler_service
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting TenderBridge API...")
    try:
        scheduler_service.start()
        logger.info("Scheduler service started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down TenderBridge API...")
    try:
        scheduler_service.stop()
        logger.info("Scheduler service stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {str(e)}")


app = FastAPI(
    title="TenderBridge API",
    lifespan=lifespan
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(auth.router)
app.include_router(company.router)
app.include_router(tender.router)
app.include_router(bids.router)
app.include_router(users.router)
app.include_router(notifications.router)
app.include_router(admin_jobs.router)
app.include_router(qa.router)
app.include_router(documents.router)

@app.get("/")
@limiter.limit("60/minute")
def root(request: Request):
    return {"message": "Welcome to TenderBridge API - Phase 4 Production Ready"}

@app.get("/health")
@limiter.limit("200/minute")  # Allow more for monitoring
def health_check(request: Request):
    """Health check endpoint with scheduler status."""
    scheduler_jobs = scheduler_service.get_job_status()
    return {
        "status": "healthy",
        "scheduler": {
            "running": scheduler_service.scheduler.running,
            "jobs": scheduler_jobs
        }
    }



