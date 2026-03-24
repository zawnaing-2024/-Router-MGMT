from fastapi import APIRouter, Depends, HTTPException, Query, Header
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
import jwt

from app.core.database import get_db
from app.models import ConfigBackup, Router, User
from app.schemas import (
    ConfigBackupResponse, ConfigBackupDetailResponse,
    BackupCompareRequest, BackupCompareResponse
)
from app.services import BackupService

router = APIRouter(prefix="/backups", tags=["Backups"])

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


@router.get("", response_model=List[ConfigBackupResponse])
def list_backups(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    router_id: Optional[int] = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    user = get_user_from_token(authorization)
    
    if not user:
        return []
    
    query = db.query(ConfigBackup)
    
    if user.role.lower() != "admin":
        router_query = db.query(Router.id)
        if user.router_ids:
            router_query = router_query.filter(Router.id.in_(user.router_ids))
        if user.project_id:
            router_query = router_query.filter(Router.project_id == user.project_id)
        
        if user.router_ids or user.project_id:
            allowed_router_ids = [r.id for r in router_query.all()]
            query = query.filter(ConfigBackup.router_id.in_(allowed_router_ids))
        else:
            return []
    
    if router_id:
        query = query.filter(ConfigBackup.router_id == router_id)
    
    return query.order_by(ConfigBackup.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{backup_id}", response_model=ConfigBackupDetailResponse)
def get_backup(backup_id: int, db: Session = Depends(get_db)):
    backup = db.query(ConfigBackup).filter(ConfigBackup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    return backup


@router.post("/{backup_id}/restore")
def restore_backup(backup_id: int, db: Session = Depends(get_db)):
    backup = db.query(ConfigBackup).filter(ConfigBackup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    backup_service = BackupService(db)
    success, message = backup_service.restore_config(backup.router_id, backup_id)
    
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=500, detail=message)


@router.delete("/{backup_id}", status_code=204)
def delete_backup(backup_id: int, db: Session = Depends(get_db)):
    backup = db.query(ConfigBackup).filter(ConfigBackup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    db.delete(backup)
    db.commit()


@router.get("/{backup_id}/download")
def download_backup(backup_id: int, db: Session = Depends(get_db)):
    backup = db.query(ConfigBackup).filter(ConfigBackup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    filename = backup.filename or f"backup_{backup_id}.cfg"
    
    return Response(
        content=backup.content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/compare", response_model=BackupCompareResponse)
def compare_backups(compare_data: BackupCompareRequest, db: Session = Depends(get_db)):
    backup_service = BackupService(db)
    diff, added, removed, unchanged = backup_service.compare_backups(
        compare_data.backup_id_1,
        compare_data.backup_id_2
    )
    
    if diff == "Backup not found":
        raise HTTPException(status_code=404, detail="One or both backups not found")
    
    return BackupCompareResponse(
        diff=diff,
        added_lines=added,
        removed_lines=removed,
        unchanged_lines=unchanged
    )


@router.get("/router/{router_id}")
def get_router_backups(router_id: int, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")
    
    backup_service = BackupService(db)
    backups = backup_service.get_router_backups(router_id, limit)
    
    return backups
