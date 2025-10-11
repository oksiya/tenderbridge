from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import User
from app.utils.security import hash_password, verify_password, create_access_token
from app.schemas.auth import UserCreate, UserLogin, Token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    try:
        print(f"Attempting to hash password of length {len(user_data.password)} ({len(user_data.password.encode('utf-8'))} bytes)")
        password_hash = hash_password(user_data.password)
    except ValueError as exc:
        print(f"Password hashing error: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))

    new_user = User(email=user_data.email, password_hash=password_hash)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    token = create_access_token({"sub": new_user.email})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    try:
        ok = verify_password(user_data.password, user.password_hash)
    except ValueError as exc:
        # e.g. if incoming password is too long for bcrypt
        raise HTTPException(status_code=400, detail=str(exc))

    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}
