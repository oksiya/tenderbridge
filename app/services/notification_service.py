"""
Notification Service - Create and manage user notifications
"""
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import logging

from app.db.models import Notification, User, Tender, Company, Bid
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


class NotificationType:
    """Notification type constants"""
    TENDER_PUBLISHED = "tender_published"
    TENDER_CLOSED = "tender_closed"
    TENDER_CANCELLED = "tender_cancelled"
    TENDER_AWARDED = "tender_awarded"
    TENDER_DEADLINE_REMINDER = "tender_deadline_reminder"  # Phase 3
    TENDER_STATUS_CHANGED = "tender_status_changed"
    BID_SUBMITTED = "bid_submitted"
    BID_ACCEPTED = "bid_accepted"
    BID_REJECTED = "bid_rejected"
    BID_WITHDRAWN = "bid_withdrawn"
    QUESTION_ASKED = "question_asked"  # Phase 3 - Q&A
    QUESTION_ANSWERED = "question_answered"  # Phase 3 - Q&A


def create_notification(
    db: Session,
    user_id: UUID,
    notification_type: str,
    title: str,
    message: str,
    related_tender_id: Optional[UUID] = None,
    related_bid_id: Optional[UUID] = None,
    email_context: Optional[Dict[str, Any]] = None
) -> Notification:
    """
    Create a new notification for a user and send email if enabled.
    
    Args:
        db: Database session
        user_id: ID of user to notify
        notification_type: Type of notification (use NotificationType constants)
        title: Short notification title
        message: Detailed notification message
        related_tender_id: Optional tender ID for context
        related_bid_id: Optional bid ID for context
        email_context: Optional additional context for email template
    
    Returns:
        Created Notification object
    """
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        related_tender_id=related_tender_id,
        related_bid_id=related_bid_id
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    # Send email notification (async, don't wait for it)
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.email:
        # Check user's email preferences
        should_send_email = user.email_notifications == "true"
        
        if should_send_email:
            # Gather related data for email template
            related_data = email_context or {}
            
            # Add tender details if available
            if related_tender_id and "tender" not in related_data:
                tender = db.query(Tender).filter(Tender.id == related_tender_id).first()
                if tender:
                    related_data["tender"] = {
                        "id": str(tender.id),
                        "title": tender.title,
                        "description": tender.description,
                        "reference_number": tender.reference_number,
                        "status": tender.status
                    }
            
            # Add bid details if available
            if related_bid_id and "bid" not in related_data:
                bid = db.query(Bid).filter(Bid.id == related_bid_id).first()
                if bid:
                    related_data["bid"] = {
                        "id": str(bid.id),
                        "amount": float(bid.amount),
                        "status": bid.status
                    }
            
            # Send email asynchronously (fire and forget)
            try:
                asyncio.create_task(
                    email_service.send_notification_email(
                        user_email=user.email,
                        notification_type=notification_type,
                        title=title,
                        message=message,
                        related_data=related_data,
                        user_id=user.id,
                        notification_id=notification.id
                    )
                )
                logger.info(f"Queued email for notification {notification.id} to {user.email}")
            except Exception as e:
                logger.error(f"Failed to queue email for notification {notification.id}: {str(e)}")
    
    return notification


def notify_company_users(
    db: Session,
    company_id: UUID,
    notification_type: str,
    title: str,
    message: str,
    related_tender_id: Optional[UUID] = None,
    related_bid_id: Optional[UUID] = None,
    exclude_user_id: Optional[UUID] = None
) -> List[Notification]:
    """
    Create notifications for all users in a company.
    
    Args:
        db: Database session
        company_id: ID of company whose users to notify
        notification_type: Type of notification
        title: Short notification title
        message: Detailed notification message
        related_tender_id: Optional tender ID
        related_bid_id: Optional bid ID
        exclude_user_id: Optional user ID to exclude from notifications
    
    Returns:
        List of created Notification objects
    """
    users = db.query(User).filter(User.company_id == company_id).all()
    
    notifications = []
    for user in users:
        if exclude_user_id and user.id == exclude_user_id:
            continue
        
        notification = create_notification(
            db=db,
            user_id=user.id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_tender_id=related_tender_id,
            related_bid_id=related_bid_id
        )
        notifications.append(notification)
    
    return notifications


def notify_tender_published(
    db: Session,
    tender: Tender,
    published_by_user: User
):
    """
    Notify company users when a tender is published.
    Excludes the user who published it.
    """
    return notify_company_users(
        db=db,
        company_id=tender.posted_by_id,
        notification_type=NotificationType.TENDER_PUBLISHED,
        title="Tender Published",
        message=f"Tender '{tender.title}' has been published and is now open for bids.",
        related_tender_id=tender.id,
        exclude_user_id=published_by_user.id
    )


def notify_tender_awarded(
    db: Session,
    tender: Tender,
    winning_company_id: UUID,
    losing_company_ids: List[UUID]
):
    """
    Notify winning and losing bidders about tender award.
    """
    # Notify winning company
    notify_company_users(
        db=db,
        company_id=winning_company_id,
        notification_type=NotificationType.BID_ACCEPTED,
        title="🎉 Bid Accepted!",
        message=f"Congratulations! Your bid for tender '{tender.title}' has been accepted.",
        related_tender_id=tender.id
    )
    
    # Notify losing companies
    for company_id in losing_company_ids:
        notify_company_users(
            db=db,
            company_id=company_id,
            notification_type=NotificationType.BID_REJECTED,
            title="Bid Not Selected",
            message=f"Your bid for tender '{tender.title}' was not selected. Thank you for participating.",
            related_tender_id=tender.id
        )


def notify_tender_status_changed(
    db: Session,
    tender: Tender,
    old_status: str,
    new_status: str,
    changed_by_user: User
):
    """
    Notify company users when tender status changes.
    """
    status_messages = {
        "published": "The tender has been published.",
        "open": "The tender is now open for bid submissions.",
        "evaluation": "The tender is now under evaluation.",
        "closed": "The tender has been closed for submissions.",
        "cancelled": "The tender has been cancelled.",
        "awarded": "The tender has been awarded."
    }
    
    message = f"Tender '{tender.title}' status changed from '{old_status}' to '{new_status}'. {status_messages.get(new_status, '')}"
    
    return notify_company_users(
        db=db,
        company_id=tender.posted_by_id,
        notification_type=NotificationType.TENDER_STATUS_CHANGED,
        title=f"Tender Status: {new_status.title()}",
        message=message,
        related_tender_id=tender.id,
        exclude_user_id=changed_by_user.id
    )


def notify_bid_submitted(
    db: Session,
    tender: Tender,
    bid_company_id: UUID
):
    """
    Notify tender owner when a new bid is submitted.
    """
    company = db.query(Company).filter(Company.id == bid_company_id).first()
    company_name = company.name if company else "A company"
    
    return notify_company_users(
        db=db,
        company_id=tender.posted_by_id,
        notification_type=NotificationType.BID_SUBMITTED,
        title="New Bid Received",
        message=f"{company_name} has submitted a bid for tender '{tender.title}'.",
        related_tender_id=tender.id
    )
