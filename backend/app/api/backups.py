from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models import ConfigBackup, Router
from app.schemas import (
    ConfigBackupResponse, ConfigBackupDetailResponse,
    BackupCompareRequest, BackupCompareResponse
)
from app.services import BackupService

router = APIRouter(prefix="/backups", tags=["Backups"])


@router.get("", response_model=List[ConfigBackupResponse])
def list_backups(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    router_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ConfigBackup)
    
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
