from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime, timedelta
import hashlib
import jwt

from app.core.database import get_db
from app.models import Router, ConfigBackup, PingMetric, ConfigChange, RouterStatus, User
from app.schemas import UptimeReport, FirmwareInfo, ConfigChangeResponse
from app.services import SSHService
from app.core.security import decrypt_password

router = APIRouter(prefix="/reports", tags=["Reports"])

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


@router.get("/uptime", response_model=List[UptimeReport])
def get_uptime_report(
    days: int = 30,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
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
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    routers = router_query.all()
    reports = []
    
    for router in routers:
        ping_metrics = db.query(PingMetric).filter(
            PingMetric.router_id == router.id,
            PingMetric.collected_at >= start_date
        ).all()
        
        total_checks = len(ping_metrics)
        if total_checks == 0:
            total_checks = days * 24
            successful_checks = 1 if router.status == RouterStatus.ONLINE else 0
        else:
            successful_checks = sum(1 for m in ping_metrics if m.packet_loss_percent < 100)
        
        failed_checks = total_checks - successful_checks
        uptime_percent = (successful_checks / total_checks * 100) if total_checks > 0 else 0
        
        avg_latency = None
        latencies = [m.latency_avg_ms for m in ping_metrics if m.latency_avg_ms is not None]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
        
        reports.append(UptimeReport(
            router_id=router.id,
            hostname=router.hostname,
            uptime_percent=round(uptime_percent, 2),
            total_checks=total_checks,
            successful_checks=successful_checks,
            failed_checks=failed_checks,
            avg_latency_ms=round(avg_latency, 2) if avg_latency else None
        ))
    
    return reports


@router.get("/firmware", response_model=List[FirmwareInfo])
def get_firmware_versions(authorization: str = Header(None), db: Session = Depends(get_db)):
    user = get_user_from_token(authorization)
    
    if not user:
        return []
    
    router_query = db.query(Router).filter(Router.status == RouterStatus.ONLINE)
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
    firmware_info = []
    
    for router in routers:
        try:
            password = decrypt_password(router.password_encrypted) if router.password_encrypted else None
            
            ssh = SSHService(
                host=router.ip_address,
                port=router.port,
                username=router.username,
                password=password,
                ssh_key=router.ssh_key
            )
            
            success, _ = ssh.connect()
            if not success:
                continue
            
            version = None
            os_type = router.vendor
            
            if "cisco" in router.vendor:
                success, output, _ = ssh.execute_command("show version | include Version")
                if success and output:
                    lines = output.split("\n")
                    for line in lines:
                        if "Version" in line:
                            version = line.split("Version")[-1].strip().split()[0]
                            break
            elif "juniper" in router.vendor:
                success, output, _ = ssh.execute_command("show version | match Junos")
                if success and output:
                    parts = output.strip().split()
                    for i, p in enumerate(parts):
                        if "Junos" in p:
                            version = parts[i + 1] if i + 1 < len(parts) else None
                            break
            elif "mikrotik" in router.vendor:
                success, output, _ = ssh.execute_command("/system routerboard print")
                if success and output:
                    version = router.vendor
            
            ssh.close()
            
            firmware_info.append(FirmwareInfo(
                router_id=router.id,
                hostname=router.hostname,
                version=version,
                os_type=os_type,
                collected_at=datetime.utcnow()
            ))
        except Exception:
            firmware_info.append(FirmwareInfo(
                router_id=router.id,
                hostname=router.hostname,
                version=None,
                os_type=router.vendor,
                collected_at=datetime.utcnow()
            ))
    
    return firmware_info


@router.get("/config-changes", response_model=List[ConfigChangeResponse])
def get_config_changes(
    router_id: Optional[int] = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    user = get_user_from_token(authorization)
    
    if not user:
        return []
    
    query = db.query(ConfigChange)
    
    if user.role.lower() != "admin":
        router_query = db.query(Router.id)
        if user.router_ids:
            router_query = router_query.filter(Router.id.in_(user.router_ids))
        if user.project_id:
            router_query = router_query.filter(Router.project_id == user.project_id)
        
        if user.router_ids or user.project_id:
            allowed_router_ids = [r.id for r in router_query.all()]
            query = query.filter(ConfigChange.router_id.in_(allowed_router_ids))
        else:
            return []
    
    if router_id:
        query = query.filter(ConfigChange.router_id == router_id)
    
    return query.order_by(ConfigChange.detected_at.desc()).limit(100).all()


@router.post("/check-config-changes/{router_id}")
def check_config_changes(router_id: int, db: Session = Depends(get_db)):
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")
    
    latest_backup = db.query(ConfigBackup).filter(
        ConfigBackup.router_id == router_id
    ).order_by(ConfigBackup.created_at.desc()).first()
    
    if not latest_backup:
        return {"has_changes": None, "message": "No backup found to compare"}
    
    try:
        password = decrypt_password(router.password_encrypted) if router.password_encrypted else None
        
        ssh = SSHService(
            host=router.ip_address,
            port=router.port,
            username=router.username,
            password=password,
            ssh_key=router.ssh_key
        )
        
        success, _ = ssh.connect()
        if not success:
            return {"has_changes": None, "message": "Cannot connect to router"}
        
        command = "show running-config all"
        if "juniper" in router.vendor:
            command = "show configuration | display set"
        elif "mikrotik" in router.vendor:
            command = "/export"
        
        success, current_config, _ = ssh.execute_command(command)
        ssh.close()
        
        if not success:
            return {"has_changes": None, "message": "Cannot get current config"}
        
        current_checksum = hashlib.sha256(current_config.encode()).hexdigest()
        
        has_changes = current_checksum != latest_backup.checksum
        
        if has_changes:
            config_change = ConfigChange(
                router_id=router_id,
                backup_id=latest_backup.id,
                change_type="detected",
                details={"old_checksum": latest_backup.checksum, "new_checksum": current_checksum}
            )
            db.add(config_change)
            db.commit()
        
        return {
            "has_changes": has_changes,
            "old_checksum": latest_backup.checksum,
            "new_checksum": current_checksum
        }
    except Exception as e:
        return {"has_changes": None, "message": str(e)}


@router.get("/config-drift-summary")
def get_config_drift_summary(authorization: str = Header(None), db: Session = Depends(get_db)):
    from app.models import User
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
        latest_backup = db.query(ConfigBackup).filter(
            ConfigBackup.router_id == router.id
        ).order_by(ConfigBackup.created_at.desc()).first()
        
        latest_change = db.query(ConfigChange).filter(
            ConfigChange.router_id == router.id
        ).order_by(ConfigChange.detected_at.desc()).first()
        
        results.append({
            "router_id": router.id,
            "hostname": router.hostname,
            "last_backup": latest_backup.created_at.isoformat() if latest_backup else None,
            "last_check": latest_change.detected_at.isoformat() if latest_change else None,
            "has_drift": latest_change is not None
        })
    
    return results
