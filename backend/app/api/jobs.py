from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime
import jwt

from app.core.database import get_db
from app.models import ScheduledJob, Router, RouterStatus, JobStatus, PingMetric, User
from app.schemas import (
    ScheduledJobCreate, ScheduledJobUpdate, ScheduledJobResponse
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])

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


@router.get("", response_model=List[ScheduledJobResponse])
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    enabled: Optional[bool] = None,
    job_type: Optional[str] = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    user = get_user_from_token(authorization)
    
    if not user:
        return []
    
    query = db.query(ScheduledJob)
    
    if user.role.lower() != "admin":
        router_query = db.query(Router.id)
        if user.router_ids:
            router_query = router_query.filter(Router.id.in_(user.router_ids))
        if user.project_id:
            router_query = router_query.filter(Router.project_id == user.project_id)
        
        if user.router_ids or user.project_id:
            allowed_router_ids = [r.id for r in router_query.all()]
            query = query.filter(ScheduledJob.router_id.in_(allowed_router_ids))
        else:
            return []
    
    if enabled is not None:
        query = query.filter(ScheduledJob.enabled == enabled)
    if job_type:
        query = query.filter(ScheduledJob.job_type == job_type)
    
    return query.order_by(ScheduledJob.name).offset(skip).limit(limit).all()


