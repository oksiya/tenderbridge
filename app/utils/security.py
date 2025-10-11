import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from app.core.config import settings

# Bcrypt has a 72-byte input limit
MAX_BCRYPT_BYTES = 72

def hash_password(password: str) -> str:
    if password is None:
        raise ValueError("password must be provided")
    
    # encode to bytes using utf-8
    pw_bytes = password.encode("utf-8")
    
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(pw_bytes, salt)
    
    # Return the hash as a string
    return password_hash.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pw_bytes = plain_password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(pw_bytes, hash_bytes)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
