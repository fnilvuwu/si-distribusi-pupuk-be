from datetime import datetime, timedelta
from jose import jwt
import bcrypt
from core.config import settings


def hash_password(password: str) -> str:
    # Bcrypt has a 72-byte limit, encode to bytes
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hash: str) -> bool:
    # Bcrypt has a 72-byte limit, encode to bytes
    password_bytes = password.encode("utf-8")
    hash_bytes = hash.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hash_bytes)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
