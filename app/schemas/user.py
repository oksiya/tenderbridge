from pydantic import BaseModel
from typing import Optional


class UserRoleUpdate(BaseModel):
    role: str  # admin, company_admin, tender_manager, evaluator, user


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    company_id: Optional[str]
    is_verified: str
    created_at: str
    
    class Config:
        from_attributes = True
