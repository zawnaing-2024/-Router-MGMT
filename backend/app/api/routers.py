from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import encrypt_password, decrypt_password
from app.models import Router, RouterStatus, RouterLog
from app.schemas import (
    RouterCreate, RouterUpdate, RouterResponse, RouterListResponse,
    CommandRequest, CommandResponse, ConnectionTestResponse
)
from app.services import SSHService, test_connection

router = APIRouter(prefix="/routers", tags=["Routers"])


def log_router_event(db: Session, router_id: int, level: str, source: str, message: str, details: dict = None):
    log_entry = RouterLog(
        router_id=router_id,
        level=level,
        source=source,
        message=message,
        details=details if details else {}
    )
    db.add(log_entry)
    db.commit()


@router.get("", response_model=List[RouterListResponse])
def list_routers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    vendor: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Router)
    
    if vendor:
        query = query.filter(Router.vendor == vendor)
    if status:
        query = query.filter(Router.status == status)
    if search:
        query = query.filter(
            (Router.hostname.ilike(f"%{search}%")) |
            (Router.ip_address.ilike(f"%{search}%")) |
            (Router.location.ilike(f"%{search}%"))
        )
    
    return query.order_by(Router.hostname).offset(skip).limit(limit).all()


@router.get("/{router_id}", response_model=RouterResponse)
def get_router(router_id: int, db: Session = Depends(get_db)):
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")
    return router


@router.post("", response_model=RouterResponse, status_code=201)
def create_router(router_data: RouterCreate, db: Session = Depends(get_db)):
    existing = db.query(Router).filter(
        (Router.hostname == router_data.hostname) |
        (Router.ip_address == router_data.ip_address)
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Router with same hostname or IP already exists")
    
    if not router_data.password and not router_data.ssh_key:
        raise HTTPException(status_code=400, detail="Either password or SSH key is required")
    
    router = Router(
        hostname=router_data.hostname,
        ip_address=router_data.ip_address,
        port=router_data.port,
        vendor=router_data.vendor,
        username=router_data.username,
        password_encrypted=encrypt_password(router_data.password) if router_data.password else "",
        ssh_key=router_data.ssh_key,
        location=router_data.location,
        tags=router_data.tags,
        notes=router_data.notes,
        status=RouterStatus.UNKNOWN
    )
    
    db.add(router)
    db.commit()
    db.refresh(router)
    
    success, _, _ = test_connection(
        host=router.ip_address,
        port=router.port,
        username=router.username,
        password=router_data.password,
        ssh_key=router_data.ssh_key
    )
    
    if success:
        router.status = RouterStatus.ONLINE
        router.last_seen = datetime.utcnow()
        log_router_event(db, router.id, "success", "router", "Router added and online", {"vendor": router.vendor, "ip": router.ip_address})
    else:
        router.status = RouterStatus.OFFLINE
        log_router_event(db, router.id, "warning", "router", "Router added but offline", {"vendor": router.vendor, "ip": router.ip_address})
    
    db.commit()
    db.refresh(router)
    return router


@router.put("/{router_id}", response_model=RouterResponse)
def update_router(router_id: int, router_data: RouterUpdate, db: Session = Depends(get_db)):
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")
    
    update_data = router_data.model_dump(exclude_unset=True)
    
    if "password" in update_data and update_data["password"]:
        router.password_encrypted = encrypt_password(update_data.pop("password"))
    elif "password" in update_data:
        update_data.pop("password")
    
    for key, value in update_data.items():
        if key not in ("password_encrypted", "password"):
            setattr(router, key, value)
    
    router.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(router)
    return router


@router.delete("/{router_id}", status_code=204)
def delete_router(router_id: int, db: Session = Depends(get_db)):
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")
    
    db.delete(router)
    db.commit()


@router.post("/{router_id}/backup")
def trigger_backup(router_id: int, db: Session = Depends(get_db)):
    from app.services import BackupService
    
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")
    
    backup_service = BackupService(db)
    success, message, backup = backup_service.backup_router(router_id, "manual")
    
    if success:
        log_router_event(db, router_id, "success", "backup", f"Backup created successfully", {"backup_id": backup.id, "size_bytes": backup.size_bytes})
        return {"success": True, "message": message, "backup_id": backup.id}
    else:
        log_router_event(db, router_id, "error", "backup", f"Backup failed: {message}")
        raise HTTPException(status_code=500, detail=message)


@router.post("/{router_id}/connect", response_model=ConnectionTestResponse)
def test_router_connection(router_id: int, db: Session = Depends(get_db)):
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")
    
    try:
        password = decrypt_password(router.password_encrypted) if router.password_encrypted else None
        success, message, latency = test_connection(
            host=router.ip_address,
            port=router.port,
            username=router.username,
            password=password,
            ssh_key=router.ssh_key
        )
        
        if success:
            router.status = RouterStatus.ONLINE
            router.last_seen = datetime.utcnow()
            log_router_event(db, router_id, "success", "connection", f"Connection successful", {"latency_ms": latency})
        else:
            router.status = RouterStatus.OFFLINE
            log_router_event(db, router_id, "error", "connection", f"Connection failed: {message}", {"latency_ms": latency})
        
        db.commit()
        
        return ConnectionTestResponse(
            success=success,
            message=message,
            latency_ms=latency
        )
    except Exception as e:
        router.status = RouterStatus.OFFLINE
        log_router_event(db, router_id, "error", "connection", f"Connection error: {str(e)}")
        db.commit()
        return ConnectionTestResponse(success=False, message=str(e))


@router.post("/{router_id}/command", response_model=CommandResponse)
def execute_command(router_id: int, cmd_data: CommandRequest, db: Session = Depends(get_db)):
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")
    
    try:
        password = decrypt_password(router.password_encrypted) if router.password_encrypted else None
        
        ssh = SSHService(
            host=router.ip_address,
            port=router.port,
            username=router.username,
            password=password,
            ssh_key=router.ssh_key
        )
        
        success, conn_msg = ssh.connect()
        if not success:
            log_router_event(db, router_id, "error", "command", f"Command execution failed: {conn_msg}", {"command": cmd_data.command})
            return CommandResponse(success=False, output="", error=f"Connection failed: {conn_msg}")
        
        success, output, error = ssh.execute_command(cmd_data.command)
        ssh.close()
        
        if success:
            log_router_event(db, router_id, "info", "command", f"Command executed successfully", {"command": cmd_data.command})
        else:
            log_router_event(db, router_id, "warning", "command", f"Command returned error", {"command": cmd_data.command, "error": error})
        
        return CommandResponse(
            success=success,
            output=output,
            error=error if error else None
        )
    except Exception as e:
        log_router_event(db, router_id, "error", "command", f"Command execution error: {str(e)}", {"command": cmd_data.command})
        return CommandResponse(success=False, output="", error=str(e))
