from app.core.database import SessionLocal
from app.models import ConfigTemplate, TemplateCategory

db = SessionLocal()

existing = db.query(ConfigTemplate).filter(ConfigTemplate.is_builtin == True).count()
if existing > 0:
    print(f'Builtin templates already exist ({existing})')
    db.close()
    exit()

templates_data = [
    {
        'name': 'Basic OSPF Area 0',
        'description': 'Basic OSPF configuration for area 0 with network advertisement',
        'category': TemplateCategory.OSPF,
        'vendor': 'cisco_ios',
        'content': """!
! OSPF Configuration Template
!
router ospf {{process_id}}
 router-id {{router_id}}
 log-adjacency-changes
!
! Network statements
{% for network in networks %}
 network {{ network.address }} {{ network.wildcard }} area {{ network.area }}
{% endfor %}
!
""",
        'variables': {'process_id': '1', 'router_id': '10.0.0.1', 'networks': [{'address': '192.168.1.0', 'wildcard': '0.0.0.255', 'area': '0'}]}
    },
    {
        'name': 'MikroTik OSPF',
        'description': 'OSPF configuration for MikroTik RouterOS',
        'category': TemplateCategory.OSPF,
        'vendor': 'mikrotik_routeros',
        'content': """# OSPF Configuration for MikroTik

/routing ospf instance
set [find default-v2=yes] name=default router-id={{router_id}}

/routing ospf area
set [find name={{area}}] area-id={{area}}

{% for network in networks %}
/routing ospf network
add area={{area}} network={{network}}
{% endfor %}
""",
        'variables': {'router_id': '10.0.0.1', 'area': 'backbone', 'networks': ['192.168.1.0/24']}
    },
    {
        'name': 'Basic BGP Peer',
        'description': 'Basic BGP configuration with a single peer',
        'category': TemplateCategory.BGP,
        'vendor': 'cisco_ios',
        'content': """!
! BGP Configuration Template
!
router bgp {{asn}}
 bgp router-id {{router_id}}
 no synchronization
!
! BGP Peer Configuration
 neighbor {{peer_ip}} remote-as {{peer_as}}
 neighbor {{peer_ip}} description {{peer_name}}
!
! Address Family
 address-family ipv4 unicast
  network {{network}} mask {{mask}}
  neighbor {{peer_ip}} activate
 exit-address-family
!
""",
        'variables': {'asn': '65001', 'router_id': '10.0.0.1', 'peer_ip': '192.168.1.1', 'peer_as': '65002', 'peer_name': 'EBGP Peer', 'network': '192.168.0.0', 'mask': '255.255.0.0'}
    },
    {
        'name': 'Access Port VLAN',
        'description': 'Configure access port with VLAN assignment',
        'category': TemplateCategory.VLAN,
        'vendor': 'cisco_ios',
        'content': """!
! VLAN Configuration - Access Port
!
interface {{interface}}
 description {{description}}
 switchport mode access
 switchport access vlan {{vlan_id}}
 switchport voice vlan {{voice_vlan}}
 spanning-tree portfast
 spanning-tree bpduguard enable
!
""",
        'variables': {'interface': 'GigabitEthernet0/1', 'description': 'User Access Port', 'vlan_id': '100', 'voice_vlan': '200'}
    },
    {
        'name': 'MikroTik VLAN Bridge',
        'description': 'Create VLAN on bridge interface for MikroTik',
        'category': TemplateCategory.VLAN,
        'vendor': 'mikrotik_routeros',
        'content': """# VLAN Configuration for MikroTik

/interface vlan
add interface={{parent_interface}} name=vlan{{vlan_id}} vlan-id={{vlan_id}}

/ip address
add address={{ip_address}}/{{prefix}} interface=vlan{{vlan_id}}
""",
        'variables': {'parent_interface': 'bridge1', 'vlan_id': '100', 'ip_address': '192.168.100.1', 'prefix': '24'}
    },
    {
        'name': 'Basic ACL Firewall',
        'description': 'Standard access control list for firewall',
        'category': TemplateCategory.FIREWALL,
        'vendor': 'cisco_ios',
        'content': """!
! Firewall ACL Configuration
!
ip access-list extended {{acl_name}}
 permit tcp any host {{host_ip}} eq {{port}}
 permit udp any any eq {{port}}
 deny ip any any log
!
interface {{interface}}
 ip access-group {{acl_name}} {{direction}}
!
""",
        'variables': {'acl_name': 'FIREWALL_POLICY', 'host_ip': '192.168.1.10', 'port': '443', 'interface': 'GigabitEthernet0/0', 'direction': 'in'}
    },
    {
        'name': 'MikroTik Firewall Filter',
        'description': 'Basic firewall filter rules for MikroTik',
        'category': TemplateCategory.FIREWALL,
        'vendor': 'mikrotik_routeros',
        'content': """# Firewall Filter Rules for MikroTik

/ip firewall filter
add chain=input action=accept connection-state=established,related comment="Allow established"
add chain=input action=accept connection-state=new src-address={{allowed_network}} comment="Allow from LAN"

add chain=input action=accept protocol=icmp comment="Allow ping"

add chain=input action=drop connection-state=invalid comment="Drop invalid"
add chain=input action=drop in-interface={{wan_interface}} comment="Drop WAN input"
""",
        'variables': {'allowed_network': '192.168.1.0/24', 'wan_interface': 'ether1'}
    },
    {
        'name': 'PAT NAT Configuration',
        'description': 'Port Address Translation (many-to-one NAT)',
        'category': TemplateCategory.NAT,
        'vendor': 'cisco_ios',
        'content': """!
! NAT Configuration (PAT)
!
ip nat inside source list {{acl_number}} interface {{outside_interface}} overload
!
interface {{inside_interface}}
 ip nat inside
!
interface {{outside_interface}}
 ip nat outside
!
access-list {{acl_number}} permit {{source_network}} {{wildcard}}
!
""",
        'variables': {'acl_number': '1', 'outside_interface': 'GigabitEthernet0/1', 'inside_interface': 'GigabitEthernet0/0', 'source_network': '192.168.1.0', 'wildcard': '0.0.0.255'}
    },
    {
        'name': 'MikroTik NAT Masquerade',
        'description': 'Source NAT (masquerade) for MikroTik',
        'category': TemplateCategory.NAT,
        'vendor': 'mikrotik_routeros',
        'content': """# NAT Configuration for MikroTik

/ip firewall nat
add chain=srcnat out-interface={{wan_interface}} action=masquerade comment="MASQ to WAN"
""",
        'variables': {'wan_interface': 'ether1'}
    },
    {
        'name': 'IPSec Site-to-Site VPN',
        'description': 'Basic IPSec site-to-site VPN configuration',
        'category': TemplateCategory.VPN,
        'vendor': 'cisco_ios',
        'content': """!
! IPSec Site-to-Site VPN Configuration
!
crypto isakmp policy {{isakmp_policy}}
 encr aes 256
 hash sha256
 authentication pre-share
 group 14
!
crypto isakmp key {{preshared_key}} address {{peer_address}}
!
crypto ipsec transform-set {{transform_set}} esp-aes 256 esp-sha256-hmac
 mode tunnel
!
crypto map {{map_name}} {{map_seq}} ipsec-isakmp
 set peer {{peer_address}}
 set transform-set {{transform_set}}
 match address {{acl_name}}
!
interface {{interface}}
 crypto map {{map_name}}
!
access-list {{acl_name}} permit ip {{local_network}} {{local_wildcard}} {{remote_network}} {{remote_wildcard}}
!
""",
        'variables': {'isakmp_policy': '10', 'preshared_key': 'YOUR_KEY', 'peer_address': '203.0.113.1', 'transform_set': 'VPN-TRANSFORM', 'map_name': 'VPN-MAP', 'map_seq': '10', 'interface': 'GigabitEthernet0/1', 'acl_name': 'VPN-ACL', 'local_network': '192.168.1.0', 'local_wildcard': '0.0.0.255', 'remote_network': '10.0.0.0', 'remote_wildcard': '0.0.0.255'}
    },
    {
        'name': 'Traffic Shaping QoS',
        'description': 'Quality of Service with traffic shaping',
        'category': TemplateCategory.QOS,
        'vendor': 'cisco_ios',
        'content': """!
! QoS Configuration
!
class-map match-any {{class_name}}
 match access-group name {{acl_name}}
!
policy-map {{policy_name}}
 class {{class_name}}
  priority percent {{priority}}
 class class-default
  fair-queue
!
interface {{interface}}
 service-policy output {{policy_name}}
!
""",
        'variables': {'class_name': 'VOICE-TRAFFIC', 'acl_name': 'VOICE-ACL', 'policy_name': 'VOICE-QOS', 'priority': '20', 'interface': 'GigabitEthernet0/0'}
    },
    {
        'name': 'Basic Interface IP',
        'description': 'Configure IP address on an interface',
        'category': TemplateCategory.INTERFACE,
        'vendor': 'cisco_ios',
        'content': """!
! Interface Configuration
!
interface {{interface}}
 description {{description}}
 ip address {{ip_address}} {{subnet_mask}}
 no shutdown
!
""",
        'variables': {'interface': 'GigabitEthernet0/0', 'description': 'WAN Interface', 'ip_address': '192.168.1.1', 'subnet_mask': '255.255.255.0'}
    },
    {
        'name': 'Interface with Speed/Duplex',
        'description': 'Configure interface with speed and duplex settings',
        'category': TemplateCategory.INTERFACE,
        'vendor': 'cisco_ios',
        'content': """!
! Interface Configuration with Speed/Duplex
!
interface {{interface}}
 description {{description}}
 speed {{speed}}
 duplex {{duplex}}
 {% if ip_address and subnet_mask %}
 ip address {{ip_address}} {{subnet_mask}}
 {% endif %}
 {% if shutdown == "no" %}
 no shutdown
 {% else %}
 shutdown
 {% endif %}
!
""",
        'variables': {'interface': 'GigabitEthernet0/1', 'description': 'Server Port', 'speed': '1000', 'duplex': 'full', 'ip_address': '', 'subnet_mask': '', 'shutdown': 'no'}
    },
    {
        'name': 'Interface Port-Channel',
        'description': 'Configure LACP port-channel interface',
        'category': TemplateCategory.INTERFACE,
        'vendor': 'cisco_ios',
        'content': """!
! Port-Channel Interface Configuration
!
interface Port-channel{{channel_number}}
 description {{description}}
 switchport mode trunk
 switchport trunk allowed vlan {{vlans}}
!
{% for member in members %}
interface {{member}}
 channel-group {{channel_number}} mode active
!
{% endfor %}
""",
        'variables': {'channel_number': '1', 'description': 'Uplink Trunk', 'vlans': '10,20,30', 'members': ['GigabitEthernet0/1', 'GigabitEthernet0/2']}
    },
    {
        'name': 'MikroTik Interface IP',
        'description': 'Configure IP address on MikroTik interface',
        'category': TemplateCategory.INTERFACE,
        'vendor': 'mikrotik_routeros',
        'content': """# Interface Configuration for MikroTik

/interface
set [find name={{interface}}] comment="{{description}}"

/ip address
add address={{ip_address}}/{{prefix}} interface={{interface}} comment="{{description}}"
""",
        'variables': {'interface': 'ether1', 'description': 'WAN Interface', 'ip_address': '192.168.1.1', 'prefix': '24'}
    },
    {
        'name': 'MikroTik Bridge Interface',
        'description': 'Create and configure bridge interface',
        'category': TemplateCategory.INTERFACE,
        'vendor': 'mikrotik_routeros',
        'content': """# Bridge Interface Configuration for MikroTik

/interface bridge
add name={{bridge_name}} comment="{{description}}"

{% for port in ports %}
/interface bridge port
add bridge={{bridge_name}} interface={{port}}
{% endfor %}

/ip address
add address={{ip_address}}/{{prefix}} interface={{bridge_name}}
""",
        'variables': {'bridge_name': 'bridge1', 'description': 'LAN Bridge', 'ports': ['ether2', 'ether3', 'ether4'], 'ip_address': '192.168.10.1', 'prefix': '24'}
    },
    {
        'name': 'MikroTik Bonding Interface',
        'description': 'Configure LACP bonding interface',
        'category': TemplateCategory.INTERFACE,
        'vendor': 'mikrotik_routeros',
        'content': """# Bonding Interface Configuration for MikroTik

/interface bonding
add name={{bond_name}} slaves={{slaves}} mode={{mode}} comment="{{description}}"

/ip address
add address={{ip_address}}/{{prefix}} interface={{bond_name}}
""",
        'variables': {'bond_name': 'bond1', 'slaves': 'ether1,ether2', 'mode': '802.3ad', 'description': 'LACP Trunk', 'ip_address': '10.0.0.1', 'prefix': '30'}
    },
    {
        'name': 'FRR BGP Configuration',
        'description': 'BGP configuration for FRR Linux router',
        'category': TemplateCategory.BGP,
        'vendor': 'frr_linux',
        'content': """router bgp {{ as_number }}
  bgp router-id {{ router_id }}
  !
  {% for neighbor in neighbors %}
  neighbor {{ neighbor.ip }} remote-as {{ neighbor.as }}
  {% if neighbor.password %}
  neighbor {{ neighbor.ip }} password {{ neighbor.password }}
  {% endif %}
  {% endfor %}
  !
  address-family ipv4 unicast
  {% for neighbor in neighbors %}
    neighbor {{ neighbor.ip }} activate
  {% endfor %}
  exit-address-family
""",
        'variables': {'as_number': '65001', 'router_id': '10.0.0.1', 'neighbors': []}
    },
    {
        'name': 'FRR SD-WAN VRF',
        'description': 'VRF configuration for SD-WAN style network',
        'category': TemplateCategory.ROUTING,
        'vendor': 'frr_linux',
        'content': """vrf {{ vrf_name }}
 description {{ description }}
 rd {{ rd }}
 route-target import {{ rt_import }}
 route-target export {{ rt_export }}
!""",
        'variables': {'vrf_name': 'CUSTOMER_A', 'description': 'Customer A VRF', 'rd': '65001:100', 'rt_import': '65001:100', 'rt_export': '65001:100'}
    },
    {
        'name': 'FRR SD-WAN BGP VPNv4',
        'description': 'BGP VPNv4 for SD-WAN overlay',
        'category': TemplateCategory.BGP,
        'vendor': 'frr_linux',
        'content': """router bgp {{ as_number }}
  bgp router-id {{ router_id }}
  !
  address-family vpnv4 unicast
  neighbor {{ neighbor_ip }} activate
  neighbor {{ neighbor_ip }} send-community both
  exit-address-family
  !
  address-family ipv4 vrf {{ vrf_name }}
  redistribute connected
  redistribute static
  exit-address-family
""",
        'variables': {'as_number': '65001', 'router_id': '10.0.0.1', 'neighbor_ip': '10.0.0.2', 'vrf_name': 'CUSTOMER_A'}
    },
    {
        'name': 'FRR SD-WAN Overlay',
        'description': 'Complete SD-WAN overlay configuration',
        'category': TemplateCategory.BGP,
        'vendor': 'frr_linux',
        'content': """!
! SD-WAN Overlay Configuration
!
bfd
!
mpls ldp
!
router bgp {{ as_number }}
  bgp router-id {{ router_id }}
  !
  neighbor {{ overlay_neighbor }} remote-as {{ as_number }}
  neighbor {{ overlay_neighbor }} update-source lo
  neighbor {{ overlay_neighbor }} bfd
  !
  address-family vpnv4 unicast
    neighbor {{ overlay_neighbor }} activate
    neighbor {{ overlay_neighbor }} route-reflector-client
    neighbor {{ overlay_neighbor }} send-community both
  exit-address-family
  !
  address-family ipv4 vrf {{ vrf_name }}
    redistribute connected
    redistribute static
  exit-address-family
""",
        'variables': {'as_number': '65001', 'router_id': '10.0.0.1', 'overlay_neighbor': '10.0.0.2', 'vrf_name': 'CUSTOMER_A'}
    }
]

for t_data in templates_data:
    template = ConfigTemplate(
        name=t_data['name'],
        description=t_data['description'],
        category=t_data['category'],
        vendor=t_data['vendor'],
        content=t_data['content'],
        variables=t_data['variables'],
        is_builtin=True
    )
    db.add(template)

db.commit()
print(f'Created {len(templates_data)} builtin templates')
db.close()
