from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode("utf-8")[:72]
    return pwd_context.hash(password_bytes)


def verify_password(password: str, hash: str) -> bool:
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode("utf-8")[:72]
    return pwd_context.verify(password_bytes, hash)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
