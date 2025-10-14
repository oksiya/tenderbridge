"""
Role-based access control utilities
"""
from fastapi import HTTPException
from app.db.models import User

# Role hierarchy
ROLES = {
    "admin": 100,           # Full system access
    "company_admin": 80,    # Manage company users and settings
    "tender_manager": 60,   # Create/manage tenders, award decisions
    "evaluator": 40,        # Score and evaluate bids
    "user": 20              # Basic bidding capabilities
}


def has_role(user: User, required_role: str) -> bool:
    """Check if user has required role or higher"""
    user_level = ROLES.get(user.role, 0)
    required_level = ROLES.get(required_role, 0)
    return user_level >= required_level


def require_role(user: User, required_role: str):
    """Raise exception if user doesn't have required role"""
    if not has_role(user, required_role):
        raise HTTPException(
            status_code=403,
            detail=f"Requires {required_role} role or higher"
        )


def is_admin(user: User) -> bool:
    """Check if user is admin"""
    return user.role == "admin"


def is_company_admin(user: User) -> bool:
    """Check if user is company admin"""
    return user.role in ["admin", "company_admin"]


def is_tender_manager(user: User) -> bool:
    """Check if user can manage tenders"""
    return user.role in ["admin", "company_admin", "tender_manager"]


def is_evaluator(user: User) -> bool:
    """Check if user can evaluate bids"""
    return user.role in ["admin", "company_admin", "tender_manager", "evaluator"]


def can_manage_company(user: User, company_id) -> bool:
    """Check if user can manage a specific company"""
    if is_admin(user):
        return True
    if user.role == "company_admin" and user.company_id == company_id:
        return True
    return False


def can_create_tender(user: User) -> bool:
    """Check if user can create tenders"""
    return is_tender_manager(user) and user.company_id is not None


def can_award_tender(user: User, tender_posted_by_id) -> bool:
    """Check if user can award a tender"""
    if is_admin(user):
        return True
    if is_tender_manager(user) and user.company_id == tender_posted_by_id:
        return True
    return False


def can_submit_bid(user: User) -> bool:
    """Check if user can submit bids"""
    return user.company_id is not None
