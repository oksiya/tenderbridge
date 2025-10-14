from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
from app.db.session import get_db
from app.db.models import User
from app.utils.security import hash_password, verify_password, create_access_token
from app.schemas.auth import (
    UserCreate, UserLogin, Token, EmailVerificationRequest,
    ResendVerificationRequest, ForgotPasswordRequest, ResetPasswordRequest
)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with email verification required"""
    user = db.query(User).filter(User.email == user_data.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    try:
        print(f"Attempting to hash password of length {len(user_data.password)} ({len(user_data.password.encode('utf-8'))} bytes)")
        password_hash = hash_password(user_data.password)
    except ValueError as exc:
        print(f"Password hashing error: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))

    # Generate verification token
    verification_token = secrets.token_urlsafe(32)
    
    new_user = User(
        email=user_data.email, 
        password_hash=password_hash,
        verification_token=verification_token,
        is_verified="false"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # TODO: Send verification email with token
    print(f"📧 Verification token for {user_data.email}: {verification_token}")
    print(f"Verification URL: /auth/verify-email?token={verification_token}")
    
    token = create_access_token({"sub": str(new_user.id)})
    return {
        "access_token": token, 
        "token_type": "bearer", 
        "user_id": str(new_user.id)
    }

@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login with email/password - returns access token"""
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    try:
        ok = verify_password(user_data.password, user.password_hash)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user_id": str(user.id)}


@router.post("/verify-email")
def verify_email(request: EmailVerificationRequest, db: Session = Depends(get_db)):
    """Verify user email with verification token"""
    user = db.query(User).filter(User.verification_token == request.token).first()
    
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token"
        )
    
    if user.is_verified == "true":
        return {"message": "Email already verified"}
    
    user.is_verified = "true"
    user.verification_token = None  # Clear the token after use
    db.commit()
    
    return {
        "message": "Email verified successfully",
        "user_id": str(user.id),
        "email": user.email
    }


@router.post("/resend-verification")
def resend_verification(request: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Resend verification email"""
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_verified == "true":
        raise HTTPException(status_code=400, detail="Email already verified")
    
    # Generate new verification token
    verification_token = secrets.token_urlsafe(32)
    user.verification_token = verification_token
    db.commit()
    
    # TODO: Send verification email
    print(f"📧 New verification token for {request.email}: {verification_token}")
    print(f"Verification URL: /auth/verify-email?token={verification_token}")
    
    return {"message": "Verification email sent"}


@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request password reset token"""
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        # Return success even if user not found (security best practice)
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token (valid for 1 hour)
    reset_token = secrets.token_urlsafe(32)
    user.reset_token = reset_token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    
    # TODO: Send password reset email
    print(f"🔐 Password reset token for {request.email}: {reset_token}")
    print(f"Reset URL: /auth/reset-password?token={reset_token}")
    print(f"Expires at: {user.reset_token_expires}")
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using reset token"""
    user = db.query(User).filter(User.reset_token == request.token).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Check if token is expired
    if user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")
    
    # Hash new password
    try:
        new_password_hash = hash_password(request.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    
    # Update password and clear reset token
    user.password_hash = new_password_hash
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    
    return {
        "message": "Password reset successfully",
        "user_id": str(user.id)
    }
