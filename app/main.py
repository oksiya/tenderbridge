from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.session import Base, engine
from app.api import auth, company, tender, bids, users, notifications, admin_jobs, qa, documents
from app.services.scheduler_service import scheduler_service
import logging

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)


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
def root():
    return {"message": "Welcome to TenderBridge API - Phase 3"}

@app.get("/health")
def health_check():
    """Health check endpoint with scheduler status."""
    scheduler_jobs = scheduler_service.get_job_status()
    return {
        "status": "healthy",
        "scheduler": {
            "running": scheduler_service.scheduler.running,
            "jobs": scheduler_jobs
        }
    }



