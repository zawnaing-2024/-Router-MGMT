from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from app.core.database import engine, Base, SessionLocal
from app.core.config import settings
from app.api import (
    routers_router, backups_router, templates_router,
    jobs_router, dashboard_router, router_groups_router,
    batch_router, audit_logs_router, export_import_router,
    reports_router, remediation_router, notifications_router,
    router_logs_router
)
from app.api.terminal import websocket_endpoint
from app.api.metrics import router as metrics_router
from app.api.ping_metrics import router as ping_metrics_router


def collect_metrics_job():
    try:
        from app.models import Router, PerformanceMetric, RouterStatus
        from app.services.monitoring_service import MonitoringService
        from app.services.ssh_service import SSHService
        from app.core.security import decrypt_password
        from sqlalchemy.orm import Session
        
        db = SessionLocal()
        try:
            routers = db.query(Router).all()
            
            for router in routers:
                try:
                    password = decrypt_password(router.password_encrypted) if router.password_encrypted else None
                    ssh = SSHService(
                        host=router.ip_address,
                        port=router.port,
                        username=router.username,
                        password=password,
                        ssh_key=router.ssh_key
                    )
                    
                    success, _ = ssh.connect()
                    if not success:
                        router.status = RouterStatus.OFFLINE
                        db.commit()
                        continue
                    
                    monitoring = MonitoringService(ssh)
                    metrics = monitoring.collect_metrics(router.vendor)
                    
                    if "error" not in metrics:
                        perf_metric = PerformanceMetric(
                            router_id=router.id,
                            cpu_percent=metrics.get("cpu_percent"),
                            memory_percent=metrics.get("memory_percent"),
                            memory_used_mb=metrics.get("memory_used_mb"),
                            memory_total_mb=metrics.get("memory_total_mb"),
                            disk_percent=metrics.get("disk_percent"),
                            uptime_seconds=metrics.get("uptime_seconds"),
                            collected_at=datetime.utcnow()
                        )
                        db.add(perf_metric)
                        router.status = RouterStatus.ONLINE
                        router.last_seen = datetime.utcnow()
                        
                        if metrics.get("uptime_seconds"):
                            router.uptime_seconds = metrics.get("uptime_seconds")
                        if metrics.get("version"):
                            router.version = metrics.get("version")
                        
                        db.commit()
                    
                    ssh.close()
                except Exception as e:
                    print(f"Failed to collect metrics for {router.hostname}: {e}")
        finally:
            db.close()
        print(f"[{datetime.now()}] Metrics collection completed")
    except Exception as e:
        print(f"Metrics collection error: {e}")


scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    
    scheduler.add_job(
        collect_metrics_job,
        'interval',
        minutes=5,
        id='metrics_collection',
        replace_existing=True
    )
    scheduler.start()
    print("Scheduler started - Metrics collection every 5 minutes")
    
    yield
    
    scheduler.shutdown()


app = FastAPI(
    title="Router MGMT API",
    description="Router Automation & Management Portal API",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routers_router, prefix="/api")
app.include_router(backups_router, prefix="/api")
app.include_router(templates_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(metrics_router)
app.include_router(ping_metrics_router, prefix="/api")
app.include_router(router_groups_router, prefix="/api")
app.include_router(batch_router, prefix="/api")
app.include_router(audit_logs_router, prefix="/api")
app.include_router(export_import_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(remediation_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(router_logs_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Router MGMT API", "version": "0.1.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.websocket("/ws/terminal/{router_id}")
async def terminal_websocket(websocket: WebSocket, router_id: int):
    await websocket_endpoint(websocket, router_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
