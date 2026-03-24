from fastapi import APIRouter, Depends, Query, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime, timedelta
import re
import httpx
import jwt

from app.core.database import get_db
from app.core.security import decrypt_password
from app.models import RouterLog, Router, NotificationChannel, User
from app.schemas import RouterLogCreate, RouterLogResponse
from app.services import SSHService

router = APIRouter(prefix="/routers", tags=["Router Logs"])

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


CRITICAL_PATTERNS = [
    r'critical', r'fail', r'error', r'dropped', r'blocked',
    r'attack', r'intrusion', r'security', r'unauthorized',
    r'link down', r'interface down', r'power', r'temperature',
    r'overload', r'exceeded', r'timeout', r'denied'
]


async def send_telegram_alert(bot_token: str, chat_id: str, message: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            )
            return response.status_code == 200
    except Exception as e:
        print(f"Telegram alert failed: {e}")
        return False


async def check_and_notify_critical_logs(db: Session, router_id: int, logs_text: str, hostname: str):
    critical_found = []
    
    for line in logs_text.split('\n'):
        line_lower = line.lower()
        for pattern in CRITICAL_PATTERNS:
            if re.search(pattern, line_lower, re.IGNORECASE):
                critical_found.append(line.strip())
                break
    
    if not critical_found:
        return False
    
    critical_summary = "\n".join(critical_found[:5])
    message = f"🚨 <b>Critical Alert - {hostname}</b>\n\n{critical_summary}\n\n<i>Full logs available in Router MGMT</i>"
    
    channels = db.query(NotificationChannel).filter(
        NotificationChannel.enabled == True,
        NotificationChannel.channel_type == "telegram"
    ).all()
    
    for channel in channels:
        if "router.critical" in channel.events or "all" in channel.events:
            bot_token = channel.config.get("bot_token")
            chat_id = channel.config.get("chat_id")
            if bot_token and chat_id:
                await send_telegram_alert(bot_token, chat_id, message)
    
    return True


@router.get("/{router_id}/logs", response_model=List[RouterLogResponse])
def get_router_logs(
    router_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    level: Optional[str] = None,
    source: Optional[str] = None,
    hours: Optional[int] = None,
    db: Session = Depends(get_db)
):
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")
    
    query = db.query(RouterLog).filter(RouterLog.router_id == router_id)
    
    if level:
        query = query.filter(RouterLog.level == level)
    if source:
        query = query.filter(RouterLog.source == source)
    if hours:
        start_time = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(RouterLog.created_at >= start_time)
    
    return query.order_by(RouterLog.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/{router_id}/logs", response_model=RouterLogResponse, status_code=201)
def create_router_log(router_id: int, log_data: RouterLogCreate, db: Session = Depends(get_db)):
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")
    
    log_entry = RouterLog(
        router_id=router_id,
        level=log_data.level,
        source=log_data.source,
        message=log_data.message,
        details=log_data.details
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


@router.delete("/{router_id}/logs")
def clear_router_logs(router_id: int, db: Session = Depends(get_db)):
    db.query(RouterLog).filter(RouterLog.router_id == router_id).delete()
    db.commit()
    return {"message": "Logs cleared"}


@router.get("/logs/all", response_model=List[RouterLogResponse])
def get_all_router_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    level: Optional[str] = None,
    hours: Optional[int] = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    user = get_user_from_token(authorization)
    
    if not user:
        return []
    
    query = db.query(RouterLog)
    
    if user.role.lower() != "admin":
        router_query = db.query(Router.id)
        if user.router_ids:
            router_query = router_query.filter(Router.id.in_(user.router_ids))
        if user.project_id:
            router_query = router_query.filter(Router.project_id == user.project_id)
        
        if user.router_ids or user.project_id:
            allowed_router_ids = [r.id for r in router_query.all()]
            query = query.filter(RouterLog.router_id.in_(allowed_router_ids))
        else:
            return []
    
    if level:
        query = query.filter(RouterLog.level == level)
    if hours:
        start_time = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(RouterLog.created_at >= start_time)
    
    return query.order_by(RouterLog.created_at.desc()).offset(skip).limit(limit).all()


def get_log_command(vendor: str) -> str:
    vendor_lower = vendor.lower()
    if "cisco" in vendor_lower:
        return "show log"
    elif "juniper" in vendor_lower:
        return "show log"
    elif "mikrotik" in vendor_lower:
        return "/log print"
    elif "huawei" in vendor_lower:
        return "display logbuffer"
    elif "arista" in vendor_lower:
        return "show log"
    elif "vyos" in vendor_lower:
        return "show log"
    elif "frr" in vendor_lower:
        return "sudo vtysh -c 'show log'"
    else:
        return "show log"


@router.get("/{router_id}/device-logs")
def get_device_logs(router_id: int, lines: int = Query(100, ge=10, le=1000), db: Session = Depends(get_db)):
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
            ssh_key=router.ssh_key,
            sudo_password=decrypt_password(router.sudo_password_encrypted) if router.sudo_password_encrypted else None
        )
        
        success, conn_msg = ssh.connect()
        if not success:
            return {"success": False, "error": f"Connection failed: {conn_msg}", "logs": ""}
        
        log_cmd = get_log_command(router.vendor)
        
        if "frr" in router.vendor.lower() and ssh.sudo_password:
            success, output, error = ssh.execute_with_sudo(log_cmd.replace("sudo ", ""))
        else:
            success, output, error = ssh.execute_command(log_cmd)
        ssh.close()
        
        if success:
            log_lines = output.strip().split('\n')[-lines:]
            logs_text = '\n'.join(log_lines)
            
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(check_and_notify_critical_logs(db, router_id, logs_text, router.hostname))
            finally:
                loop.close()
            
            return {
                "success": True,
                "router_id": router_id,
                "hostname": router.hostname,
                "vendor": router.vendor,
                "command": log_cmd,
                "logs": logs_text
            }
        else:
            return {"success": False, "error": error or "Failed to fetch logs", "logs": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "logs": ""}


@router.get("/{router_id}/device-info")
def get_device_info(router_id: int, db: Session = Depends(get_db)):
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
            return {"success": False, "error": f"Connection failed: {conn_msg}"}
        
        info = {"hostname": router.hostname, "vendor": router.vendor, "commands": {}}
        
        commands = [
            ("version", "show version | include Version"),
            ("uptime", "show uptime"),
            ("interfaces", "show ip interface brief"),
            ("cpu_usage", "show processes cpu"),
            ("memory", "show memory"),
            ("arp", "show ip arp"),
        ]
        
        if "juniper" in router.vendor.lower():
            commands = [
                ("version", "show version"),
                ("uptime", "show system uptime"),
                ("interfaces", "show interface terse"),
                ("cpu_usage", "show chassis routing-engine"),
                ("memory", "show system memory"),
            ]
        elif "mikrotik" in router.vendor.lower():
            commands = [
                ("version", "/system/resource print"),
                ("uptime", "/system/resource print"),
                ("interfaces", "/interface print"),
            ]
        
        for name, cmd in commands:
            success, output, _ = ssh.execute_command(cmd)
            if success:
                info["commands"][name] = output.strip()
        
        ssh.close()
        return {"success": True, "data": info}
    except Exception as e:
        return {"success": False, "error": str(e)}
