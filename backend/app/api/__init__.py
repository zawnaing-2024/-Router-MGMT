from app.api.routers import router as routers_router
from app.api.backups import router as backups_router
from app.api.templates import router as templates_router
from app.api.jobs import router as jobs_router
from app.api.dashboard import router as dashboard_router
from app.api.metrics import router as metrics_router
from app.api.ping_metrics import router as ping_metrics_router
from app.api.router_groups import router as router_groups_router
from app.api.batch import router as batch_router
from app.api.audit_logs import router as audit_logs_router
from app.api.export_import import router as export_import_router
from app.api.reports import router as reports_router
from app.api.remediation import router as remediation_router
from app.api.notifications import router as notifications_router
from app.api.router_logs import router as router_logs_router
from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.api.api_tokens import router as api_tokens_router

__all__ = [
    "routers_router", "backups_router", "templates_router", "jobs_router",
    "dashboard_router", "metrics_router", "ping_metrics_router", "router_groups_router",
    "batch_router", "audit_logs_router", "export_import_router",
    "reports_router", "remediation_router", "notifications_router",
    "router_logs_router", "auth_router", "projects_router", "api_tokens_router"
]
