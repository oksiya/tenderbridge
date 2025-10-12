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
    posted_by_id: UUID

class TenderOut(TenderBase):
    id: UUID
    status: str
    created_at: datetime
    posted_by_id: UUID
    document_path: Optional[str] = None

    class Config:
        orm_mode = True

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
