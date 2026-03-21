from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import concurrent.futures

from app.core.database import get_db
from app.models import Router
from app.schemas import (
    BatchCommandRequest, BatchCommandResponse, BatchCommandResult
)
from app.services import SSHService
from app.core.security import decrypt_password

router = APIRouter(prefix="/batch", tags=["Batch Operations"])


def execute_on_router(router_id: int, hostname: str, ip_address: str, port: int,
                      username: str, password_encrypted: str, ssh_key: str | None,
                      command: str) -> BatchCommandResult:
    try:
        password = None
        if password_encrypted:
            try:
                password = decrypt_password(password_encrypted)
            except Exception as e:
                return BatchCommandResult(
                    router_id=router_id,
                    hostname=hostname,
                    success=False,
                    error=f"Failed to decrypt password: {str(e)}"
                )
        
        ssh = SSHService(
            host=ip_address,
            port=port,
            username=username,
            password=password,
            ssh_key=ssh_key
        )
        
        success, conn_msg = ssh.connect()
        if not success:
            return BatchCommandResult(
                router_id=router_id,
                hostname=hostname,
                success=False,
                error=f"Connection failed: {conn_msg}"
            )
        
        success, output, error = ssh.execute_command(command)
        ssh.close()
        
        return BatchCommandResult(
            router_id=router_id,
            hostname=hostname,
            success=success,
            output=output if success else None,
            error=error if not success else None
        )
    except Exception as e:
        return BatchCommandResult(
            router_id=router_id,
            hostname=hostname,
            success=False,
            error=str(e)
        )


@router.post("/command", response_model=BatchCommandResponse)
def batch_command(request: BatchCommandRequest, db: Session = Depends(get_db)):
    routers = db.query(Router).filter(Router.id.in_(request.router_ids)).all()
    
    if len(routers) != len(request.router_ids):
        found_ids = {r.id for r in routers}
        missing = set(request.router_ids) - found_ids
        raise HTTPException(
            status_code=404,
            detail=f"Routers not found: {missing}"
        )
    
    results = []
    
    for r in routers:
        result = execute_on_router(
            r.id,
            r.hostname,
            r.ip_address,
            r.port,
            r.username,
            r.password_encrypted,
            r.ssh_key,
            request.command
        )
        results.append(result)
    
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    
    return BatchCommandResponse(
        results=results,
        total=len(results),
        successful=successful,
        failed=failed
    )
