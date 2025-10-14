"""
Admin API for Scheduled Jobs (Phase 3 - Task 2)

Endpoints for managing and monitoring scheduled jobs.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.core.deps import get_current_user, get_db
from app.db.models import User
from app.services.scheduler_service import scheduler_service
from app.utils.permissions import require_role

router = APIRouter(prefix="/api/admin/jobs", tags=["admin", "jobs"])


class JobStatus(BaseModel):
    """Job status response."""
    id: str
    name: str
    next_run: str | None
    trigger: str


class JobTriggerRequest(BaseModel):
    """Request to manually trigger a job."""
    job_id: str


@router.get("/", response_model=List[JobStatus])
def list_scheduled_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all scheduled jobs with their status.
    Admin only.
    """
    require_role(current_user, ["admin"])
    
    jobs = scheduler_service.get_job_status()
    return jobs


@router.post("/trigger")
def trigger_job(
    request: JobTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger a scheduled job.
    Admin only.
    """
    require_role(current_user, ["admin"])
    
    success = scheduler_service.trigger_job(request.job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"message": f"Job {request.job_id} triggered successfully"}


@router.get("/health")
def scheduler_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get scheduler health status.
    Admin only.
    """
    require_role(current_user, ["admin"])
    
    return {
        "scheduler_running": scheduler_service.scheduler.running,
        "total_jobs": len(scheduler_service.scheduler.get_jobs()),
        "jobs": scheduler_service.get_job_status()
    }


@router.post("/deadline-reminders/run")
def run_deadline_reminders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually run deadline reminder check.
    Admin only.
    """
    require_role(current_user, ["admin"])
    
    try:
        scheduler_service.check_tender_deadlines()
        return {"message": "Deadline reminder check completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/status-transitions/run")
def run_status_transitions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually run status transition check.
    Admin only.
    """
    require_role(current_user, ["admin"])
    
    try:
        scheduler_service.auto_transition_tender_status()
        return {"message": "Status transition check completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
