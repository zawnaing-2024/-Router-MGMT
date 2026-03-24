from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import hashlib
import secrets

from app.core.database import get_db
from app.models import APIToken, User
from pydantic import BaseModel

router = APIRouter(prefix="/api-tokens", tags=["API Tokens"])


class APITokenCreate(BaseModel):
    name: str
    permissions: str = "read"
    expires_days: Optional[int] = None


class APITokenResponse(BaseModel):
    id: int
    name: str
    permissions: str
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    created_at: datetime
    token_prefix: str


class TokenResponse(BaseModel):
    token: str
    name: str
    expires_at: Optional[datetime]


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.get("", response_model=List[APITokenResponse])
def list_tokens(authorization: str = Header(None), db: Session = Depends(get_db)):
    from app.api.routers import get_user_from_token
    user = get_user_from_token(authorization)
    
    if not user or user.role.upper() not in ["ADMIN", "MANAGER"]:
        raise HTTPException(status_code=403, detail="Only admins and managers can manage API tokens")
    
    tokens = db.query(APIToken).filter(APIToken.user_id == user.id).all()
    
    return [
        APITokenResponse(
            id=t.id,
            name=t.name,
            permissions=t.permissions,
            expires_at=t.expires_at,
            last_used=t.last_used,
            created_at=t.created_at,
            token_prefix=t.token_hash[:8] if t.token_hash else ""
        )
        for t in tokens
    ]


@router.post("", response_model=TokenResponse)
def create_token(token_data: APITokenCreate, authorization: str = Header(None), db: Session = Depends(get_db)):
    from app.api.routers import get_user_from_token
    user = get_user_from_token(authorization)
    
    if not user or user.role.upper() not in ["ADMIN", "MANAGER"]:
        raise HTTPException(status_code=403, detail="Only admins and managers can create API tokens")
    
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    
    expires_at = None
    if token_data.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=token_data.expires_days)
    
    api_token = APIToken(
        user_id=user.id,
        name=token_data.name,
        token_hash=token_hash,
        permissions=token_data.permissions,
        expires_at=expires_at
    )
    
    db.add(api_token)
    db.commit()
    
    return TokenResponse(
        token=token,
        name=token_data.name,
        expires_at=expires_at
    )


@router.delete("/{token_id}")
def delete_token(token_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    from app.api.routers import get_user_from_token
    user = get_user_from_token(authorization)
    
    if not user or user.role.upper() not in ["ADMIN", "MANAGER"]:
        raise HTTPException(status_code=403, detail="Only admins and managers can delete API tokens")
    
    token = db.query(APIToken).filter(APIToken.id == token_id, APIToken.user_id == user.id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    db.delete(token)
    db.commit()
    
    return {"message": "Token deleted"}


def verify_api_token(token: str, db: Session) -> Optional[User]:
    token_hash = hash_token(token)
    
    api_token = db.query(APIToken).filter(APIToken.token_hash == token_hash).first()
    
    if not api_token:
        return None
    
    if api_token.expires_at and api_token.expires_at < datetime.utcnow():
        return None
    
    api_token.last_used = datetime.utcnow()
    db.commit()
    
    user = db.query(User).filter(User.id == api_token.user_id).first()
    return user
