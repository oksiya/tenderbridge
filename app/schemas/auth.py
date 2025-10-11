from pydantic import BaseModel, EmailStr, validator

# bcrypt limit in bytes
MAX_BCRYPT_BYTES = 72


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @validator("password")
    def password_byte_length(cls, v: str):
        if v is None:
            raise ValueError("password must be provided")
        encoded = v.encode("utf-8")
        print(f"UserCreate Validator: Password length is {len(v)} chars ({len(encoded)} bytes)")
        if len(encoded) > MAX_BCRYPT_BYTES:
            # Truncate to valid UTF-8 boundary up to MAX_BCRYPT_BYTES
            v = encoded[:MAX_BCRYPT_BYTES].decode('utf-8', errors='ignore')
            print(f"UserCreate Validator: Truncated to {len(v)} chars ({len(v.encode('utf-8'))} bytes)")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @validator("password")
    def password_byte_length(cls, v: str):
        if v is None:
            raise ValueError("password must be provided")
        encoded = v.encode("utf-8")
        if len(encoded) > MAX_BCRYPT_BYTES:
            # Truncate to valid UTF-8 boundary up to MAX_BCRYPT_BYTES
            v = encoded[:MAX_BCRYPT_BYTES].decode('utf-8', errors='ignore')
        return v


class Token(BaseModel):
    access_token: str
    token_type: str
