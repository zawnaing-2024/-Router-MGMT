import paramiko
import socket
import time
from typing import Optional, Tuple
from app.core.config import settings
from app.core.security import decrypt_password


class SSHService:
    def __init__(self, host: str, port: int, username: str, password: Optional[str] = None, ssh_key: Optional[str] = None, sudo_password: Optional[str] = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.ssh_key = ssh_key
        self.sudo_password = sudo_password
        self.client: Optional[paramiko.SSHClient] = None
    
    def connect(self) -> Tuple[bool, str]:
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "timeout": settings.SSH_TIMEOUT,
                "look_for_keys": False,
                "allow_agent": False,
            }
            
            if self.ssh_key:
                connect_kwargs["key_filename"] = self.ssh_key
            elif self.password:
                connect_kwargs["password"] = self.password
            
            start_time = time.time()
            self.client.connect(**connect_kwargs)
            latency = (time.time() - start_time) * 1000
            
            return True, f"Connected in {latency:.2f}ms"
        except Exception as e:
            return False, str(e)
    
    def execute_command(self, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        if not self.client:
            return False, "", "Not connected"
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            output = stdout.read().decode("utf-8", errors="replace")
            error = stderr.read().decode("utf-8", errors="replace")
            exit_status = stdout.channel.recv_exit_status()
            
            return exit_status == 0, output, error
        except Exception as e:
            return False, "", str(e)
    
    def execute_with_sudo(self, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        if not self.client:
            return False, "", "Not connected"
        
        try:
            full_command = f"echo '{self.sudo_password}' | sudo -S {command}"
            stdin, stdout, stderr = self.client.exec_command(full_command, timeout=timeout)
            output = stdout.read().decode("utf-8", errors="replace")
            error = stderr.read().decode("utf-8", errors="replace")
            exit_status = stdout.channel.recv_exit_status()
            
            return exit_status == 0, output, error
        except Exception as e:
            return False, "", str(e)
    
    def get_config(self, vendor: str) -> Tuple[bool, str]:
        command_map = {
            "cisco_ios": "show running-config",
            "cisco_ios_xe": "show running-config",
            "juniper_junos": "show configuration | display set",
            "mikrotik_routeros": "/export",
            "huawei": "display current-configuration",
            "arista_eos": "show running-config",
            "vyos": "show configuration",
        }
        
        command = command_map.get(vendor, "show running-config")
        success, output, error = self.execute_command(command, timeout=60)
        
        if success:
            return True, output
        return False, error or "Failed to retrieve config"
    
    def close(self):
        if self.client:
            self.client.close()
            self.client = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def test_connection(
    host: str,
    port: int,
    username: str,
    password: Optional[str] = None,
    ssh_key: Optional[str] = None
) -> Tuple[bool, str, Optional[float]]:
    ssh = SSHService(host, port, username, password, ssh_key)
    try:
        success, message = ssh.connect()
        if success:
            return True, message, None
        return False, message, None
    finally:
        ssh.close()


def check_router_reachable(host: str, port: int = 22) -> Tuple[bool, float]:
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        latency = (time.time() - start) * 1000
        return result == 0, latency
    except Exception:
        return False, 0.0
