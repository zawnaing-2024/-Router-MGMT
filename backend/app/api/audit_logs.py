from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models import AuditLog, User
from app.schemas import AuditLogResponse
import jwt

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])

SECRET_KEY = "your-secret-key-change-in-production-use-strong-random-key"
ALGORITHM = "HS256"


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


@router.get("", response_model=List[AuditLogResponse])
def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: Optional[int] = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    user = get_user_from_token(authorization)
    
    if not user or user.role.upper() not in ["ADMIN", "MANAGER"]:
        return []
    
    query = db.query(AuditLog)
    
    if user.role.upper() == "MANAGER":
        from app.models import Router
        conditions = []
        if user.router_ids:
            conditions.append(AuditLog.entity_id.in_(user.router_ids))
        if user.project_id:
            routers = db.query(Router.id).filter(Router.project_id == user.project_id).all()
            router_ids = [r.id for r in routers]
            conditions.append(AuditLog.entity_id.in_(router_ids))
        if conditions:
            from sqlalchemy import or_
            query = query.filter(or_(*conditions))
        else:
            query = query.filter(AuditLog.user_id == user.id)
    
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    
    return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/actions")
def get_actions(db: Session = Depends(get_db)):
    actions = db.query(AuditLog.action).distinct().all()
    return [a[0] for a in actions]


@router.get("/entity-types")
def get_entity_types(db: Session = Depends(get_db)):
    types = db.query(AuditLog.entity_type).distinct().all()
    return [t[0] for t in types]
