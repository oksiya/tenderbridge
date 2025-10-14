from pydantic import BaseModel
from typing import Optional


class UserRoleUpdate(BaseModel):
    role: str  # admin, company_admin, tender_manager, evaluator, user


class EmailPreferencesUpdate(BaseModel):
    """Schema for updating user email preferences (Phase 3)"""
    email_notifications: Optional[str] = None  # true, false
    email_frequency: Optional[str] = None  # immediate, daily, weekly, never


class EmailPreferencesOut(BaseModel):
    """Schema for email preferences response"""
    email_notifications: str
    email_frequency: str
    
    class Config:
        from_attributes = True


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


# Phase 3: Email Preferences
class EmailPreferencesUpdate(BaseModel):
    email_notifications: Optional[str] = None  # "true" or "false"
    email_frequency: Optional[str] = None  # "immediate", "daily", "weekly", "never"


class EmailPreferencesOut(BaseModel):
    email_notifications: str
    email_frequency: str
