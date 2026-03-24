from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class VendorEnum(str, enum.Enum):
    CISCO_IOS = "cisco_ios"
    CISCO_IOS_XE = "cisco_ios_xe"
    JUNIPER_JUNOS = "juniper_junos"
    MIKROTIK_ROUTEROS = "mikrotik_routeros"
    HUAWEI = "huawei"
    ARISTA_EOS = "arista_eos"
    VYOS = "vyos"
    FRR_LINUX = "frr_linux"
    GENERIC = "generic"
    LINUX = "linux"


class RouterStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    WARNING = "warning"
    UNKNOWN = "unknown"


class JobType(str, enum.Enum):
    BACKUP = "backup"
    COMMAND = "command"
    TEMPLATE = "template"
    PING = "ping"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Router(Base):
    __tablename__ = "routers"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    port = Column(Integer, default=22)
    vendor = Column(String(32), nullable=False)
    username = Column(String(128), nullable=False)
    password_encrypted = Column(Text, nullable=False)
    ssh_key = Column(Text, nullable=True)
    sudo_password_encrypted = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    tags = Column(JSON, default=list)
    status = Column(Enum(RouterStatus), default=RouterStatus.UNKNOWN)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    uptime_seconds = Column(Integer, nullable=True)
    version = Column(String(128), nullable=True)
    custom_commands = Column(JSON, default=list)
    project_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    backups = relationship("ConfigBackup", back_populates="router", cascade="all, delete-orphan")
    jobs = relationship("ScheduledJob", back_populates="router", cascade="all, delete-orphan")


class ConfigBackup(Base):
    __tablename__ = "config_backups"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    checksum = Column(String(64), nullable=False)
    source = Column(String(32), default="manual")
    size_bytes = Column(Integer, default=0)
    filename = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    router = relationship("Router", back_populates="backups")


class TemplateCategory(str, enum.Enum):
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


class ConfigTemplate(Base):
    __tablename__ = "config_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(Enum(TemplateCategory), default=TemplateCategory.OTHER)
    vendor = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    variables = Column(JSON, default=dict)
    is_builtin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    job_type = Column(Enum(JobType), nullable=False)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=True)
    template_id = Column(Integer, ForeignKey("config_templates.id", ondelete="SET NULL"), nullable=True)
    command = Column(Text, nullable=True)
    schedule = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    last_run = Column(DateTime(timezone=True), nullable=True)
    last_status = Column(Enum(JobStatus), nullable=True)
    last_output = Column(Text, nullable=True)
    ping_target = Column(String(255), nullable=True)
    ping_source = Column(String(255), nullable=True)
    ping_count = Column(Integer, default=4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    router = relationship("Router", back_populates="jobs")
    template = relationship("ConfigTemplate")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(64), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False, index=True)
    cpu_percent = Column(Integer, nullable=True)
    memory_percent = Column(Integer, nullable=True)
    memory_used_mb = Column(Integer, nullable=True)
    memory_total_mb = Column(Integer, nullable=True)
    disk_percent = Column(Integer, nullable=True)
    uptime_seconds = Column(Integer, nullable=True)
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    router = relationship("Router", backref="performance_metrics")


class PingMetric(Base):
    __tablename__ = "ping_metrics"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("scheduled_jobs.id", ondelete="CASCADE"), nullable=True, index=True)
    target = Column(String(255), nullable=False)
    latency_avg_ms = Column(Integer, nullable=True)
    latency_min_ms = Column(Integer, nullable=True)
    latency_max_ms = Column(Integer, nullable=True)
    packet_loss_percent = Column(Integer, default=0)
    packets_sent = Column(Integer, default=0)
    packets_received = Column(Integer, default=0)
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    router = relationship("Router", backref="ping_metrics")
    job = relationship("ScheduledJob", backref="ping_metrics")


class RouterGroup(Base):
    __tablename__ = "router_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    router_ids = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RemediationScript(Base):
    __tablename__ = "remediation_scripts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    trigger_condition = Column(String(255), nullable=False)
    commands = Column(JSON, default=list)
    enabled = Column(Boolean, default=True)
    auto_execute = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    channel_type = Column(String(32), nullable=False)
    config = Column(JSON, default=dict)
    enabled = Column(Boolean, default=True)
    events = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(512), nullable=False)
    events = Column(JSON, default=list)
    headers = Column(JSON, default=dict)
    enabled = Column(Boolean, default=True)
    retry_count = Column(Integer, default=3)
    last_triggered = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ConfigChange(Base):
    __tablename__ = "config_changes"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False)
    backup_id = Column(Integer, ForeignKey("config_backups.id", ondelete="CASCADE"), nullable=True)
    change_type = Column(String(32), nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    details = Column(JSON, default=dict)

    router = relationship("Router", backref="config_changes")
    backup = relationship("ConfigBackup", backref="config_changes")


class RouterLog(Base):
    __tablename__ = "router_logs"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False)
    level = Column(String(16), default="info")
    source = Column(String(64), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    router = relationship("Router", backref="logs")


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(16), default="VIEWER")
    router_ids = Column(JSON, default=list)
    project_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
