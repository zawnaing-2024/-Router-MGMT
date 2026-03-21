from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum


class VendorEnum(str, Enum):
    CISCO_IOS = "cisco_ios"
    CISCO_IOS_XE = "cisco_ios_xe"
    JUNIPER_JUNOS = "juniper_junos"
    MIKROTIK_ROUTEROS = "mikrotik_routeros"
    HUAWEI = "huawei"
    ARISTA_EOS = "arista_eos"
    VYOS = "vyos"
    FRR_LINUX = "frr_linux"
    GENERIC = "generic"


class RouterStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    WARNING = "warning"
    UNKNOWN = "unknown"


class JobType(str, Enum):
    BACKUP = "backup"
    COMMAND = "command"
    TEMPLATE = "template"
    PING = "ping"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class TemplateCategoryEnum(str, Enum):
    OSPF = "ospf"
    BGP = "bgp"
    VLAN = "vlan"
    QOS = "qos"
    FIREWALL = "firewall"
    NAT = "nat"
    ROUTING = "routing"
    SECURITY = "security"
    WIRELESS = "wireless"
    VPN = "vpn"
    INTERFACE = "interface"
    OTHER = "other"


class RouterBase(BaseModel):
    hostname: str = Field(..., min_length=1, max_length=255)
    ip_address: str = Field(..., min_length=1, max_length=45)
    port: int = Field(default=22, ge=1, le=65535)
    vendor: VendorEnum
    username: str = Field(..., min_length=1, max_length=128)
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    location: Optional[str] = None
    tags: list[str] = []
    notes: Optional[str] = None


class RouterCreate(RouterBase):
    password: str


class RouterUpdate(BaseModel):
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    vendor: Optional[VendorEnum] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None


class RouterResponse(RouterBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: RouterStatus
    uptime_seconds: Optional[int]
    version: Optional[str]
    last_seen: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


class RouterListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    hostname: str
    ip_address: str
    vendor: VendorEnum
    status: RouterStatus
    uptime_seconds: Optional[int]
    version: Optional[str]
    location: Optional[str]
    last_seen: Optional[datetime]


class ConfigBackupBase(BaseModel):
    router_id: int
    content: str
    source: str = "manual"


class ConfigBackupCreate(ConfigBackupBase):
    pass


class ConfigBackupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    router_id: int
    checksum: str
    source: str
    size_bytes: int
    filename: Optional[str] = None
    created_at: datetime


class ConfigBackupDetailResponse(ConfigBackupResponse):
    content: str


class ConfigTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: TemplateCategoryEnum = TemplateCategoryEnum.OTHER
    vendor: VendorEnum
    content: str
    variables: dict = {}


class ConfigTemplateCreate(ConfigTemplateBase):
    pass


class ConfigTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[TemplateCategoryEnum] = None
    vendor: Optional[VendorEnum] = None
    content: Optional[str] = None
    variables: Optional[dict] = None


class ConfigTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str]
    category: TemplateCategoryEnum
    vendor: VendorEnum
    variables: dict
    is_builtin: bool
    created_at: datetime
    updated_at: Optional[datetime]


class TemplateRenderRequest(BaseModel):
    variables: dict = {}


class TemplateRenderResponse(BaseModel):
    rendered: str


class AISuggestionRequest(BaseModel):
    category: TemplateCategoryEnum
    vendor: VendorEnum
    description: Optional[str] = None
    network_info: Optional[str] = None


class AISuggestionResponse(BaseModel):
    suggestion: str
    configuration: str
    explanation: Optional[str] = None


class ScheduledJobBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    job_type: JobType
    router_id: Optional[int] = None
    template_id: Optional[int] = None
    command: Optional[str] = None
    schedule: str = Field(..., pattern=r'^[\d\*\/\-\,\s]+$')
    ping_target: Optional[str] = None
    ping_source: Optional[str] = None
    ping_count: int = 4


class ScheduledJobCreate(ScheduledJobBase):
    pass


class ScheduledJobUpdate(BaseModel):
    name: Optional[str] = None
    router_id: Optional[int] = None
    template_id: Optional[int] = None
    command: Optional[str] = None
    schedule: Optional[str] = None
    enabled: Optional[bool] = None
    ping_target: Optional[str] = None
    ping_source: Optional[str] = None
    ping_count: Optional[int] = None


class ScheduledJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    job_type: JobType
    router_id: Optional[int]
    template_id: Optional[int]
    schedule: str
    enabled: bool
    last_run: Optional[datetime]
    last_status: Optional[JobStatus]
    last_output: Optional[str]
    ping_target: Optional[str]
    ping_source: Optional[str]
    ping_count: int
    created_at: datetime
    updated_at: Optional[datetime]


class CommandRequest(BaseModel):
    command: str


class CommandResponse(BaseModel):
    output: str
    success: bool
    error: Optional[str] = None


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    latency_ms: Optional[float] = None


class BackupCompareRequest(BaseModel):
    backup_id_1: int
    backup_id_2: int


class BackupCompareResponse(BaseModel):
    diff: str
    added_lines: int
    removed_lines: int
    unchanged_lines: int


class DashboardStats(BaseModel):
    total_routers: int
    online_routers: int
    offline_routers: int
    warning_routers: int
    backups_today: int
    backups_this_week: int
    failed_jobs: int


class RouterGroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    router_ids: list[int] = []
    tags: list[str] = []


class RouterGroupCreate(RouterGroupBase):
    pass


class RouterGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    router_ids: Optional[list[int]] = None
    tags: Optional[list[str]] = None


class RouterGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str]
    router_ids: list[int]
    tags: list[str]
    created_at: datetime
    updated_at: Optional[datetime]


class BatchCommandRequest(BaseModel):
    router_ids: list[int]
    command: str


class BatchCommandResult(BaseModel):
    router_id: int
    hostname: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None


class BatchCommandResponse(BaseModel):
    results: list[BatchCommandResult]
    total: int
    successful: int
    failed: int


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    action: str
    entity_type: str
    entity_id: Optional[int]
    details: dict
    ip_address: Optional[str]
    created_at: datetime


class AuditLogQuery(BaseModel):
    action: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    skip: int = 0
    limit: int = 100


class ExportData(BaseModel):
    routers: list
    groups: list
    templates: list


class RemediationScriptBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_condition: str
    commands: list[str] = []
    enabled: bool = True
    auto_execute: bool = False


class RemediationScriptCreate(RemediationScriptBase):
    pass


class RemediationScriptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_condition: Optional[str] = None
    commands: Optional[list[str]] = None
    enabled: Optional[bool] = None
    auto_execute: Optional[bool] = None


class RemediationScriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str]
    trigger_condition: str
    commands: list[str]
    enabled: bool
    auto_execute: bool
    created_at: datetime
    updated_at: Optional[datetime]


class NotificationChannelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    channel_type: str
    config: dict = {}
    enabled: bool = True
    events: list[str] = []


class NotificationChannelCreate(NotificationChannelBase):
    pass


class NotificationChannelUpdate(BaseModel):
    name: Optional[str] = None
    channel_type: Optional[str] = None
    config: Optional[dict] = None
    enabled: Optional[bool] = None
    events: Optional[list[str]] = None


class NotificationChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    channel_type: str
    config: dict
    enabled: bool
    events: list[str]
    created_at: datetime
    updated_at: Optional[datetime]


class WebhookBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: str
    events: list[str] = []
    headers: dict = {}
    enabled: bool = True
    retry_count: int = 3


class WebhookCreate(WebhookBase):
    pass


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[list[str]] = None
    headers: Optional[dict] = None
    enabled: Optional[bool] = None
    retry_count: Optional[int] = None


class WebhookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    url: str
    events: list[str]
    headers: dict
    enabled: bool
    retry_count: int
    last_triggered: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


class UptimeReport(BaseModel):
    router_id: int
    hostname: str
    uptime_percent: float
    total_checks: int
    successful_checks: int
    failed_checks: int
    avg_latency_ms: Optional[float] = None


class UptimeReportQuery(BaseModel):
    start_date: datetime
    end_date: datetime
    router_ids: Optional[list[int]] = None


class ConfigChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    router_id: int
    backup_id: Optional[int]
    change_type: str
    detected_at: datetime
    details: dict


class FirmwareInfo(BaseModel):
    router_id: int
    hostname: str
    version: Optional[str] = None
    os_type: Optional[str] = None
    collected_at: datetime


class RouterLogBase(BaseModel):
    router_id: int
    level: str = "info"
    source: str
    message: str
    details: dict = {}


class RouterLogCreate(RouterLogBase):
    pass


class RouterLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    router_id: int
    level: str
    source: str
    message: str
    details: dict
    created_at: datetime


class ManualTriggerRequest(BaseModel):
    router_ids: list[int] = []
    message: Optional[str] = None
