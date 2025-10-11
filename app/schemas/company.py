from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class CompanyBase(BaseModel):
    name: str
    registration_number: str
    bee_level: Optional[int] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    registration_number: Optional[str] = None
    bee_level: Optional[int] = None

class CompanyOut(CompanyBase):
    id: UUID
    created_at: datetime

    class Config:
        orm_mode = True
