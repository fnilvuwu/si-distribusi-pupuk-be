from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import logging

from core.config import settings
from db.db_base import get_db
from db.models import User

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except ValueError as e:
        logger.error(f"User ID conversion error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token format")

def require_role(*roles, optional=False):
    """
    Dependency to require specific roles.
    
    Args:
        roles: Allowed role names
        optional: If True, returns None instead of raising 401 when not authenticated
    """
    def checker(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
        if not token:
            if optional:
                return None
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if not user_id:
                if optional:
                    return None
                raise HTTPException(status_code=401, detail="Invalid token")

            user = db.query(User).filter(User.id == int(user_id)).first()
            if not user:
                if optional:
                    return None
                raise HTTPException(status_code=401, detail="User not found")
            
            if user.role not in roles:
                raise HTTPException(status_code=403, detail="Forbidden: insufficient permissions")
            
            return {"id": user.id, "username": user.username, "role": user.role}
        except JWTError as e:
            logger.error(f"JWT decode error in require_role: {str(e)}")
            if optional:
                return None
            raise HTTPException(status_code=401, detail="Invalid token")
        except ValueError as e:
            logger.error(f"Value error in require_role: {str(e)}")
            if optional:
                return None
            raise HTTPException(status_code=401, detail="Invalid token format")
    
    return checker
