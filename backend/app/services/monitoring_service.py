from typing import Optional, Dict, Any, Tuple
import re
from app.services.ssh_service import SSHService


class MonitoringService:
    VENDOR_COMMANDS = {
        "mikrotik_routeros": {
            "cpu": "/system/resource print",
            "parse": "cpu-load"
        },
        "cisco_ios": {
            "cpu": "show processes cpu | include CPU",
            "memory": "show memory"
        },
        "cisco_ios_xe": {
            "cpu": "show processes cpu | include CPU",
            "memory": "show memory"
        },
        "juniper_junos": {
            "system": "show system resources"
        },
        "frr_linux": {
            "version": "show version",
            "memory": "show memory",
            "interface": "show interface"
        },
        "generic": {
            "system": "top -n 1 | head -5"
        }
    }

    def __init__(self, ssh: SSHService):
        self.ssh = ssh

    def _parse_uptime(self, uptime_str: str) -> int:
        if not uptime_str:
            return 0
        
        total_seconds = 0
        weeks = re.search(r'(\d+)w', uptime_str)
        days = re.search(r'(\d+)d', uptime_str)
        hours = re.search(r'(\d+)h', uptime_str)
        minutes = re.search(r'(\d+)m', uptime_str)
        seconds = re.search(r'(\d+)s', uptime_str)
        
        if weeks: total_seconds += int(weeks.group(1)) * 604800
        if days: total_seconds += int(days.group(1)) * 86400
        if hours: total_seconds += int(hours.group(1)) * 3600
        if minutes: total_seconds += int(minutes.group(1)) * 60
        if seconds: total_seconds += int(seconds.group(1))
        
        return total_seconds

    def collect_metrics(self, vendor: str) -> Dict[str, Any]:
        vendor = vendor.lower()
        
        if vendor == "mikrotik_routeros":
            return self._collect_mikrotik()
        elif vendor in ("cisco_ios", "cisco_ios_xe"):
            return self._collect_cisco()
        elif vendor == "juniper_junos":
            return self._collect_juniper()
        elif vendor == "frr_linux":
            return self._collect_frr()
        else:
            return self._collect_generic()

    def _collect_mikrotik(self) -> Dict[str, Any]:
        success, output, error = self.ssh.execute_command(
            "/system/resource print",
            timeout=10
        )
        
        if not success:
            return {"error": error}

        metrics = {}
        uptime_str = ""
        
        for line in output.split('\n'):
            line = line.strip()
            if ':' not in line:
                continue
            
            parts = line.split(':', 1)
            if len(parts) != 2:
                continue
            
            key = parts[0].strip().lower()
            value = parts[1].strip()
            
            if 'cpu-load' in key or key == 'cpu load':
                match = re.search(r'(\d+)%', value)
                if match:
                    metrics['cpu_percent'] = int(match.group(1))
            elif 'total-memory' in key or key == 'total memory':
                match = re.search(r'([\d.]+)', value)
                if match:
                    total_str = value.replace('MiB', '').replace('GiB', '').strip()
                    if 'GiB' in value:
                        metrics['memory_total_mb'] = int(float(total_str) * 1024)
                    else:
                        metrics['memory_total_mb'] = int(float(total_str))
            elif 'free-memory' in key or key == 'free memory':
                match = re.search(r'([\d.]+)', value)
                if match:
                    free_str = value.replace('MiB', '').replace('GiB', '').strip()
                    if 'GiB' in value:
                        metrics['memory_free_mb'] = int(float(free_str) * 1024)
                    else:
                        metrics['memory_free_mb'] = int(float(free_str))
            elif 'uptime' in key:
                uptime_str = value
            elif 'version' in key:
                metrics['version'] = value

        if 'memory_total_mb' in metrics and 'memory_free_mb' in metrics:
            metrics['memory_used_mb'] = metrics['memory_total_mb'] - metrics['memory_free_mb']
            metrics['memory_percent'] = int(
                (metrics['memory_used_mb'] / metrics['memory_total_mb']) * 100
            )

        metrics['uptime_seconds'] = self._parse_uptime(uptime_str)

        if not metrics:
            return {"error": f"No metrics parsed. Output: {output[:500]}"}

        return metrics

    def _collect_cisco(self) -> Dict[str, Any]:
        metrics = {}

        success, cpu_out, _ = self.ssh.execute_command(
            "show processes cpu | include CPU",
            timeout=10
        )
        
        if success and cpu_out:
            match = re.search(r'(\d+)%.*?(\d+)%', cpu_out)
            if match:
                metrics['cpu_percent'] = int(match.group(2))

        success, mem_out, _ = self.ssh.execute_command(
            "show memory | include Processor",
            timeout=10
        )
        
        if success and mem_out:
            parts = mem_out.split()
            if len(parts) >= 3:
                try:
                    total = int(parts[1]) // 1024
                    used = int(parts[2]) // 1024
                    metrics['memory_total_mb'] = total
                    metrics['memory_used_mb'] = used
                    metrics['memory_percent'] = int((used / total) * 100)
                except (ValueError, IndexError):
                    pass

        return metrics

    def _collect_juniper(self) -> Dict[str, Any]:
        success, output, _ = self.ssh.execute_command(
            "show system resources",
            timeout=10
        )
        
        if not success:
            return {"error": output}

        metrics = {}
        for line in output.split('\n'):
            if 'CPU' in line and '%' in line:
                match = re.search(r'CPU\s*(\d+)%', line)
                if match:
                    metrics['cpu_percent'] = int(match.group(1))
            elif 'Memory' in line:
                match = re.search(r'(\d+)%', line)
                if match and 'memory_percent' not in metrics:
                    metrics['memory_percent'] = int(match.group(1))

        return metrics

    def _collect_frr(self) -> Dict[str, Any]:
        metrics = {}

        success, version_out, _ = self.ssh.execute_command(
            "sudo vtysh -c 'show version'",
            timeout=10
        )
        
        if success and version_out:
            for line in version_out.split('\n'):
                line = line.strip()
                if 'FRRouting' in line or 'FRR' in line:
                    match = re.search(r'FRRouting\s+([\d.]+)', line)
                    if match:
                        metrics['version'] = match.group(1)
                        break
                elif 'uptime' in line.lower() or 'Uptime' in line:
                    parts = line.split('uptime')
                    if len(parts) > 1:
                        uptime_str = parts[1].strip()
                        metrics['uptime_seconds'] = self._parse_uptime(uptime_str)

        success, mem_out, _ = self.ssh.execute_command(
            "sudo vtysh -c 'show memory'",
            timeout=10
        )
        
        if success and mem_out:
            for line in mem_out.split('\n'):
                line = line.strip()
                if 'Total' in line and 'MB' in line:
                    match = re.findall(r'(\d+)', line)
                    if len(match) >= 2:
                        metrics['memory_total_mb'] = int(match[0])
                        metrics['memory_used_mb'] = int(match[1])
                        if int(match[0]) > 0:
                            metrics['memory_percent'] = int((int(match[1]) / int(match[0])) * 100)

        success, int_out, _ = self.ssh.execute_command(
            "cat /proc/loadavg",
            timeout=5
        )
        
        if success and int_out:
            parts = int_out.strip().split()
            if len(parts) >= 3:
                metrics['load_average_1m'] = float(parts[0])
                metrics['load_average_5m'] = float(parts[1])

        success, cpu_out, _ = self.ssh.execute_command(
            "top -bn1 | head -3",
            timeout=5
        )
        
        if success and cpu_out:
            for line in cpu_out.split('\n'):
                if 'Cpu' in line or 'cpu' in line:
                    match = re.search(r'(\d+\.?\d*)\s*id', line)
                    if match:
                        idle = float(match.group(1))
                        metrics['cpu_percent'] = int(100 - idle)
                    break

        if not metrics:
            return {"error": "Could not collect FRR metrics"}
        
        return metrics

    def _collect_generic(self) -> Dict[str, Any]:
        success, output, _ = self.ssh.execute_command(
            "top -bn1 | head -5",
            timeout=10
        )
        
        if not success:
            return {"error": output}

        metrics = {}
        for line in output.split('\n'):
            if 'Cpu' in line or 'cpu' in line:
                match = re.search(r'(\d+\.?\d*)\s*id', line)
                if match:
                    idle = float(match.group(1))
                    metrics['cpu_percent'] = int(100 - idle)
            elif 'Mem' in line:
                parts = re.findall(r'\d+', line)
                if len(parts) >= 4:
                    total, used, free, buff = map(int, parts[:4])
                    metrics['memory_total_mb'] = total // 1024
                    metrics['memory_used_mb'] = used // 1024
                    metrics['memory_percent'] = int((used / total) * 100)

        return metrics


def collect_router_metrics(
    host: str,
    port: int,
    username: str,
    password: Optional[str],
    vendor: str
) -> Tuple[bool, Dict[str, Any]]:
    ssh = SSHService(
        host=host,
        port=port,
        username=username,
        password=password
    )
    
    try:
        success, message = ssh.connect()
        if not success:
            return False, {"error": message}
        
        monitor = MonitoringService(ssh)
        metrics = monitor.collect_metrics(vendor)
        
        if "error" in metrics:
            return False, metrics
        
        return True, metrics
    except Exception as e:
        return False, {"error": str(e)}
    finally:
        ssh.close()
