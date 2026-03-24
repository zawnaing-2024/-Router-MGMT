from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import jwt
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.models import User, UserRole
from app.schemas import LoginRequest, LoginResponse, UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/auth", tags=["Auth"])

SECRET_KEY = "your-secret-key-change-in-production-use-strong-random-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def get_user_from_token(authorization: str = None) -> Optional[User]:
    if not authorization:
        return None
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        db = next(get_db())
        user = db.query(User).filter(User.id == payload.get("sub")).first()
        return user
    except:
        return None


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(db: Session = Depends(get_db), token: str = None):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
    except:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        return None
    return user


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive")
    
    token = create_access_token({"sub": user.id})
    user_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": str(user.role) if user.role else "VIEWER",
        "router_ids": user.router_ids or [],
        "is_active": user.is_active,
        "project_id": user.project_id,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None
    }
    return LoginResponse(token=token, user=UserResponse(**user_data))


@router.post("/register", response_model=UserResponse)
def register(data: UserCreate, authorization: str = Header(None), db: Session = Depends(get_db)):
    current_user = get_user_from_token(authorization)
    if not current_user or current_user.role.lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create users")
    
    existing = db.query(User).filter(
        (User.username == data.username) | (User.email == data.email)
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role or "VIEWER",
        router_ids=data.router_ids or [],
        project_id=data.project_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
def get_me(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, data: UserUpdate, authorization: str = Header(None), db: Session = Depends(get_db)):
    current_user = get_user_from_token(authorization)
    if not current_user or current_user.role.lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admins can manage users")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if data.username:
        user.username = data.username
    if data.email:
        user.email = data.email
    if data.password:
        user.password_hash = hash_password(data.password)
    if data.role:
        user.role = data.role
    if data.router_ids is not None:
        user.router_ids = data.router_ids
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.project_id is not None:
        user.project_id = data.project_id
    
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UserResponse])
def list_users(authorization: str = Header(None), db: Session = Depends(get_db)):
    current_user = get_user_from_token(authorization)
    if not current_user or current_user.role.lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view users")
    return db.query(User).all()


@router.delete("/users/{user_id}")
def delete_user(user_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    current_user = get_user_from_token(authorization)
    if not current_user or current_user.role.lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete users")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}
