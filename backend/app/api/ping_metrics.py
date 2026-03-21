from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models import PingMetric, Router

router = APIRouter(prefix="/ping-metrics", tags=["Ping Metrics"])


@router.get("/router/{router_id}")
def get_router_ping_history(
    router_id: int,
    hours: int = Query(24, ge=1, le=168),
    target: Optional[str] = None,
    db: Session = Depends(get_db)
):
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    if not router_obj:
        return {"error": "Router not found"}
    
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
    db: Session = Depends(get_db)
):
    from sqlalchemy import func
    
    query = db.query(
        PingMetric.router_id,
        PingMetric.target,
        func.max(PingMetric.collected_at).label("latest_time")
    ).group_by(PingMetric.router_id, PingMetric.target)
    
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
