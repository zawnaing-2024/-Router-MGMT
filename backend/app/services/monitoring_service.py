from typing import Optional, Dict, Any, Tuple, List
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
        
        week_match = re.search(r'(\d+)\s*w', uptime_str)
        if week_match:
            total_seconds += int(week_match.group(1)) * 604800
        
        day_match = re.search(r'(\d+)\s*d', uptime_str)
        if day_match:
            total_seconds += int(day_match.group(1)) * 86400
        else:
            day_word_match = re.search(r'(\d+)\s*day', uptime_str)
            if day_word_match:
                total_seconds += int(day_word_match.group(1)) * 86400
        
        hour_min_match = re.search(r'(\d+):(\d+)', uptime_str)
        if hour_min_match:
            total_seconds += int(hour_min_match.group(1)) * 3600
            total_seconds += int(hour_min_match.group(2)) * 60
        else:
            hour_match = re.search(r'(\d+)\s*h', uptime_str)
            if hour_match:
                total_seconds += int(hour_match.group(1)) * 3600
            else:
                hour_word_match = re.search(r'(\d+)\s*hour', uptime_str)
                if hour_word_match:
                    total_seconds += int(hour_word_match.group(1)) * 3600
            
            min_match = re.search(r'(\d+)\s*m(?!in)', uptime_str)
            if min_match:
                total_seconds += int(min_match.group(1)) * 60
            else:
                min_word_match = re.search(r'(\d+)\s*min', uptime_str)
                if min_word_match:
                    total_seconds += int(min_word_match.group(1)) * 60
        
        sec_match = re.search(r'(\d+)\s*s', uptime_str)
        if sec_match:
            total_seconds += int(sec_match.group(1))
        
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
    
    def _collect_mikrotik_interfaces(self) -> List[Dict[str, Any]]:
        success, output, _ = self.ssh.execute_command(
            "/interface print terse",
            timeout=10
        )
        if not success:
            return []
        
        interfaces = []
        for line in output.strip().split('\n'):
            if not line.strip() or 'Flags' in line:
                continue
            parts = line.split()
            if len(parts) >= 1:
                name = parts[0]
                state = "UP" if "X" not in line and "R" in line else "DOWN"
                interfaces.append({
                    'name': name,
                    'state': state,
                    'ip': 'N/A'
                })
        
        if not interfaces:
            success, output, _ = self.ssh.execute_command(
                "/interface print",
                timeout=10
            )
            if success:
                for line in output.strip().split('\n'):
                    if not line.strip() or 'Flags' in line or '#' in line:
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        interfaces.append({
                            'name': parts[1] if len(parts) > 1 else parts[0],
                            'state': 'UP' if 'X' not in line else 'DOWN',
                            'ip': 'N/A'
                        })
        
        return interfaces
    
    def _collect_cisco_interfaces(self) -> List[Dict[str, Any]]:
        success, output, _ = self.ssh.execute_command(
            "show ip interface brief",
            timeout=10
        )
        if not success:
            return []
        
        interfaces = []
        for line in output.strip().split('\n'):
            if 'Interface' in line or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                interfaces.append({
                    'name': parts[0],
                    'state': 'UP' if parts[1] == 'up' else 'DOWN',
                    'ip': parts[3] if len(parts) > 3 and parts[3] != 'unassigned' else 'N/A'
                })
        return interfaces
    
    def _collect_juniper_interfaces(self) -> List[Dict[str, Any]]:
        success, output, _ = self.ssh.execute_command(
            "show interfaces terse",
            timeout=10
        )
        if not success:
            return []
        
        interfaces = []
        for line in output.strip().split('\n'):
            if not line.strip() or 'Interface' in line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                state = "UP" if 'up' in line else "DOWN"
                ip = 'N/A'
                for p in parts:
                    if '/' in p and ('.' in p or ':' in p):
                        ip = p
                        break
                interfaces.append({
                    'name': name,
                    'state': state,
                    'ip': ip
                })
        return interfaces
    
    def _collect_cisco_bgp(self) -> List[Dict[str, Any]]:
        success, output, _ = self.ssh.execute_command(
            "show ip bgp summary",
            timeout=15
        )
        if not success:
            return []
        
        peers = []
        for line in output.strip().split('\n'):
            if any(asn in line for asn in ['Neighbor', 'AS', 'Table']) or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 3 and ('.' in parts[0] or ':' in parts[0]):
                state = 'Established' if parts[2] != 'Idle' else 'Idle'
                peers.append({
                    'neighbor': parts[0],
                    'state': state,
                    'asn': parts[1] if len(parts) > 1 else 'N/A'
                })
        return peers
    
    def _collect_juniper_bgp(self) -> List[Dict[str, Any]]:
        success, output, _ = self.ssh.execute_command(
            "show bgp summary",
            timeout=15
        )
        if not success:
            return []
        
        peers = []
        for line in output.strip().split('\n'):
            if not line.strip() or 'Peer' in line or 'AS' in line:
                continue
            parts = line.split()
            if len(parts) >= 3:
                peer = parts[0] if '.' in parts[0] or ':' in parts[0] else 'N/A'
                state = 'Established' if parts[1] != '0' else 'Idle'
                peers.append({
                    'neighbor': peer,
                    'state': state,
                    'asn': parts[-1] if len(parts) > 2 else 'N/A'
                })
        return peers

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

        interfaces = self._collect_mikrotik_interfaces()
        if interfaces:
            metrics['interfaces'] = interfaces

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

        interfaces = self._collect_cisco_interfaces()
        if interfaces:
            metrics['interfaces'] = interfaces
        
        bgp_peers = self._collect_cisco_bgp()
        if bgp_peers:
            metrics['bgp_peers'] = bgp_peers

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

        interfaces = self._collect_juniper_interfaces()
        if interfaces:
            metrics['interfaces'] = interfaces
        
        bgp_peers = self._collect_juniper_bgp()
        if bgp_peers:
            metrics['bgp_peers'] = bgp_peers

        return metrics

    def _collect_frr(self) -> Dict[str, Any]:
        metrics = {}

        success, uptime_out, _ = self.ssh.execute_command("uptime")
        if success and uptime_out:
            uptime_line = uptime_out.strip()
            match = re.search(r'up\s+(\d+)\s*days?[,\s]+(\d+):(\d+)', uptime_line)
            if match:
                days = int(match.group(1))
                hours = int(match.group(2))
                mins = int(match.group(3))
                metrics['uptime_seconds'] = days * 86400 + hours * 3600 + mins * 60

        success, mem_out, _ = self.ssh.execute_command("free -m")
        if success and mem_out:
            for line in mem_out.split('\n'):
                if 'Mem:' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        mem_total = int(parts[1])
                        mem_used = int(parts[2])
                        if mem_total > 0:
                            metrics['memory_total_mb'] = mem_total
                            metrics['memory_used_mb'] = mem_used
                            metrics['memory_percent'] = int((mem_used / mem_total) * 100)
                    break

        success, int_out, _ = self.ssh.execute_command(
            "cat /proc/loadavg",
            timeout=5
        )
        
        if success and int_out:
            parts = int_out.strip().split()
            if len(parts) >= 3:
                metrics['load_average_1m'] = float(parts[0])
                metrics['load_average_5m'] = float(parts[1])

        success, top_out, _ = self.ssh.execute_command(
            "ps aux --noheaders -o %cpu | awk '{sum+=$1} END {print sum}'",
            timeout=5
        )
        if success and top_out:
            try:
                total_cpu = float(top_out.strip())
                metrics['cpu_percent'] = min(100, max(0, int(total_cpu)))
            except (ValueError, IndexError):
                pass
        
        if 'cpu_percent' not in metrics:
            success, top_out, _ = self.ssh.execute_command(
                "top -bn1 | head -3",
                timeout=5
            )
            if success and top_out:
                for line in top_out.split('\n'):
                    line_lower = line.lower()
                    if 'cpu' in line_lower:
                        match = re.search(r'(\d+\.?\d*)\s*(?:us|sy|id|%cpu)', line_lower)
                        if match:
                            usage = float(match.group(1))
                            if usage < 100:
                                metrics['cpu_percent'] = min(100, max(0, int(usage)))
                                break

        if not metrics:
            return {"error": "Could not collect FRR metrics"}
        
        interfaces = self._collect_frr_interfaces()
        if interfaces:
            metrics['interfaces'] = interfaces
        
        bgp_peers = self._collect_frr_bgp()
        if bgp_peers:
            metrics['bgp_peers'] = bgp_peers
        
        return metrics
    
    def _collect_frr_interfaces(self) -> List[Dict[str, Any]]:
        success, output, _ = self.ssh.execute_command(
            "ip -br addr show",
            timeout=10
        )
        if not success:
            return []
        
        interfaces = []
        for line in output.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 2:
                iface = {
                    'name': parts[0],
                    'state': parts[1] if len(parts) > 1 else 'UNKNOWN',
                    'ip': parts[2] if len(parts) > 2 else 'N/A',
                    'description': '',
                    'speed_mbps': 0,
                    'tx_bps': 0,
                    'rx_bps': 0,
                    'tx_bpsHuman': '0',
                    'rx_bpsHuman': '0',
                    'tx_bytes': 0,
                    'rx_bytes': 0,
                    'tx_packets': 0,
                    'rx_packets': 0,
                    'tx_errors': 0,
                    'rx_errors': 0
                }
                interfaces.append(iface)
        
        success, snmp_interfaces, _ = self.ssh.execute_command(
            "snmpwalk -v2c -c public localhost 1.3.6.1.2.1.2.1 2>/dev/null | head -5 || echo 'snmp_not_available'",
            timeout=10
        )
        
        snmp_available = success and 'snmp_not_available' not in (snmp_interfaces or '')
        
        for iface in interfaces:
            name = iface['name']
            
            if snmp_available:
                success, snmp_if_out, _ = self.ssh.execute_command(
                    f"snmpget -v2c -c public localhost 1.3.6.1.2.1.2.2.1.8.$(cat /sys/class/net/{name}/ifindex 2>/dev/null || echo '1') 2>/dev/null | grep -o 'INTEGER: [0-9]' | grep -o '[0-9]' || echo '1'",
                    timeout=5
                )
                
                success, snmp_speed_out, _ = self.ssh.execute_command(
                    f"snmpget -v2c -c public localhost 1.3.6.1.2.1.2.2.1.5.$(cat /sys/class/net/{name}/ifindex 2>/dev/null || echo '2') 2>/dev/null | grep -o '[0-9]*' | head -1 || echo '0'",
                    timeout=5
                )
                
                if success and snmp_speed_out:
                    try:
                        speed_val = int(snmp_speed_out.strip())
                        if speed_val > 0:
                            iface['speed_mbps'] = speed_val // 1000000
                    except:
                        pass
            
            success, proc_net_output, _ = self.ssh.execute_command(
                f"cat /proc/net/dev | grep '{name}:'",
                timeout=5
            )
            
            if success and proc_net_output:
                parts = proc_net_output.strip().split(':')
                if len(parts) >= 2:
                    stats = parts[1].strip().split()
                    if len(stats) >= 10:
                        iface['rx_bytes'] = int(stats[0])
                        iface['rx_packets'] = int(stats[1])
                        iface['rx_errors'] = int(stats[2])
                        iface['tx_bytes'] = int(stats[8])
                        iface['tx_packets'] = int(stats[9])
                        iface['tx_errors'] = int(stats[10])
        
        for iface in interfaces:
            name = iface['name']
            
            success, tx_output, _ = self.ssh.execute_command(
                f"cat /sys/class/net/{name}/statistics/tx_bytes",
                timeout=5
            )
            success, rx_output, _ = self.ssh.execute_command(
                f"cat /sys/class/net/{name}/statistics/rx_bytes",
                timeout=5
            )
            if success and tx_output:
                iface['tx_bytes'] = int(tx_output.strip())
            if success and rx_output:
                iface['rx_bytes'] = int(rx_output.strip())
            
            success, speed_output, _ = self.ssh.execute_command(
                f"ethtool {name} 2>/dev/null | grep -E 'Speed|Duplex|Port' | head -3",
                timeout=5
            )
            if success and speed_output:
                speed_match = re.search(r'Speed:\s*(\d+)Mb/s', speed_output)
                if speed_match:
                    iface['speed_mbps'] = int(speed_match.group(1))
                duplex_match = re.search(r'Duplex:\s*(\w+)', speed_output)
                if duplex_match:
                    iface['duplex'] = duplex_match.group(1)
                port_match = re.search(r'Port:\s*(\w+)', speed_output)
                if port_match:
                    iface['port'] = port_match.group(1)
            
            success, tx_pkt_output, _ = self.ssh.execute_command(
                f"cat /sys/class/net/{name}/statistics/tx_packets",
                timeout=5
            )
            success, rx_pkt_output, _ = self.ssh.execute_command(
                f"cat /sys/class/net/{name}/statistics/rx_packets",
                timeout=5
            )
            if success and tx_pkt_output:
                iface['tx_packets'] = int(tx_pkt_output.strip())
            if success and rx_pkt_output:
                iface['rx_packets'] = int(rx_pkt_output.strip())
            
            success, tx_err_output, _ = self.ssh.execute_command(
                f"cat /sys/class/net/{name}/statistics/tx_errors",
                timeout=5
            )
            success, rx_err_output, _ = self.ssh.execute_command(
                f"cat /sys/class/net/{name}/statistics/rx_errors",
                timeout=5
            )
            if success and tx_err_output:
                iface['tx_errors'] = int(tx_err_output.strip())
            if success and rx_err_output:
                iface['rx_errors'] = int(rx_err_output.strip())
        
        return interfaces
    
    def _collect_frr_bgp(self) -> List[Dict[str, Any]]:
        commands = [
            "vtysh -c 'sh ip bgp sum' 2>&1",
            "vtysh -c 'show ip bgp summary' 2>&1",
            "vtysh -c 'show bgp summary' 2>&1",
        ]
        
        for cmd in commands:
            success, output, _ = self.ssh.execute_command(cmd, timeout=15)
            
            if success and output and 'no bgp' not in output.lower() and 'BGP' in output:
                peers = self._parse_bgp_output(output)
                if peers:
                    return peers
        
        for cmd in commands:
            success, output, _ = self.ssh.execute_with_sudo(cmd, timeout=15)
            
            if success and output and 'no bgp' not in output.lower() and 'BGP' in output:
                peers = self._parse_bgp_output(output)
                if peers:
                    return peers
        
        return []
    
    def _parse_bgp_output(self, output: str) -> List[Dict[str, Any]]:
        peers = []
        
        for line in output.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if 'Neighbor' in line or 'neighbor' in line or line.startswith('-'):
                continue
            
            match = re.match(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+', line)
            if not match:
                match = re.match(r'^([0-9a-f:]+)\s+', line, re.IGNORECASE)
            
            if match:
                neighbor = match.group(1)
                
                asn = None
                state = 'Established'
                uptime = ''
                description = ''
                
                if 'never' in line.lower():
                    state = 'Idle'
                    if 'Admin' in line:
                        state = 'Idle (Admin)'
                
                if 'Idle' in line and 'Admin' not in line:
                    state = 'Idle'
                
                state_patterns = ['Established', 'Connect', 'Active', 'OpenSent', 'OpenConfirm']
                for p in state_patterns:
                    if p in line:
                        state = p
                        break
                
                asn_match = re.search(r'\s+(\d{4,10})\s+\d+\s+\d+\s+\d+\s+\d+\s+', line)
                if asn_match:
                    asn = asn_match.group(1)
                
                uptime_match = re.search(r'(\d+w\d+d\d+h|\d+d\d+h|\d+h\d+m|\d+h|\d+d|\d+m|never)', line)
                if uptime_match:
                    uptime = uptime_match.group(1)
                
                words = line.split()
                for w in reversed(words):
                    w_clean = w.replace('_', ' ').replace('-', ' ')
                    if w_clean.replace(' ', '').isalpha() and len(w_clean) > 2 and w_clean not in ['Established', 'Idle', 'Active', 'Connect', 'OpenSent', 'OpenConfirm', 'never', 'Admin']:
                        description = w_clean
                        break
                
                if neighbor not in [pe['neighbor'] for pe in peers]:
                    peers.append({
                        'neighbor': neighbor,
                        'state': state,
                        'asn': str(asn) if asn else 'N/A',
                        'uptime': uptime,
                        'description': description
                    })
        
        return peers

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

        interfaces = self._collect_frr_interfaces()
        if interfaces:
            metrics['interfaces'] = interfaces

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
