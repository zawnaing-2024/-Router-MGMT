from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models import RemediationScript
from app.schemas import (
    RemediationScriptCreate, RemediationScriptUpdate, RemediationScriptResponse
)

router = APIRouter(prefix="/remediation", tags=["Remediation"])


@router.get("", response_model=List[RemediationScriptResponse])
def list_scripts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(RemediationScript).offset(skip).limit(limit).all()


@router.get("/{script_id}", response_model=RemediationScriptResponse)
def get_script(script_id: int, db: Session = Depends(get_db)):
    script = db.query(RemediationScript).filter(RemediationScript.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Remediation script not found")
    return script


@router.post("", response_model=RemediationScriptResponse, status_code=201)
def create_script(data: RemediationScriptCreate, db: Session = Depends(get_db)):
    script = RemediationScript(**data.model_dump())
    db.add(script)
    db.commit()
    db.refresh(script)
    return script


@router.put("/{script_id}", response_model=RemediationScriptResponse)
def update_script(script_id: int, data: RemediationScriptUpdate, db: Session = Depends(get_db)):
    script = db.query(RemediationScript).filter(RemediationScript.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Remediation script not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(script, key, value)
    
    db.commit()
    db.refresh(script)
    return script


@router.delete("/{script_id}", status_code=204)
def delete_script(script_id: int, db: Session = Depends(get_db)):
    script = db.query(RemediationScript).filter(RemediationScript.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Remediation script not found")
    
    db.delete(script)
    db.commit()


@router.post("/{script_id}/run/{router_id}")
def run_script(script_id: int, router_id: int, db: Session = Depends(get_db)):
    from app.models import Router
    from app.services import SSHService
    from app.core.security import decrypt_password
    
    script = db.query(RemediationScript).filter(RemediationScript.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Remediation script not found")
    
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
        
        success, _ = ssh.connect()
        if not success:
            return {"success": False, "error": "Connection failed"}
        
        results = []
        for command in script.commands:
            success, output, error = ssh.execute_command(command)
            results.append({
                "command": command,
                "success": success,
                "output": output,
                "error": error
            })
        
        ssh.close()
        
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}
