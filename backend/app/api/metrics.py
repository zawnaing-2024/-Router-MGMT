from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import jwt

from app.core.database import get_db
from app.core.security import decrypt_password
from app.models import Router, PerformanceMetric, User
from app.services.monitoring_service import collect_router_metrics

router = APIRouter(prefix="/api/routers", tags=["metrics"])

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
def get_latest_metrics(router_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    user = get_user_from_token(authorization)
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")
    
    if user and user.role.lower() != "admin":
        has_access = False
        if user.router_ids and router_id in user.router_ids:
            has_access = True
        if user.project_id and router.project_id == user.project_id:
            has_access = True
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")

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
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    user = get_user_from_token(authorization)
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")
    
    if user and user.role.lower() != "admin":
        has_access = False
        if user.router_ids and router_id in user.router_ids:
            has_access = True
        if user.project_id and router.project_id == user.project_id:
            has_access = True
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")

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
    
    if data.get("uptime_seconds"):
        router.uptime_seconds = data.get("uptime_seconds")
    if data.get("version"):
        router.version = data.get("version")
    
    db.commit()
    db.refresh(metric)

    return CollectResponse(success=True, metrics=data)


@router.get("/metrics/all-latest", response_model=List[LatestMetricsResponse])
def get_all_latest_metrics(authorization: str = Header(None), db: Session = Depends(get_db)):
    user = get_user_from_token(authorization)
    
    if not user:
        return []
    
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
            return []
    
    routers = router_query.all()
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


class InterfaceInfo(BaseModel):
    name: str
    state: str
    ip: str
    description: Optional[str] = ''
    speed_mbps: Optional[int] = 0
    duplex: Optional[str] = None
    port: Optional[str] = None
    tx_bps: Optional[int] = 0
    rx_bps: Optional[int] = 0
    tx_bpsHuman: Optional[str] = '0'
    rx_bpsHuman: Optional[str] = '0'
    tx_bytes: Optional[int] = 0
    rx_bytes: Optional[int] = 0
    tx_packets: Optional[int] = 0
    rx_packets: Optional[int] = 0
    tx_errors: Optional[int] = 0
    rx_errors: Optional[int] = 0


class BGPPeerInfo(BaseModel):
    neighbor: str
    state: str
    asn: Optional[str] = None
    uptime: Optional[str] = ''
    description: Optional[str] = ''


class NetworkInfoResponse(BaseModel):
    interfaces: List[InterfaceInfo]
    bgp_peers: List[BGPPeerInfo]


@router.get("/{router_id}/network-info", response_model=NetworkInfoResponse)
def get_network_info(router_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    user = get_user_from_token(authorization)
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")
    
    if user and user.role.lower() != "admin":
        has_access = False
        if user.router_ids and router_id in user.router_ids:
            has_access = True
        if user.project_id and router.project_id == user.project_id:
            has_access = True
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")
    
    password = decrypt_password(router.password_encrypted) if router.password_encrypted else None
    
    from app.services.monitoring_service import MonitoringService
    from app.services.ssh_service import SSHService
    
    ssh = SSHService(
        host=router.ip_address,
        port=router.port,
        username=router.username,
        password=password,
        ssh_key=router.ssh_key
    )
    
    success, _ = ssh.connect()
    if not success:
        raise HTTPException(status_code=503, detail="Cannot connect to router")
    
    monitoring = MonitoringService(ssh)
    metrics = monitoring.collect_metrics(router.vendor if router.vendor else "generic")
    ssh.close()
    
    interfaces = [InterfaceInfo(**i) for i in metrics.get('interfaces', [])]
    bgp_peers = [BGPPeerInfo(**p) for p in metrics.get('bgp_peers', [])]
    
    return NetworkInfoResponse(interfaces=interfaces, bgp_peers=bgp_peers)
