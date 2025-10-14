from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

# ------------------------
# Tender Schemas
# ------------------------
class TenderBase(BaseModel):
    title: str
    description: str
    closing_date: datetime

class TenderCreate(TenderBase):
    pass  # posted_by_id will come from current_user


class TenderUpdate(BaseModel):
    """Schema for updating tender details (only in draft/published state)"""
    title: Optional[str] = None
    description: Optional[str] = None
    closing_date: Optional[datetime] = None


class TenderStatusUpdate(BaseModel):
    """Schema for updating tender status"""
    status: str
    reason: Optional[str] = None  # Required for cancellation


class TenderOut(TenderBase):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    status_updated_at: datetime
    posted_by_id: UUID
    document_path: Optional[str] = None
    
    # Cancellation fields
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    cancelled_by_id: Optional[UUID] = None
    
    # Award-related fields (only populated when awarded)
    awarded_at: Optional[datetime] = None
    winning_bid_id: Optional[UUID] = None
    award_chain_tx: Optional[str] = None
    award_hash_on_chain: Optional[str] = None
    award_justification: Optional[str] = None

    class Config:
        orm_mode = True


class AwardTenderRequest(BaseModel):
    """Request schema for awarding a tender to a winning bid"""
    winning_bid_id: UUID
    justification: str  # Mandatory justification for award decision


class AwardVerification(BaseModel):
    """Response schema for award verification"""
    tender_id: str
    verified: bool
    winning_bid_id: Optional[str] = None
    winning_company_id: Optional[str] = None
    award_amount: Optional[int] = None
    award_date: Optional[int] = None
    awarded_by: Optional[str] = None
    hash_on_chain: Optional[str] = None
    method: Optional[str] = None

# ------------------------
# Bid Schemas
# ------------------------
class BidBase(BaseModel):
    tender_id: UUID
    company_id: UUID
    amount: float

class BidCreate(BidBase):
    document_path: Optional[str] = None  # optional file path for bid attachments

class BidOut(BidBase):
    id: UUID
    submitted_at: datetime
    # Optional: status if you want to track bid acceptance
    status: Optional[str] = "pending"

    class Config:
        orm_mode = True
