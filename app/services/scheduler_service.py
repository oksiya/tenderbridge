"""
Scheduler Service for TenderBridge (Phase 3 - Task 2)

Manages scheduled jobs for:
- Tender deadline reminders
- Automated status transitions
- Report generation
- Email digests
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Tender, User, Bid, Notification
from app.services.notification_service import (
    NotificationType,
    create_notification
)

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Background job scheduler using APScheduler.
    Runs periodic tasks for tender management and notifications.
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.jobs = {}
    
    def start(self):
        """Start the scheduler and register all jobs."""
        if self.scheduler.running:
            logger.warning("Scheduler already running")
            return
        
        logger.info("Starting scheduler service...")
        
        # Register jobs
        self._register_deadline_reminder_job()
        self._register_status_transition_job()
        self._register_cleanup_job()
        
        # Start scheduler
        self.scheduler.start()
        logger.info(f"Scheduler started with {len(self.scheduler.get_jobs())} jobs")
    
    def stop(self):
        """Stop the scheduler."""
        if not self.scheduler.running:
            return
        
        logger.info("Stopping scheduler service...")
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    def _register_deadline_reminder_job(self):
        """
        Check for upcoming tender deadlines and send reminders.
        Runs every hour.
        """
        job = self.scheduler.add_job(
            func=self.check_tender_deadlines,
            trigger=IntervalTrigger(hours=1),
            id="tender_deadline_reminders",
            name="Tender Deadline Reminders",
            replace_existing=True
        )
        self.jobs["deadline_reminders"] = job
        logger.info("Registered job: tender_deadline_reminders (every 1 hour)")
    
    def _register_status_transition_job(self):
        """
        Automatically transition tender statuses based on dates.
        Runs every 5 minutes.
        """
        job = self.scheduler.add_job(
            func=self.auto_transition_tender_status,
            trigger=IntervalTrigger(minutes=5),
            id="tender_status_transitions",
            name="Tender Status Transitions",
            replace_existing=True
        )
        self.jobs["status_transitions"] = job
        logger.info("Registered job: tender_status_transitions (every 5 minutes)")
    
    def _register_cleanup_job(self):
        """
        Clean up old notifications and logs.
        Runs daily at 2 AM.
        """
        job = self.scheduler.add_job(
            func=self.cleanup_old_data,
            trigger=CronTrigger(hour=2, minute=0),
            id="cleanup_old_data",
            name="Cleanup Old Data",
            replace_existing=True
        )
        self.jobs["cleanup"] = job
        logger.info("Registered job: cleanup_old_data (daily at 2 AM)")
    
    def check_tender_deadlines(self):
        """
        Check for tenders approaching their deadline and send reminders.
        Sends reminders at: 1 week, 48 hours, 24 hours before closing.
        """
        logger.info("Running tender deadline reminder check...")
        db = SessionLocal()
        
        try:
            now = datetime.utcnow()
            
            # Define reminder windows
            reminder_windows = [
                (timedelta(days=7), "1 week"),
                (timedelta(hours=48), "48 hours"),
                (timedelta(hours=24), "24 hours"),
            ]
            
            for time_delta, label in reminder_windows:
                # Find tenders closing within this window
                target_time = now + time_delta
                window_start = target_time - timedelta(minutes=30)
                window_end = target_time + timedelta(minutes=30)
                
                tenders = db.query(Tender).filter(
                    Tender.status.in_(["open", "published"]),
                    Tender.closing_date >= window_start,
                    Tender.closing_date <= window_end
                ).all()
                
                for tender in tenders:
                    self._send_deadline_reminder(db, tender, label)
            
            db.commit()
            logger.info(f"Deadline reminder check complete")
            
        except Exception as e:
            logger.error(f"Error in deadline reminder check: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    def _send_deadline_reminder(self, db: Session, tender: Tender, time_remaining: str):
        """Send deadline reminder for a tender."""
        try:
            # Get all users from the company that posted the tender
            company_users = db.query(User).filter(
                User.company_id == tender.posted_by_id
            ).all()
            
            # Get all users who have submitted bids
            bidders = db.query(User).join(
                Bid, User.company_id == Bid.company_id
            ).filter(
                Bid.tender_id == tender.id
            ).distinct().all()
            
            # Combine and deduplicate
            all_users = list(set(company_users + bidders))
            
            for user in all_users:
                # Check if user already received this reminder
                existing = db.query(Notification).filter(
                    Notification.user_id == user.id,
                    Notification.related_tender_id == tender.id,
                    Notification.type == "tender_deadline_reminder",
                    Notification.message.contains(time_remaining)
                ).first()
                
                if not existing:
                    create_notification(
                        db=db,
                        user_id=user.id,
                        notification_type="tender_deadline_reminder",
                        title=f"⏰ Tender Deadline Approaching",
                        message=f"Tender '{tender.title}' closes in {time_remaining}. Don't miss the opportunity!",
                        related_tender_id=tender.id,
                        email_context={
                            "tender": {
                                "id": str(tender.id),
                                "title": tender.title,
                                "reference_number": tender.reference_number,
                                "closing_date": tender.closing_date.isoformat(),
                                "time_remaining": time_remaining
                            }
                        }
                    )
                    logger.info(f"Sent {time_remaining} deadline reminder for tender {tender.id} to user {user.id}")
        
        except Exception as e:
            logger.error(f"Error sending deadline reminder: {str(e)}")
    
    def auto_transition_tender_status(self):
        """
        Automatically transition tender statuses based on dates:
        - draft -> published (when publish_date is reached)
        - open/published -> closed (when closing_date is reached)
        """
        logger.info("Running auto status transition check...")
        db = SessionLocal()
        
        try:
            now = datetime.utcnow()
            
            # Transition draft -> published
            draft_tenders = db.query(Tender).filter(
                Tender.status == "draft",
                Tender.publish_date.isnot(None),
                Tender.publish_date <= now
            ).all()
            
            for tender in draft_tenders:
                tender.status = "published"
                logger.info(f"Auto-transitioned tender {tender.id} from draft to published")
                
                # Notify company users
                company_users = db.query(User).filter(
                    User.company_id == tender.posted_by_id
                ).all()
                
                for user in company_users:
                    create_notification(
                        db=db,
                        user_id=user.id,
                        notification_type=NotificationType.TENDER_PUBLISHED,
                        title="Tender Published",
                        message=f"Tender '{tender.title}' has been automatically published.",
                        related_tender_id=tender.id
                    )
            
            # Transition open/published -> closed
            open_tenders = db.query(Tender).filter(
                Tender.status.in_(["open", "published"]),
                Tender.closing_date <= now
            ).all()
            
            for tender in open_tenders:
                tender.status = "closed"
                logger.info(f"Auto-transitioned tender {tender.id} to closed")
                
                # Notify company users
                company_users = db.query(User).filter(
                    User.company_id == tender.posted_by_id
                ).all()
                
                for user in company_users:
                    create_notification(
                        db=db,
                        user_id=user.id,
                        notification_type=NotificationType.TENDER_CLOSED,
                        title="Tender Closed",
                        message=f"Tender '{tender.title}' has been automatically closed.",
                        related_tender_id=tender.id
                    )
            
            db.commit()
            logger.info(f"Auto-transitioned {len(draft_tenders)} draft and {len(open_tenders)} open tenders")
            
        except Exception as e:
            logger.error(f"Error in auto status transition: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    def cleanup_old_data(self):
        """
        Clean up old data:
        - Delete read notifications older than 90 days
        - Delete old email logs (optional, keep for audit)
        """
        logger.info("Running cleanup job...")
        db = SessionLocal()
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            # Delete old read notifications
            deleted = db.query(Notification).filter(
                Notification.is_read == "true",
                Notification.created_at < cutoff_date
            ).delete()
            
            db.commit()
            logger.info(f"Cleaned up {deleted} old notifications")
            
        except Exception as e:
            logger.error(f"Error in cleanup job: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    def get_job_status(self) -> List[dict]:
        """Get status of all scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs
    
    def trigger_job(self, job_id: str):
        """Manually trigger a job."""
        job = self.scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now())
            logger.info(f"Manually triggered job: {job_id}")
            return True
        return False


# Singleton instance
scheduler_service = SchedulerService()
