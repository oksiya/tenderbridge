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

class BidOut(BidBase):
    id: UUID
    document_path: Optional[str]
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

class BidStatusUpdate(BaseModel):
    status: str  # expected: "pending" | "accepted" | "rejected"
