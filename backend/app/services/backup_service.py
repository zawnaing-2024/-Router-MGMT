import hashlib
import os
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import Router, ConfigBackup, RouterStatus
from app.services.ssh_service import SSHService
from app.core.security import decrypt_password
from app.core.config import settings


class BackupService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_backup(self, router_id: int, content: str, source: str = "manual") -> ConfigBackup:
        checksum = hashlib.sha256(content.encode()).hexdigest()
        size_bytes = len(content.encode())
        
        router = self.db.query(Router).filter(Router.id == router_id).first()
        filename = self._generate_filename(router.hostname if router else f"router{router_id}", source)
        
        backup = ConfigBackup(
            router_id=router_id,
            content=content,
            checksum=checksum,
            source=source,
            size_bytes=size_bytes,
            filename=filename
        )
        
        self.db.add(backup)
        self.db.commit()
        self.db.refresh(backup)
        
        self._update_router_last_seen(router_id)
        
        return backup
    
    def _generate_filename(self, hostname: str, source: str) -> str:
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M")
        source_suffix = "manual" if source == "manual" else "auto"
        return f"{hostname}_{timestamp}_{source_suffix}.cfg"
    
    def backup_router(self, router_id: int, source: str = "manual") -> tuple[bool, str, Optional[ConfigBackup]]:
        router = self.db.query(Router).filter(Router.id == router_id).first()
        if not router:
            return False, "Router not found", None
        
        try:
            password = decrypt_password(router.password_encrypted)
            
            ssh = SSHService(
                host=router.ip_address,
                port=router.port,
                username=router.username,
                password=password,
                ssh_key=router.ssh_key
            )
            
            success, message = ssh.connect()
            if not success:
                self._update_router_status(router_id, RouterStatus.OFFLINE)
                return False, f"Connection failed: {message}", None
            
            success, config = ssh.get_config(router.vendor)
            ssh.close()
            
            if not success:
                return False, f"Failed to get config: {config}", None
            
            backup = self.create_backup(router_id, config, source)
            self._update_router_status(router_id, RouterStatus.ONLINE)
            
            return True, "Backup created successfully", backup
            
        except Exception as e:
            self._update_router_status(router_id, RouterStatus.WARNING)
            return False, str(e), None
    
    def restore_config(self, router_id: int, backup_id: int) -> tuple[bool, str]:
        router = self.db.query(Router).filter(Router.id == router_id).first()
        if not router:
            return False, "Router not found"
        
        backup = self.db.query(ConfigBackup).filter(
            ConfigBackup.id == backup_id,
            ConfigBackup.router_id == router_id
        ).first()
        
        if not backup:
            return False, "Backup not found"
        
        try:
            password = decrypt_password(router.password_encrypted)
            
            ssh = SSHService(
                host=router.ip_address,
                port=router.port,
                username=router.username,
                password=password,
                ssh_key=router.ssh_key
            )
            
            success, message = ssh.connect()
            if not success:
                return False, f"Connection failed: {message}"
            
            commands = self._generate_config_commands(router.vendor, backup.content)
            
            for cmd in commands:
                success, output, error = ssh.execute_command(cmd)
                if not success:
                    ssh.close()
                    return False, f"Command failed: {cmd}\n{error}"
            
            ssh.close()
            return True, "Configuration restored successfully"
            
        except Exception as e:
            return False, str(e)
    
    def compare_backups(self, backup_id_1: int, backup_id_2: int) -> tuple[str, int, int, int]:
        backup1 = self.db.query(ConfigBackup).filter(ConfigBackup.id == backup_id_1).first()
        backup2 = self.db.query(ConfigBackup).filter(ConfigBackup.id == backup_id_2).first()
        
        if not backup1 or not backup2:
            return "Backup not found", 0, 0, 0
        
        lines1 = backup1.content.splitlines()
        lines2 = backup2.content.splitlines()
        
        added = set(lines2) - set(lines1)
        removed = set(lines1) - set(lines2)
        unchanged = set(lines1) & set(lines2)
        
        diff_lines = []
        diff_lines.append("--- Backup {} ({})\n".format(backup_id_1, backup1.created_at))
        diff_lines.append("+++ Backup {} ({})\n".format(backup_id_2, backup2.created_at))
        
        for line in sorted(removed):
            diff_lines.append(f"- {line}")
        for line in sorted(added):
            diff_lines.append(f"+ {line}")
        
        return "\n".join(diff_lines), len(added), len(removed), len(unchanged)
    
    def get_router_backups(self, router_id: int, limit: int = 50) -> List[ConfigBackup]:
        return self.db.query(ConfigBackup).filter(
            ConfigBackup.router_id == router_id
        ).order_by(ConfigBackup.created_at.desc()).limit(limit).all()
    
    def _generate_config_commands(self, vendor: str, config: str) -> List[str]:
        lines = config.strip().splitlines()
        
        if vendor in ["cisco_ios", "cisco_ios_xe", "arista_eos"]:
            return ["config terminal"] + [line for line in lines if line.strip()] + ["end", "write memory"]
        elif vendor == "juniper_junos":
            return ["configure", "load set " + "\n".join(lines), "commit"]
        elif vendor == "mikrotik_routeros":
            return [f"/configuration/reset"]
        else:
            return [line for line in lines if line.strip()]
    
    def _update_router_status(self, router_id: int, status: RouterStatus):
        router = self.db.query(Router).filter(Router.id == router_id).first()
        if router:
            router.status = status
            router.last_seen = datetime.utcnow()
            self.db.commit()
    
    def _update_router_last_seen(self, router_id: int):
        router = self.db.query(Router).filter(Router.id == router_id).first()
        if router:
            router.last_seen = datetime.utcnow()
            router.status = RouterStatus.ONLINE
            self.db.commit()
