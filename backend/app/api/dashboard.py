from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models import Router, ConfigBackup, ScheduledJob, RouterStatus, JobStatus
from app.schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Router.id)).scalar()
    online = db.query(func.count(Router.id)).filter(Router.status == RouterStatus.ONLINE).scalar()
    offline = db.query(func.count(Router.id)).filter(Router.status == RouterStatus.OFFLINE).scalar()
    warning = db.query(func.count(Router.id)).filter(Router.status == RouterStatus.WARNING).scalar()
    
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    
    backups_today = db.query(func.count(ConfigBackup.id)).filter(
        ConfigBackup.created_at >= today
    ).scalar()
    
    backups_this_week = db.query(func.count(ConfigBackup.id)).filter(
        ConfigBackup.created_at >= week_ago
    ).scalar()
    
    failed_jobs = db.query(func.count(ScheduledJob.id)).filter(
        ScheduledJob.last_status == JobStatus.FAILED
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
