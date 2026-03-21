from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import decrypt_password
from app.models import Router, PerformanceMetric
from app.services.monitoring_service import collect_router_metrics


router = APIRouter(prefix="/api/routers", tags=["metrics"])


class MetricResponse(BaseModel):
    id: int
    router_id: int
    cpu_percent: Optional[int]
    memory_percent: Optional[int]
    memory_used_mb: Optional[int]
    memory_total_mb: Optional[int]
    disk_percent: Optional[int]
    uptime_seconds: Optional[int]
    collected_at: datetime

    class Config:
        from_attributes = True


class LatestMetricsResponse(BaseModel):
    router_id: int
    hostname: str
    cpu_percent: Optional[int]
    memory_percent: Optional[int]
    memory_used_mb: Optional[int]
    memory_total_mb: Optional[int]
    disk_percent: Optional[int]
    uptime_seconds: Optional[int]
    collected_at: Optional[datetime]


class CollectResponse(BaseModel):
    success: bool
    metrics: Optional[dict] = None
    error: Optional[str] = None


@router.get("/{router_id}/metrics/latest", response_model=LatestMetricsResponse)
def get_latest_metrics(router_id: int, db: Session = Depends(get_db)):
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")

    metric = db.query(PerformanceMetric).filter(
        PerformanceMetric.router_id == router_id
    ).order_by(desc(PerformanceMetric.collected_at)).first()

    return LatestMetricsResponse(
        router_id=router.id,
        hostname=router.hostname,
        cpu_percent=metric.cpu_percent if metric else None,
        memory_percent=metric.memory_percent if metric else None,
        memory_used_mb=metric.memory_used_mb if metric else None,
        memory_total_mb=metric.memory_total_mb if metric else None,
        disk_percent=metric.disk_percent if metric else None,
        uptime_seconds=metric.uptime_seconds if metric else None,
        collected_at=metric.collected_at if metric else None
    )


@router.get("/{router_id}/metrics/history", response_model=List[MetricResponse])
def get_metrics_history(
    router_id: int,
    hours: int = 24,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")

    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    metrics = db.query(PerformanceMetric).filter(
        PerformanceMetric.router_id == router_id,
        PerformanceMetric.collected_at >= cutoff
    ).order_by(desc(PerformanceMetric.collected_at)).limit(limit).all()

    return metrics


@router.post("/{router_id}/metrics/collect", response_model=CollectResponse)
def collect_metrics(router_id: int, db: Session = Depends(get_db)):
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")

    password = decrypt_password(router.password_encrypted) if router.password_encrypted else None

    success, data = collect_router_metrics(
        host=router.ip_address,
        port=router.port,
        username=router.username,
        password=password,
        vendor=router.vendor if router.vendor else "generic"
    )

    if not success:
        return CollectResponse(success=False, error=data.get("error"))

    metric = PerformanceMetric(
        router_id=router_id,
        cpu_percent=data.get("cpu_percent"),
        memory_percent=data.get("memory_percent"),
        memory_used_mb=data.get("memory_used_mb"),
        memory_total_mb=data.get("memory_total_mb"),
        disk_percent=data.get("disk_percent"),
        uptime_seconds=data.get("uptime_seconds")
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)

    return CollectResponse(success=True, metrics=data)


@router.get("/metrics/all-latest", response_model=List[LatestMetricsResponse])
def get_all_latest_metrics(db: Session = Depends(get_db)):
    routers = db.query(Router).all()
    results = []

    for router in routers:
        metric = db.query(PerformanceMetric).filter(
            PerformanceMetric.router_id == router.id
        ).order_by(desc(PerformanceMetric.collected_at)).first()

        results.append(LatestMetricsResponse(
            router_id=router.id,
            hostname=router.hostname,
            cpu_percent=metric.cpu_percent if metric else None,
            memory_percent=metric.memory_percent if metric else None,
            memory_used_mb=metric.memory_used_mb if metric else None,
            memory_total_mb=metric.memory_total_mb if metric else None,
            disk_percent=metric.disk_percent if metric else None,
            uptime_seconds=metric.uptime_seconds if metric else None,
            collected_at=metric.collected_at if metric else None
        ))

    return results


@router.post("/metrics/collect-all", response_model=dict)
def collect_all_metrics(db: Session = Depends(get_db)):
    routers = db.query(Router).all()
    results = {"success": 0, "failed": 0, "errors": []}

    for router in routers:
        password = decrypt_password(router.password_encrypted) if router.password_encrypted else None

        success, data = collect_router_metrics(
            host=router.ip_address,
            port=router.port,
            username=router.username,
            password=password,
            vendor=router.vendor if router.vendor else "generic"
        )

        if success:
            metric = PerformanceMetric(
                router_id=router.id,
                cpu_percent=data.get("cpu_percent"),
                memory_percent=data.get("memory_percent"),
                memory_used_mb=data.get("memory_used_mb"),
                memory_total_mb=data.get("memory_total_mb"),
                disk_percent=data.get("disk_percent"),
                uptime_seconds=data.get("uptime_seconds")
            )
            db.add(metric)
            results["success"] += 1
        else:
            results["failed"] += 1
            results["errors"].append({"router": router.hostname, "error": data.get("error")})

    db.commit()
    return results


@router.delete("/metrics/cleanup")
def cleanup_old_metrics(days: int = 30, db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=days)
    deleted = db.query(PerformanceMetric).filter(
        PerformanceMetric.collected_at < cutoff
    ).delete()
    db.commit()
    return {"deleted": deleted}
