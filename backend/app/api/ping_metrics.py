from fastapi import APIRouter, Depends, Query, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime, timedelta
import jwt

from app.core.database import get_db
from app.models import PingMetric, Router, User

router = APIRouter(prefix="/ping-metrics", tags=["Ping Metrics"])

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


@router.get("/router/{router_id}")
def get_router_ping_history(
    router_id: int,
    hours: int = Query(24, ge=1, le=168),
    target: Optional[str] = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    user = get_user_from_token(authorization)
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    if not router_obj:
        return {"error": "Router not found"}
    
    if user and user.role.lower() != "admin":
        has_access = False
        if user.router_ids and router_id in user.router_ids:
            has_access = True
        if user.project_id and router_obj.project_id == user.project_id:
            has_access = True
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")
    
    since = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(PingMetric).filter(
        PingMetric.router_id == router_id,
        PingMetric.collected_at >= since
    )
    
    if target:
        query = query.filter(PingMetric.target == target)
    
    metrics = query.order_by(PingMetric.collected_at).all()
    
    return {
        "router_id": router_id,
        "target": target,
        "hours": hours,
        "data": [
            {
                "id": m.id,
                "target": m.target,
                "latency_avg_ms": m.latency_avg_ms,
                "latency_min_ms": m.latency_min_ms,
                "latency_max_ms": m.latency_max_ms,
                "packet_loss_percent": m.packet_loss_percent,
                "packets_sent": m.packets_sent,
                "packets_received": m.packets_received,
                "collected_at": m.collected_at.isoformat() if m.collected_at else None
            }
            for m in metrics
        ]
    }


@router.get("/job/{job_id}")
def get_job_ping_history(
    job_id: int,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    since = datetime.utcnow() - timedelta(hours=hours)
    
    metrics = db.query(PingMetric).filter(
        PingMetric.job_id == job_id,
        PingMetric.collected_at >= since
    ).order_by(PingMetric.collected_at).all()
    
    return {
        "job_id": job_id,
        "hours": hours,
        "data": [
            {
                "id": m.id,
                "target": m.target,
                "latency_avg_ms": m.latency_avg_ms,
                "latency_min_ms": m.latency_min_ms,
                "latency_max_ms": m.latency_max_ms,
                "packet_loss_percent": m.packet_loss_percent,
                "packets_sent": m.packets_sent,
                "packets_received": m.packets_received,
                "collected_at": m.collected_at.isoformat() if m.collected_at else None
            }
            for m in metrics
        ]
    }


@router.get("/latest")
def get_latest_ping_metrics(
    router_id: Optional[int] = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    user = get_user_from_token(authorization)
    
    if not user:
        return []
    
    from sqlalchemy import func
    
    router_query = db.query(Router.id)
    if user.role.lower() != "admin":
        if user.router_ids:
            router_query = router_query.filter(Router.id.in_(user.router_ids))
        if user.project_id:
            router_query = router_query.filter(Router.project_id == user.project_id)
        
        if not user.router_ids and not user.project_id:
            return []
        allowed_router_ids = [r.id for r in router_query.all()]
    
    query = db.query(
        PingMetric.router_id,
        PingMetric.target,
        func.max(PingMetric.collected_at).label("latest_time")
    ).group_by(PingMetric.router_id, PingMetric.target)
    
    if user.role.lower() != "admin":
        query = query.filter(PingMetric.router_id.in_(allowed_router_ids))
    
    if router_id:
        query = query.filter(PingMetric.router_id == router_id)
    
    latest = query.all()
    
    results = []
    for item in latest:
        metric = db.query(PingMetric).filter(
            PingMetric.router_id == item.router_id,
            PingMetric.target == item.target,
            PingMetric.collected_at == item.latest_time
        ).first()
        
        if metric:
            results.append({
                "router_id": metric.router_id,
                "target": metric.target,
                "latency_avg_ms": metric.latency_avg_ms,
                "latency_min_ms": metric.latency_min_ms,
                "latency_max_ms": metric.latency_max_ms,
                "packet_loss_percent": metric.packet_loss_percent,
                "packets_sent": metric.packets_sent,
                "packets_received": metric.packets_received,
                "collected_at": metric.collected_at.isoformat() if metric.collected_at else None
            })
    
    return results
