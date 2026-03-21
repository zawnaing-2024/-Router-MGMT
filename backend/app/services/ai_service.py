import os
import re
from typing import Optional, Dict, Any, Tuple
from app.core.config import settings


class AISuggestionService:
    VENDOR_PROMPTS = {
        "cisco_ios": "Cisco IOS/IOS-XE",
        "cisco_ios_xe": "Cisco IOS-XE",
        "juniper_junos": "Juniper JunOS",
        "mikrotik_routeros": "MikroTik RouterOS",
        "huawei": "Huawei",
        "arista_eos": "Arista EOS",
        "vyos": "VyOS",
        "generic": "Generic Network Device",
    }

    CATEGORY_TEMPLATES = {
        "ospf": {
            "cisco_ios": """!
! OSPF Configuration for Cisco IOS
!
router ospf {{process_id}}
 router-id {{router_id}}
 network {{network}} {{wildcard}} area {{area}}
!
! Optional: Configure reference bandwidth
! bandwidth-reference {{bandwidth}}
!
! Optional: Passive interface
! passive-interface default
! no passive-interface {{interface}}
!""",
            "mikrotik_routeros": """/routing ospf instance
set [find default-v2=yes] name=default router-id={{router_id}}
!
/routing ospf area
set [find name={{area}}] area-id={{area}}
!
/routing ospf interface
add interface={{interface}} network-type=broadcast"""
        },
        "bgp": {
            "cisco_ios": """!
! BGP Configuration for Cisco IOS
!
router bgp {{asn}}
 bgp router-id {{router_id}}
!
! Peer with neighbors
 neighbor {{neighbor_ip}} remote-as {{neighbor_as}}
 neighbor {{neighbor_ip}} description {{neighbor_name}}
!
! Advertise networks
 address-family ipv4 unicast
  network {{network}} mask {{netmask}}
  neighbor {{neighbor_ip}} activate
 exit-address-family
!""",
            "mikrotik_routeros": """/routing bgp connection
add local.address={{local_ip}} local.as={{asn}} name={{connection_name}} \
    remote.address={{neighbor_ip}} remote.as={{neighbor_as}} \
    router-id={{router_id}}"""
        },
        "vlan": {
            "cisco_ios": """!
! VLAN Configuration for Cisco IOS
!
vlan {{vlan_id}}
 name {{vlan_name}}
!
interface {{interface}}
 switchport mode access
 switchport access vlan {{vlan_id}}
!
! For trunk ports:
! interface {{trunk_interface}}
! switchport mode trunk
! switchport trunk allowed vlan {{vlan_id}}""",
            "mikrotik_routeros": """/interface/vlan
add interface={{parent_interface}} name={{vlan_name}} vlan-id={{vlan_id}}
!
/ip address
add address={{ip_address}}/{{prefix}} interface={{vlan_name}}"""
        },
        "firewall": {
            "cisco_ios": """!
! ACL Firewall Rules for Cisco IOS
!
ip access-list extended {{acl_name}}
 permit tcp any host {{host_ip}} eq {{port}}
 permit udp any any eq {{port}}
 deny ip any any log
!
interface {{interface}}
 ip access-group {{acl_name}} in""",
            "mikrotik_routeros": """/ip firewall filter
add action=accept chain=forward src-address={{src_network}} dst-address={{dst_network}} \
    protocol={{protocol}} dst-port={{port}} comment="{{rule_name}}"
add action=drop chain=forward src-address={{src_network}} comment="Drop unwanted traffic" """
        },
        "nat": {
            "cisco_ios": """!
! NAT Configuration for Cisco IOS
!
ip nat inside source list {{acl_number}} interface {{outside_interface}} overload
!
interface {{inside_interface}}
 ip nat inside
!
interface {{outside_interface}}
 ip nat outside""",
            "mikrotik_routeros": """/ip firewall nat
add chain=srcnat out-interface={{wan_interface}} action=masquerade
add chain=dstnat in-interface={{wan_interface}} dst-address={{public_ip}} \
    action=dst-nat to-addresses={{private_ip}}"""
        },
        "qos": {
            "cisco_ios": """!
! QoS Configuration for Cisco IOS
!
class-map match-any {{class_name}}
 match access-group name {{acl_name}}
!
policy-map {{policy_name}}
 class {{class_name}}
  priority percent {{bandwidth}}
!
interface {{interface}}
 service-policy output {{policy_name}}""",
            "mikrotik_routeros": """/queue type
add name={{queue_type}} kind=pcq pcq-rate={{rate}}
!
/queue tree
add name={{tree_name}} parent=global max-limit={{max_limit}}
add name={{class_name}} parent={{tree_name}} priority={{priority}} \
    queue={{queue_type}} max-limit={{class_limit}}"""
        },
        "vpn": {
            "cisco_ios": """!
! IPSec VPN Configuration for Cisco IOS
!
crypto isakmp policy {{policy_priority}}
 encr aes
 hash sha256
 authentication pre-share
 group 14
!
crypto isakmp key {{preshared_key}} address {{peer_ip}}
!
crypto ipsec transform-set {{transform_set}} esp-aes esp-sha256
!
crypto map {{map_name}} {{map_sequence}} ipsec-isakmp
 set peer {{peer_ip}}
 set transform-set {{transform_set}}
 match address {{acl_name}}
!
interface {{interface}}
 crypto map {{map_name}}""",
            "mikrotik_routeros": """/ip ipsec profile
set [find default=yes] hash-algorithm=sha256 enc-algorithm=aes-128
!
/ip ipsec peer
add address={{peer_ip}} secret={{secret}}
!
/ip ipsec identity
add peer={{peer_ip}} auth-method=pre-shared-key \
    secret-key={{preshared_key}}
!
/ip ipsec policy
add src-address={{local_subnet}} dst-address={{remote_subnet}} \
    peer={{peer_ip}} action=encrypt"""
        }
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.use_ai = bool(self.api_key)

    async def get_suggestion(
        self,
        category: str,
        vendor: str,
        description: Optional[str] = None,
        network_info: Optional[str] = None
    ) -> Dict[str, Any]:
        if self.use_ai:
            return await self._get_ai_suggestion(category, vendor, description, network_info)
        else:
            return self._get_template_suggestion(category, vendor, description)

    async def _get_ai_suggestion(
        self,
        category: str,
        vendor: str,
        description: Optional[str] = None,
        network_info: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.api_key)
            
            vendor_name = self.VENDOR_PROMPTS.get(vendor, vendor)
            category_name = category.upper()
            
            system_prompt = f"""You are a network automation expert specializing in {vendor_name} configurations.
Generate precise, working network configurations based on user requirements.
Always provide configuration in proper syntax for the specified vendor.
Include brief explanations for key sections."""

            user_prompt = f"""Generate a {category_name} configuration for {vendor_name}.
"""
            if description:
                user_prompt += f"Requirements: {description}\n"
            if network_info:
                user_prompt += f"Network details: {network_info}\n"
            user_prompt += "\nProvide the configuration and a brief explanation."

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )

            content = response.choices[0].message.content
            
            parts = content.split("Configuration:")
            if len(parts) > 1:
                explanation = parts[0].replace("Explanation:", "").strip()
                config = parts[1].strip()
            else:
                explanation = ""
                config = content

            return {
                "suggestion": f"{category_name} configuration for {vendor_name}",
                "configuration": config,
                "explanation": explanation
            }
        except Exception as e:
            return {
                "suggestion": f"Error generating suggestion: {str(e)}",
                "configuration": self._get_template_suggestion(category, vendor, description).get("configuration", ""),
                "explanation": "Falling back to template-based suggestion."
            }

    def _get_template_suggestion(
        self,
        category: str,
        vendor: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        templates = self.CATEGORY_TEMPLATES.get(category.lower(), {})
        config = templates.get(vendor, templates.get("cisco_ios", "# No template available for this combination"))

        if description:
            explanation = f"{category.upper()} configuration based on: {description}"
        else:
            explanation = f"Basic {category.upper()} configuration template for {vendor.replace('_', ' ').title()}"

        return {
            "suggestion": f"{category.upper()} configuration",
            "configuration": config,
            "explanation": explanation
        }

    async def generate_from_prompt(
        self,
        prompt: str,
        vendor: str
    ) -> Dict[str, Any]:
        if self.use_ai:
            return await self._generate_ai_from_prompt(prompt, vendor)
        else:
            return self._generate_template_from_prompt(prompt, vendor)

    async def _generate_ai_from_prompt(
        self,
        prompt: str,
        vendor: str
    ) -> Dict[str, Any]:
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.api_key)
            vendor_name = self.VENDOR_PROMPTS.get(vendor, vendor)
            
            system_prompt = f"""You are a network automation expert specializing in {vendor_name} configurations.
Parse natural language requests and generate precise network device configurations.
Always output ONLY the configuration commands without explanations first.
If you need to provide context, put it after a '---EXPLANATION---' separator."""

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate {vendor_name} configuration for: {prompt}\n\nProvide ONLY the configuration commands:"}
                ],
                max_tokens=1500,
                temperature=0.3
            )

            content = response.choices[0].message.content
            
            if "---EXPLANATION---" in content:
                parts = content.split("---EXPLANATION---")
                config = parts[0].strip()
                explanation = parts[1].strip() if len(parts) > 1 else ""
            else:
                config = content.strip()
                explanation = self._generate_explanation(prompt, vendor)

            return {
                "prompt": prompt,
                "vendor": vendor,
                "configuration": config,
                "explanation": explanation
            }
        except Exception as e:
            return {
                "prompt": prompt,
                "vendor": vendor,
                "configuration": f"# Error: {str(e)}",
                "explanation": "Failed to generate configuration"
            }

    def _generate_template_from_prompt(
        self,
        prompt: str,
        vendor: str
    ) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        config = ""
        explanation = ""
        
        if "loopback" in prompt_lower:
            config, explanation = self._parse_loopback(prompt, vendor)
        elif "interface" in prompt_lower and ("vlan" in prompt_lower or "ip" in prompt_lower):
            config, explanation = self._parse_interface(prompt, vendor)
        elif "ospf" in prompt_lower:
            config, explanation = self._parse_ospf(prompt, vendor)
        elif "bgp" in prompt_lower:
            config, explanation = self._parse_bgp(prompt, vendor)
        elif "nat" in prompt_lower:
            config, explanation = self._parse_nat(prompt, vendor)
        elif "firewall" in prompt_lower or "acl" in prompt_lower:
            config, explanation = self._parse_firewall(prompt, vendor)
        elif "vpn" in prompt_lower:
            config, explanation = self._parse_vpn(prompt, vendor)
        elif "vlan" in prompt_lower:
            config, explanation = self._parse_vlan(prompt, vendor)
        elif "qos" in prompt_lower or "traffic" in prompt_lower or "priority" in prompt_lower:
            config, explanation = self._parse_qos(prompt, vendor)
        elif "route" in prompt_lower or "static" in prompt_lower:
            config, explanation = self._parse_static_route(prompt, vendor)
        elif "dhcp" in prompt_lower:
            config, explanation = self._parse_dhcp(prompt, vendor)
        elif "bridge" in prompt_lower:
            config, explanation = self._parse_bridge(prompt, vendor)
        else:
            config = f"# Could not parse prompt: {prompt}\n# Try specifying: loopback, interface, vlan, ospf, bgp, nat, firewall, vpn, route, dhcp"
            explanation = "Template-based parser couldn't understand the prompt"

        return {
            "prompt": prompt,
            "vendor": vendor,
            "configuration": config,
            "explanation": explanation
        }

    def _parse_loopback(self, prompt: str, vendor: str) -> Tuple[str, str]:
        prompt_lower = prompt.lower()
        
        loopback_match = re.search(r'loopback[_\s]?(\d+)', prompt_lower)
        ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:\/(\d+))?', prompt)
        description_match = re.search(r'description[:\s]+([^\n,]+)', prompt, re.IGNORECASE)
        
        if not loopback_match:
            loopback_match = re.search(r'interface\s+loopback[_\s]?(\d+)', prompt_lower)
        
        interface_num = loopback_match.group(1) if loopback_match else "0"
        ip_address = ip_match.group(1) if ip_match else None
        prefix = ip_match.group(2) if ip_match else "32"
        description = description_match.group(1).strip() if description_match else "Loopback Interface"
        
        if vendor in ("cisco_ios", "cisco_ios_xe", "arista_eos"):
            config = f"""!
interface Loopback{interface_num}
 description {description}
"""
            if ip_address:
                subnet_mask = self._prefix_to_mask(int(prefix))
                config += f" ip address {ip_address} {subnet_mask}"
            config += "\n!"
        elif vendor == "mikrotik_routeros":
            if ip_address:
                config = f"""# Loopback Interface for MikroTik
/ip address add address={ip_address}/{prefix} interface=lo comment="{description}"
"""
            else:
                config = f"""# Loopback Interface for MikroTik
# Note: MikroTik has one built-in loopback interface "lo"
# Configure IP on loopback:
# /ip address add address=<IP>/<prefix> interface=lo
"""
        elif vendor == "juniper_junos":
            config = f"""# Loopback Interface for Juniper
set interfaces lo0 unit 0 description "{description}"
"""
            if ip_address:
                config += f'set interfaces lo0 unit 0 family inet address {ip_address}/{prefix}\n'
        else:
            config = f"# Loopback interface {interface_num} with IP {ip_address}/{prefix}"
        
        explanation = f"Loopback interface {interface_num} configuration"
        if ip_address:
            explanation += f" with IP {ip_address}/{prefix}"
        
        return config, explanation

    def _parse_interface(self, prompt: str, vendor: str) -> Tuple[str, str]:
        prompt_lower = prompt.lower()
        
        interface_match = re.search(r'(?:interface\s+)([\w\-\/]+)', prompt_lower)
        if not interface_match:
            interface_match = re.search(r'(g\d+\/\d+|gigabitethernet\d+\/\d+|fastethernet\d+\/\d+|ethernet\d+\/\d+|loopback\d+)', prompt_lower)
        
        ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:\/(\d+))?', prompt)
        description_match = re.search(r'description[:\s]+([^\n,]+)', prompt, re.IGNORECASE)
        dhcp_match = re.search(r'dhcp', prompt_lower)
        
        interface_name = interface_match.group(1) if interface_match else None
        ip_address = ip_match.group(1) if ip_match else None
        prefix = ip_match.group(2) if (ip_match and ip_match.group(2)) else "24"
        description = description_match.group(1).strip() if description_match else "Interface"
        
        if interface_name and interface_name.startswith(('g', 'gi', 'fa', 'et', 'lo')):
            interface = interface_name
        elif interface_name and interface_name.isdigit():
            interface = f"GigabitEthernet0/{interface_name}"
        else:
            interface = interface_name or "GigabitEthernet0/0"
        
        if vendor in ("cisco_ios", "cisco_ios_xe", "arista_eos"):
            config = f"""!
interface {interface}
 description {description}
"""
            if dhcp_match:
                config += " ip address dhcp\n"
            elif ip_address:
                subnet_mask = self._prefix_to_mask(int(prefix))
                config += f" ip address {ip_address} {subnet_mask}\n"
            config += " no shutdown\n!"
        elif vendor == "mikrotik_routeros":
            config = f"""# Interface Configuration for MikroTik
/ip address add address={ip_address}/{prefix} interface={interface} comment="{description}"
"""
            if dhcp_match:
                config = f"""/ip address add address=dhcp interface={interface} comment="{description}"
"""
        elif vendor == "juniper_junos":
            config = f"""# Interface Configuration for Juniper
set interfaces {interface} description "{description}"
"""
            if ip_address:
                config += f'set interfaces {interface} unit 0 family inet address {ip_address}/{prefix}\n'
            config += f"set interfaces {interface} enable\n"
        else:
            config = f"# Interface {interface} configuration"
        
        return config, f"Interface {interface} configuration"

    def _parse_ospf(self, prompt: str, vendor: str) -> Tuple[str, str]:
        prompt_lower = prompt.lower()
        area_match = re.search(r'area[_\s]?(\d+)', prompt_lower)
        network_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:\/(\d+))?', prompt)
        router_id_match = re.search(r'router[_-]?id[:\s]+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', prompt_lower)
        
        area = area_match.group(1) if area_match else "0"
        router_id = router_id_match.group(1) if router_id_match else "10.0.0.1"
        
        if network_match:
            network = network_match.group(1)
            prefix = int(network_match.group(2) or "24")
            wildcard = self._prefix_to_wildcard(prefix)
        else:
            network = "192.168.1.0"
            wildcard = "0.0.0.255"
        
        if vendor in ("cisco_ios", "cisco_ios_xe"):
            config = f"""!
router ospf 1
 router-id {router_id}
 log-adjacency-changes
 network {network} {wildcard} area {area}
!
"""
        elif vendor == "mikrotik_routeros":
            ospf_prefix = int(prefix) if prefix else 24
            config = f"""/routing ospf instance
set [find default-v2=yes] router-id={router_id}
/routing ospf network
add area=backbone network={network}/{ospf_prefix}
"""
        else:
            config = f"# OSPF area {area} configuration"
        
        return config, f"OSPF area {area} configuration"

    def _parse_bgp(self, prompt: str, vendor: str) -> Tuple[str, str]:
        prompt_lower = prompt.lower()
        asn_match = re.search(r'(?:as|asn)[:\s]?(\d+)', prompt_lower)
        neighbor_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:\/(\d+))?', prompt)
        remote_as_match = re.search(r'remote[_-]?as[:\s]?(\d+)', prompt_lower)
        
        asn = asn_match.group(1) if asn_match else "65001"
        router_id = f"10.0.0.{asn[-1]}"
        neighbor = neighbor_match.group(1) if neighbor_match else "192.168.1.1"
        remote_as = remote_as_match.group(1) if remote_as_match else "65002"
        
        if vendor in ("cisco_ios", "cisco_ios_xe"):
            config = f"""!
router bgp {asn}
 bgp router-id {router_id}
 neighbor {neighbor} remote-as {remote_as}
!
"""
        elif vendor == "mikrotik_routeros":
            config = f"""/routing bgp connection
add local.address={router_id} local.as={asn} \
    remote.address={neighbor} remote.as={remote_as} \
    name=bgp-peer
"""
        else:
            config = f"# BGP AS {asn} configuration"
        
        return config, f"BGP AS {asn} peer {neighbor}"

    def _parse_nat(self, prompt: str, vendor: str) -> Tuple[str, str]:
        prompt_lower = prompt.lower()
        inside_match = re.search(r'inside|internal|lan', prompt_lower)
        outside_match = re.search(r'outside|external|wan', prompt_lower)
        
        inside_if = "GigabitEthernet0/0" if inside_match else "inside"
        outside_if = "GigabitEthernet0/1" if outside_match else "outside"
        mikrotik_if = "ether1" if outside_match else "ether2"
        
        if vendor in ("cisco_ios", "cisco_ios_xe"):
            config = f"""!
ip nat inside source list 1 interface {outside_if} overload
!
interface {inside_if}
 ip nat inside
!
interface {outside_if}
 ip nat outside
!
access-list 1 permit 192.168.0.0 0.0.255.255
!
"""
        elif vendor == "mikrotik_routeros":
            config = f"""/ip firewall nat
add chain=srcnat out-interface={mikrotik_if} action=masquerade comment="NAT to WAN"
"""
        else:
            config = "# NAT configuration"
        
        return config, "PAT NAT configuration"

    def _parse_firewall(self, prompt: str, vendor: str) -> Tuple[str, str]:
        prompt_lower = prompt.lower()
        action_match = re.search(r'(allow|permit|deny|block|accept|drop)', prompt_lower)
        src_match = re.search(r'from[:\s]+([^\n,]+)', prompt, re.IGNORECASE)
        port_match = re.search(r'(?:port|eq)[:\s]?(\d+)', prompt_lower)
        
        action = "accept" if action_match and action_match.group(1) in ["allow", "permit", "accept"] else "drop"
        src = src_match.group(1).strip() if src_match else "any"
        port = port_match.group(1) if port_match else None
        
        if vendor in ("cisco_ios", "cisco_ios_xe"):
            config = f"""!
ip access-list extended FIREWALL_POLICY
"""
            if action == "accept":
                if port:
                    config += f" permit tcp any any eq {port}\n"
                else:
                    config += f" permit ip {src} any\n"
            else:
                if port:
                    config += f" deny tcp any any eq {port}\n"
                else:
                    config += f" deny ip {src} any\n"
            config += " permit ip any any\n!"
        elif vendor == "mikrotik_routeros":
            action_mk = "accept" if action == "accept" else "drop"
            config = f"""/ip firewall filter
add chain=input action={action_mk} src-address={src} comment="Firewall rule"
"""
            if port:
                config = f"""/ip firewall filter
add chain=input action={action_mk} protocol=tcp dst-port={port} \
    src-address={src} comment="Allow port {port}"
"""
        else:
            config = f"# Firewall {action} rule"
        
        return config, f"Firewall {action} rule"

    def _parse_vpn(self, prompt: str, vendor: str) -> Tuple[str, str]:
        prompt_lower = prompt.lower()
        peer_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', prompt)
        local_match = re.search(r'local[:\s]+([^\n,]+)', prompt, re.IGNORECASE)
        remote_match = re.search(r'remote[:\s]+([^\n,]+)', prompt, re.IGNORECASE)
        
        peer = peer_match.group(1) if peer_match else "203.0.113.1"
        local_net = local_match.group(1).strip() if local_match else "192.168.1.0/24"
        remote_net = remote_match.group(1).strip() if remote_match else "10.0.0.0/24"
        
        if vendor in ("cisco_ios", "cisco_ios_xe"):
            config = f"""!
crypto isakmp policy 1
 encr aes
 hash sha256
 authentication pre-share
 group 14
!
crypto isakmp key PRE_SHARED_KEY address {peer}
!
crypto ipsec transform-set TS esp-aes esp-sha256-hmac
!
crypto map CRYPTO_MAP 10 ipsec-isakmp
 set peer {peer}
 set transform-set TS
 match address VPN_TRAFFIC
!
interface GigabitEthernet0/1
 crypto map CRYPTO_MAP
!
ip access-list extended VPN_TRAFFIC
 permit ip {local_net.replace('/', ' ')} {remote_net.replace('/', ' ')}
!
"""
        elif vendor == "mikrotik_routeros":
            config = f"""/ip ipsec profile
set [find default=yes] hash-algorithm=sha256 enc-algorithm=aes-128
/ip ipsec peer
add address={peer} secret=PRE_SHARED_KEY
/ip ipsec policy
add src-address={local_net} dst-address={remote_net} \
    peer={peer} action=encrypt comment="Site-to-Site VPN"
"""
        else:
            config = "# IPSec VPN configuration"
        
        return config, f"IPSec VPN to {peer}"

    def _parse_vlan(self, prompt: str, vendor: str) -> Tuple[str, str]:
        prompt_lower = prompt.lower()
        vlan_match = re.search(r'vlan[_\s]?(\d+)', prompt_lower)
        interface_match = re.search(r'(?:interface|port)[:\s]+([^\n,]+)', prompt, re.IGNORECASE)
        ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:\/(\d+))?', prompt)
        
        vlan_id = vlan_match.group(1) if vlan_match else "100"
        interface = interface_match.group(1).strip() if interface_match else "GigabitEthernet0/1"
        ip_address = ip_match.group(1) if ip_match else None
        prefix = ip_match.group(2) if ip_match else "24"
        
        if vendor in ("cisco_ios", "cisco_ios_xe"):
            config = f"""!
vlan {vlan_id}
!
interface {interface}
 switchport mode access
 switchport access vlan {vlan_id}
 spanning-tree portfast
!
"""
        elif vendor == "mikrotik_routeros":
            config = f"""/interface vlan
add interface=bridge1 name=vlan{vlan_id} vlan-id={vlan_id}
"""
            if ip_address:
                config += f"/ip address\nadd address={ip_address}/{prefix} interface=vlan{vlan_id}\n"
        else:
            config = f"# VLAN {vlan_id} configuration"
        
        return config, f"VLAN {vlan_id} configuration"

    def _parse_qos(self, prompt: str, vendor: str) -> Tuple[str, str]:
        prompt_lower = prompt.lower()
        bandwidth_match = re.search(r'(\d+)(?:%|mbps|mbit)?', prompt)
        
        bandwidth = bandwidth_match.group(1) if bandwidth_match else "10"
        
        if vendor in ("cisco_ios", "cisco_ios_xe"):
            config = f"""!
class-map match-any QOS_CLASS
 match access-group name QOS_ACL
!
policy-map QOS_POLICY
 class QOS_CLASS
  priority percent {bandwidth}
 class class-default
  fair-queue
!
interface GigabitEthernet0/0
 service-policy output QOS_POLICY
!
ip access-list extended QOS_ACL
 permit ip any any
!
"""
        elif vendor == "mikrotik_routeros":
            config = f"""/queue type
add name=limited-queue kind=pcq pcq-rate={bandwidth}m
/queue tree
add name=QOS parent=global max-limit=100m
add name=QOS_CLASS parent=QOS priority=1 \
    queue=limited-queue max-limit={bandwidth}m
"""
        else:
            config = f"# QoS {bandwidth}% priority configuration"
        
        return config, f"QoS with {bandwidth}% bandwidth"

    def _parse_static_route(self, prompt: str, vendor: str) -> Tuple[str, str]:
        prompt_lower = prompt.lower()
        network_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:\/(\d+))?', prompt)
        gateway_match = re.search(r'(?:gateway|via|next[_-]?hop)[:\s]+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', prompt_lower)
        
        network = network_match.group(1) if network_match else "0.0.0.0"
        prefix = network_match.group(2) if network_match else "0"
        gateway = gateway_match.group(1) if gateway_match else "192.168.1.1"
        
        if vendor in ("cisco_ios", "cisco_ios_xe"):
            config = f"""!
ip route {network} {self._prefix_to_mask(int(prefix)) if prefix != '0' else '0.0.0.0'} {gateway}
!
"""
        elif vendor == "mikrotik_routeros":
            config = f"""/ip route
add dst-address={network}/{prefix} gateway={gateway}
"""
        else:
            config = f"# Static route to {network}/{prefix} via {gateway}"
        
        return config, f"Static route to {network}/{prefix}"

    def _parse_dhcp(self, prompt: str, vendor: str) -> Tuple[str, str]:
        prompt_lower = prompt.lower()
        pool_match = re.search(r'pool[:\s]+([^\n,]+)', prompt, re.IGNORECASE)
        network_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:\/(\d+))?', prompt)
        
        pool_name = pool_match.group(1).strip() if pool_match else "DHCP_POOL"
        network = network_match.group(1) if network_match else "192.168.1.0"
        prefix = int(network_match.group(2) or 24)
        gateway = ".".join(network.split(".")[:3]) + ".1"
        
        if vendor in ("cisco_ios", "cisco_ios_xe"):
            config = f"""!
ip dhcp pool {pool_name}
 network {network} {self._prefix_to_mask(prefix)}
 default-router {gateway}
 dns-server 8.8.8.8 8.8.4.4
!
ip dhcp excluded-address {gateway}
!
"""
        elif vendor == "mikrotik_routeros":
            config = f"""/ip pool
add name={pool_name} ranges={network.split('.')[0]}.{network.split('.')[1]}.{network.split('.')[2]}.10-{network.split('.')[0]}.{network.split('.')[1]}.{network.split('.')[2]}.250
/ip dhcp-server
add name=dhcp_server address-pool={pool_name} interface=bridge1
/ip dhcp-server network
add address={network}/{prefix} gateway={gateway} dns-server=8.8.8.8
"""
        else:
            config = f"# DHCP pool {pool_name} configuration"
        
        return config, f"DHCP pool {pool_name}"

    def _parse_bridge(self, prompt: str, vendor: str) -> Tuple[str, str]:
        prompt_lower = prompt.lower()
        name_match = re.search(r'bridge[:\s]+([^\n,]+)', prompt, re.IGNORECASE)
        ports_match = re.search(r'ports?[:\s]+([^\n,]+)', prompt, re.IGNORECASE)
        
        bridge_name = name_match.group(1).strip() if name_match else "bridge1"
        ports_str = ports_match.group(1).strip() if ports_match else "ether2,ether3"
        ports = [p.strip() for p in ports_str.replace(",", " ").split()]
        
        if vendor == "mikrotik_routeros":
            config = f"""/interface bridge
add name={bridge_name} comment="LAN Bridge"
"""
            for port in ports:
                config += f"/interface bridge port\nadd bridge={bridge_name} interface={port}\n"
        else:
            config = f"# Bridge {bridge_name} configuration"
        
        return config, f"Bridge {bridge_name}"

    def _generate_explanation(self, prompt: str, vendor: str) -> str:
        return f"Configuration generated from prompt: {prompt[:50]}..."

    def _prefix_to_mask(self, prefix: int) -> str:
        mask = (0xFFFFFFFF >> (32 - prefix)) << (32 - prefix)
        return f"{(mask >> 24) & 0xFF}.{(mask >> 16) & 0xFF}.{(mask >> 8) & 0xFF}.{mask & 0xFF}"

    def _prefix_to_wildcard(self, prefix: int) -> str:
        mask = 0xFFFFFFFF ^ ((0xFFFFFFFF >> (32 - prefix)) << (32 - prefix))
        return f"{(mask >> 24) & 0xFF}.{(mask >> 16) & 0xFF}.{(mask >> 8) & 0xFF}.{mask & 0xFF}"


ai_service = AISuggestionService()
