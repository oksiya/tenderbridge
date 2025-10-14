# app/schemas/bid.py
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class BidBase(BaseModel):
    tender_id: UUID
    company_id: UUID
    amount: Decimal

class BidCreate(BidBase):
    # For file upload we will use form/file so this schema is for JSON use-cases
    document_path: Optional[str] = None


class BidUpdate(BaseModel):
    """Schema for revising a bid"""
    amount: Optional[Decimal] = None
    document_path: Optional[str] = None


class BidWithdrawal(BaseModel):
    """Schema for withdrawing a bid"""
    reason: str


class BidOut(BidBase):
    id: UUID
    document_path: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    
    # Withdrawal fields
    withdrawn_at: Optional[datetime] = None
    withdrawal_reason: Optional[str] = None
    
    # Revision tracking
    revision_number: int
    parent_bid_id: Optional[UUID] = None

    class Config:
        orm_mode = True
        from_attributes = True


class BidStatusUpdate(BaseModel):
    status: str  # expected: pending, shortlisted, accepted, rejected, withdrawn