@router.get("/{job_id}", response_model=ScheduledJobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("", response_model=ScheduledJobResponse, status_code=201)
def create_job(job_data: ScheduledJobCreate, db: Session = Depends(get_db)):
    if job_data.router_id:
        router_obj = db.query(Router).filter(Router.id == job_data.router_id).first()
        if not router_obj:
            raise HTTPException(status_code=400, detail="Router not found")
    
    job = ScheduledJob(
        name=job_data.name,
        job_type=job_data.job_type,
        router_id=job_data.router_id,
        template_id=job_data.template_id,
        command=job_data.command,
        schedule=job_data.schedule,
        enabled=True,
        ping_target=job_data.ping_target,
        ping_source=job_data.ping_source,
        ping_count=job_data.ping_count
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.put("/{job_id}", response_model=ScheduledJobResponse)
def update_job(job_id: int, job_data: ScheduledJobUpdate, db: Session = Depends(get_db)):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    update_data = job_data.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(job, key, value)
    
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    db.delete(job)
    db.commit()


@router.post("/{job_id}/run")
def run_job_now(job_id: int, db: Session = Depends(get_db)):
    from app.services import BackupService
    from app.core.security import decrypt_password
    from app.services.ssh_service import SSHService
    
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.last_run = datetime.utcnow()
    job.last_status = JobStatus.RUNNING
    db.commit()
    
    try:
        if job.job_type.value == "backup":
            backup_service = BackupService(db)
            success, message, _ = backup_service.backup_router(job.router_id, "scheduled")
            job.last_status = JobStatus.SUCCESS if success else JobStatus.FAILED
            job.last_output = message
        
        elif job.job_type.value == "command":
            if not job.router_id:
                raise ValueError("No router specified for command job")
            
            router_obj = db.query(Router).filter(Router.id == job.router_id).first()
            password = decrypt_password(router_obj.password_encrypted) if router_obj.password_encrypted else None
            
            ssh = SSHService(
                host=router_obj.ip_address,
                port=router_obj.port,
                username=router_obj.username,
                password=password
            )
            
            success, ssh_msg = ssh.connect()
            if not success:
                raise Exception(f"SSH connection failed: {ssh_msg}")
            
            success, output, error = ssh.execute_command(job.command, timeout=30)
            ssh.close()
            
            job.last_output = output if success else error
            job.last_status = JobStatus.SUCCESS if success else JobStatus.FAILED
        
        elif job.job_type.value == "ping":
            if not job.router_id or not job.ping_target:
                raise ValueError("Router and ping target are required")
            
            router_obj = db.query(Router).filter(Router.id == job.router_id).first()
            password = decrypt_password(router_obj.password_encrypted) if router_obj.password_encrypted else None
            
            ssh = SSHService(
                host=router_obj.ip_address,
                port=router_obj.port,
                username=router_obj.username,
                password=password
            )
            
            success, ssh_msg = ssh.connect()
            if not success:
                raise Exception(f"SSH connection failed: {ssh_msg}")
            
            ping_cmd = generate_ping_command(router_obj.vendor, job.ping_target, job.ping_source, job.ping_count)
            success, output, error = ssh.execute_command(ping_cmd, timeout=30)
            ssh.close()
            
            job.last_output = output if success else error
            job.last_status = JobStatus.SUCCESS if success else JobStatus.FAILED
            
            ping_metric = parse_ping_output(job.router_id, job.id, job.ping_target, output)
            if ping_metric:
                db.add(ping_metric)
        
        else:
            job.last_status = JobStatus.SUCCESS
            job.last_output = "Job type not implemented"
        
        db.commit()
        return {"success": True, "message": job.last_output}
    except Exception as e:
        job.last_status = JobStatus.FAILED
        job.last_output = str(e)
        db.commit()
        return {"success": False, "message": str(e)}


def generate_ping_command(vendor: str, target: str, source: Optional[str], count: int) -> str:
    if vendor == "mikrotik_routeros":
        cmd = f"/ping {target} count={count}"
        if source:
            cmd += f" src-address={source}"
        return cmd
    elif vendor in ("cisco_ios", "cisco_ios_xe", "arista_eos"):
        cmd = f"ping {target} repeat {count}"
        if source:
            cmd = f"ping {target} source {source} repeat {count}"
        return cmd
    elif vendor == "juniper_junos":
        cmd = f"ping {target} count {count}"
        if source:
            cmd = f"ping {target} source {source} count {count}"
        return cmd
    else:
        cmd = f"ping -c {count} {target}"
        if source:
            cmd = f"ping -I {source} -c {count} {target}"
        return cmd


def parse_ping_output(router_id: int, job_id: int, target: str, output: str) -> Optional[PingMetric]:
    import re
    from datetime import datetime
    
    metric = PingMetric(
        router_id=router_id,
        job_id=job_id,
        target=target,
        collected_at=datetime.utcnow()
    )
    
    if not output:
        metric.packet_loss_percent = 100
        return metric
    
    packet_loss_match = re.search(r'packet-loss[=:]?\s*(\d+)%', output, re.IGNORECASE)
    if packet_loss_match:
        metric.packet_loss_percent = int(packet_loss_match.group(1))
    
    sent_match = re.search(r'sent[=:]?\s*(\d+)', output, re.IGNORECASE)
    if sent_match:
        metric.packets_sent = int(sent_match.group(1))
    
    received_match = re.search(r'(?:received|rcvd)[=:]?\s*(\d+)', output, re.IGNORECASE)
    if received_match:
        metric.packets_received = int(received_match.group(1))
    
    avg_match = re.search(r'(?:avg-rtt|average|avg)[=:]?\s*(\d+)ms|(\d+)m?s', output, re.IGNORECASE)
    if avg_match:
        if avg_match.group(1):
            metric.latency_avg_ms = int(avg_match.group(1))
        elif avg_match.group(2):
            metric.latency_avg_ms = int(avg_match.group(2))
    
    avg_rtt_match = re.search(r'avg-rtt[=:]?\s*(\d+)ms(\d+)us|(\d+)ms', output, re.IGNORECASE)
    if avg_rtt_match:
        if avg_rtt_match.group(1) and avg_rtt_match.group(2):
            metric.latency_avg_ms = int(avg_rtt_match.group(1))
        elif avg_rtt_match.group(3):
            metric.latency_avg_ms = int(avg_rtt_match.group(3))
    
    min_match = re.search(r'min-rtt[=:]?\s*(\d+)ms(\d+)us|min[=:]?\s*(\d+)', output, re.IGNORECASE)
    if min_match:
        if min_match.group(1):
            metric.latency_min_ms = int(min_match.group(1))
        elif min_match.group(3):
            metric.latency_min_ms = int(min_match.group(3))
    
    max_match = re.search(r'max-rtt[=:]?\s*(\d+)ms(\d+)us|max[=:]?\s*(\d+)', output, re.IGNORECASE)
    if max_match:
        if max_match.group(1):
            metric.latency_max_ms = int(max_match.group(1))
        elif max_match.group(3):
            metric.latency_max_ms = int(max_match.group(3))
    
    time_match = re.search(r'TIME\s+(\d+)ms', output, re.IGNORECASE)
    if time_match and not metric.latency_avg_ms:
        metric.latency_avg_ms = int(time_match.group(1))
    
    return metric
