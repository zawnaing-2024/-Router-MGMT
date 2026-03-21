from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
import hashlib

from app.core.database import get_db
from app.models import Router, ConfigBackup, PingMetric, ConfigChange, RouterStatus
from app.schemas import UptimeReport, FirmwareInfo, ConfigChangeResponse
from app.services import SSHService
from app.core.security import decrypt_password

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/uptime", response_model=List[UptimeReport])
def get_uptime_report(
    days: int = 30,
    db: Session = Depends(get_db)
):
    start_date = datetime.utcnow() - timedelta(days=days)
    
    routers = db.query(Router).all()
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
def get_firmware_versions(db: Session = Depends(get_db)):
    routers = db.query(Router).filter(Router.status == RouterStatus.ONLINE).all()
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
    db: Session = Depends(get_db)
):
    query = db.query(ConfigChange)
    
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
