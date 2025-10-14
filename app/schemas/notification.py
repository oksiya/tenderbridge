from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class NotificationCreate(BaseModel):
    """Schema for creating a notification"""
    user_id: UUID
    type: str
    title: str
    message: str
    related_tender_id: Optional[UUID] = None
    related_bid_id: Optional[UUID] = None


class NotificationOut(BaseModel):
    """Schema for notification response"""
    id: UUID
    user_id: UUID
    type: str
    title: str
    message: str
    related_tender_id: Optional[UUID]
    related_bid_id: Optional[UUID]
    is_read: str
    created_at: datetime
    read_at: Optional[datetime]
    
    class Config:
        orm_mode = True
        from_attributes = True


class NotificationMarkRead(BaseModel):
    """Schema for marking notifications as read"""
    notification_ids: list[UUID]
