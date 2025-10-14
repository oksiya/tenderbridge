from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from typing import List

from app.db.session import get_db
from app.db.models import Notification
from app.schemas.notification import NotificationOut, NotificationMarkRead
from app.core.deps import get_current_user
from app.utils.pagination import PaginationParams, create_paginated_response, paginate_query

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/")
def list_notifications(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    unread_only: bool = False
):
    """
    Get all notifications for the current user with pagination
    Optionally filter for unread notifications only.
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    query = query.order_by(Notification.created_at.desc())
    items, total = paginate_query(query, pagination.skip, pagination.limit)
    return create_paginated_response(items, total, pagination.skip, pagination.limit)


@router.get("/unread/count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get count of unread notifications"""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == "false"
    ).count()
    
    return {"unread_count": count}


@router.post("/mark-read")
def mark_notifications_read(
    payload: NotificationMarkRead,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Mark one or more notifications as read"""
    notifications = db.query(Notification).filter(
        Notification.id.in_(payload.notification_ids),
        Notification.user_id == current_user.id
    ).all()
    
    if not notifications:
        raise HTTPException(status_code=404, detail="No matching notifications found")
    
    for notification in notifications:
        if notification.is_read == "false":
            notification.is_read = "true"
            notification.read_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": f"Marked {len(notifications)} notification(s) as read",
        "count": len(notifications)
    }


@router.post("/mark-all-read")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Mark all notifications as read for current user"""
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == "false"
    ).all()
    
    for notification in notifications:
        notification.is_read = "true"
        notification.read_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": f"Marked {len(notifications)} notification(s) as read",
        "count": len(notifications)
    }


@router.get("/{notification_id}", response_model=NotificationOut)
def get_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get a specific notification by ID"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Auto-mark as read when viewed
    if notification.is_read == "false":
        notification.is_read = "true"
        notification.read_at = datetime.utcnow()
        db.commit()
    
    return notification
