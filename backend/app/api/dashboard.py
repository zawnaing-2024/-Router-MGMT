from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, timedelta
from typing import Optional
import jwt

from app.core.database import get_db
from app.models import Router, ConfigBackup, ScheduledJob, RouterStatus, JobStatus, User
from app.schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

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


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(authorization: str = Header(None), db: Session = Depends(get_db)):
    user = get_user_from_token(authorization)
    
    if not user:
        return DashboardStats(
            total_routers=0, online_routers=0, offline_routers=0, warning_routers=0,
            backups_today=0, backups_this_week=0, failed_jobs=0
        )
    
    router_query = db.query(Router)
    if user.role.lower() != "admin":
        conditions = []
        if user.router_ids:
            conditions.append(Router.id.in_(user.router_ids))
        if user.project_id:
            conditions.append(Router.project_id == user.project_id)
        
        if conditions:
            router_query = router_query.filter(or_(*conditions))
        else:
            return DashboardStats(
                total_routers=0, online_routers=0, offline_routers=0, warning_routers=0,
                backups_today=0, backups_this_week=0, failed_jobs=0
            )
    
    total = router_query.with_entities(func.count(Router.id)).scalar()
    online = router_query.filter(Router.status == RouterStatus.ONLINE).with_entities(func.count(Router.id)).scalar()
    offline = router_query.filter(Router.status == RouterStatus.OFFLINE).with_entities(func.count(Router.id)).scalar()
    warning = router_query.filter(Router.status == RouterStatus.WARNING).with_entities(func.count(Router.id)).scalar()
    
    router_ids = [r.id for r in router_query.all()]
    
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    
    backups_today = db.query(func.count(ConfigBackup.id)).filter(
        ConfigBackup.created_at >= today,
        ConfigBackup.router_id.in_(router_ids) if router_ids else False
    ).scalar()
    
    backups_this_week = db.query(func.count(ConfigBackup.id)).filter(
        ConfigBackup.created_at >= week_ago,
        ConfigBackup.router_id.in_(router_ids) if router_ids else False
    ).scalar()
    
    failed_jobs = db.query(func.count(ScheduledJob.id)).join(Router).filter(
        ScheduledJob.last_status == JobStatus.FAILED,
        Router.id.in_(router_ids) if router_ids else False
    ).scalar()
    
    return DashboardStats(
        total_routers=total or 0,
        online_routers=online or 0,
        offline_routers=offline or 0,
        warning_routers=warning or 0,
        backups_today=backups_today or 0,
        backups_this_week=backups_this_week or 0,
        failed_jobs=failed_jobs or 0
    )
