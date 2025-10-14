from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.session import get_db
from app.db.models import User
from app.schemas.user import UserRoleUpdate, UserOut, EmailPreferencesUpdate, EmailPreferencesOut
from app.core.deps import get_current_user
from app.utils.permissions import is_admin, is_company_admin, ROLES

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role,
        "company_id": str(current_user.company_id) if current_user.company_id else None,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat()
    }


@router.put("/{user_id}/role")
def update_user_role(
    user_id: UUID,
    role_update: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a user's role.
    Only admins can assign any role.
    Company admins can assign roles within their company (except admin).
    """
    # Validate role
    if role_update.role not in ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(ROLES.keys())}"
        )
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Authorization checks
    if not is_admin(current_user):
        # Company admins can only manage users in their company
        if not is_company_admin(current_user):
            raise HTTPException(
                status_code=403,
                detail="Only admins or company admins can assign roles"
            )
        
        # Company admin restrictions
        if current_user.company_id != target_user.company_id:
            raise HTTPException(
                status_code=403,
                detail="You can only manage users in your company"
            )
        
        if role_update.role == "admin":
            raise HTTPException(
                status_code=403,
                detail="Only system admins can assign admin role"
            )
    
    # Update role
    old_role = target_user.role
    target_user.role = role_update.role
    db.commit()
    
    return {
        "message": f"User role updated from {old_role} to {role_update.role}",
        "user_id": str(user_id),
        "old_role": old_role,
        "new_role": role_update.role
    }


@router.get("/", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List users.
    Admins see all users.
    Company admins see users in their company.
    """
    if is_admin(current_user):
        users = db.query(User).all()
    elif is_company_admin(current_user):
        if not current_user.company_id:
            raise HTTPException(status_code=400, detail="User not assigned to a company")
        users = db.query(User).filter(User.company_id == current_user.company_id).all()
    else:
        raise HTTPException(
            status_code=403,
            detail="Only admins or company admins can list users"
        )
    
    return [
        {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "company_id": str(user.company_id) if user.company_id else None,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat()
        }
        for user in users
    ]


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user details by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Authorization: users can see themselves, admins can see all, company admins can see their company
    if str(current_user.id) == str(user_id):
        pass  # User can see themselves
    elif is_admin(current_user):
        pass  # Admin can see all
    elif is_company_admin(current_user) and current_user.company_id == user.company_id:
        pass  # Company admin can see their company users
    else:
        raise HTTPException(status_code=403, detail="Not authorized to view this user")
    
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "company_id": str(user.company_id) if user.company_id else None,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat()
    }


@router.get("/me/email-preferences", response_model=EmailPreferencesOut)
def get_email_preferences(current_user: User = Depends(get_current_user)):
    """Get current user's email notification preferences (Phase 3)"""
    return {
        "email_notifications": current_user.email_notifications or "true",
        "email_frequency": current_user.email_frequency or "immediate"
    }


@router.put("/me/email-preferences", response_model=EmailPreferencesOut)
def update_email_preferences(
    preferences: EmailPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update email notification preferences (Phase 3).
    
    - email_notifications: 'true' or 'false' (enable/disable all emails)
    - email_frequency: 'immediate', 'daily', 'weekly', or 'never'
    """
    # Validate values
    if preferences.email_notifications and preferences.email_notifications not in ["true", "false"]:
        raise HTTPException(
            status_code=400,
            detail="email_notifications must be 'true' or 'false'"
        )
    
    if preferences.email_frequency and preferences.email_frequency not in ["immediate", "daily", "weekly", "never"]:
        raise HTTPException(
            status_code=400,
            detail="email_frequency must be 'immediate', 'daily', 'weekly', or 'never'"
        )
    
    # Update preferences
    if preferences.email_notifications is not None:
        current_user.email_notifications = preferences.email_notifications
    
    if preferences.email_frequency is not None:
        current_user.email_frequency = preferences.email_frequency
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "email_notifications": current_user.email_notifications,
        "email_frequency": current_user.email_frequency
    }
