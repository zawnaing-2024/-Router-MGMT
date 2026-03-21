from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import csv
import io

from app.core.database import get_db
from app.core.security import encrypt_password
from app.models import Router, RouterGroup, ConfigTemplate

router = APIRouter(prefix="/export", tags=["Export/Import"])


@router.get("/routers/json")
def export_routers_json(db: Session = Depends(get_db)):
    routers = db.query(Router).all()
    
    data = []
    for r in routers:
        data.append({
            "hostname": r.hostname,
            "ip_address": r.ip_address,
            "port": r.port,
            "vendor": r.vendor if r.vendor else None,
            "username": r.username,
            "location": r.location,
            "tags": r.tags,
            "notes": r.notes
        })
    
    return {"routers": data}


@router.get("/routers/csv")
def export_routers_csv(db: Session = Depends(get_db)):
    routers = db.query(Router).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["hostname", "ip_address", "port", "vendor", "username", "location", "tags", "status"])
    
    for r in routers:
        writer.writerow([
            r.hostname,
            r.ip_address,
            r.port,
            r.vendor if r.vendor else "",
            r.username,
            r.location or "",
            ",".join(r.tags) if r.tags else "",
            r.status.value if r.status else ""
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=routers.csv"}
    )


@router.get("/all/json")
def export_all_json(db: Session = Depends(get_db)):
    routers = db.query(Router).all()
    groups = db.query(RouterGroup).all()
    templates = db.query(ConfigTemplate).all()
    
    return {
        "version": "1.0",
        "exported_at": db.execute("SELECT NOW()").scalar(),
        "routers": [
            {
                "hostname": r.hostname,
                "ip_address": r.ip_address,
                "port": r.port,
                "vendor": r.vendor if r.vendor else None,
                "username": r.username,
                "location": r.location,
                "tags": r.tags,
                "notes": r.notes
            }
            for r in routers
        ],
        "groups": [
            {
                "name": g.name,
                "description": g.description,
                "router_ids": g.router_ids,
                "tags": g.tags
            }
            for g in groups
        ],
        "templates": [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category.value if t.category else None,
                "vendor": t.vendor if t.vendor else None,
                "content": t.content,
                "variables": t.variables
            }
            for t in templates
        ]
    }


@router.post("/import/routers")
def import_routers(data: dict, db: Session = Depends(get_db)):
    routers_data = data.get("routers", [])
    imported = 0
    skipped = 0
    errors = []
    
    for r_data in routers_data:
        try:
            existing = db.query(Router).filter(
                (Router.hostname == r_data["hostname"]) |
                (Router.ip_address == r_data["ip_address"])
            ).first()
            
            if existing:
                skipped += 1
                continue
            
            router = Router(
                hostname=r_data["hostname"],
                ip_address=r_data["ip_address"],
                port=r_data.get("port", 22),
                vendor=r_data["vendor"],
                username=r_data["username"],
                password_encrypted="",
                location=r_data.get("location"),
                tags=r_data.get("tags", []),
                notes=r_data.get("notes")
            )
            db.add(router)
            imported += 1
        except Exception as e:
            errors.append(f"Error importing {r_data.get('hostname', 'unknown')}: {str(e)}")
    
    db.commit()
    
    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors
    }


@router.post("/import/all")
def import_all(data: dict, db: Session = Depends(get_db)):
    results = {"routers": {"imported": 0, "skipped": 0}, "groups": {"imported": 0, "skipped": 0}, "templates": {"imported": 0, "skipped": 0}}
    
    routers_data = data.get("routers", [])
    for r_data in routers_data:
        try:
            existing = db.query(Router).filter(Router.hostname == r_data["hostname"]).first()
            if existing:
                results["routers"]["skipped"] += 1
                continue
            
            router = Router(
                hostname=r_data["hostname"],
                ip_address=r_data["ip_address"],
                port=r_data.get("port", 22),
                vendor=r_data["vendor"],
                username=r_data["username"],
                password_encrypted="",
                location=r_data.get("location"),
                tags=r_data.get("tags", []),
                notes=r_data.get("notes")
            )
            db.add(router)
            results["routers"]["imported"] += 1
        except Exception:
            results["routers"]["skipped"] += 1
    
    groups_data = data.get("groups", [])
    for g_data in groups_data:
        try:
            existing = db.query(RouterGroup).filter(RouterGroup.name == g_data["name"]).first()
            if existing:
                results["groups"]["skipped"] += 1
                continue
            
            group = RouterGroup(
                name=g_data["name"],
                description=g_data.get("description"),
                router_ids=g_data.get("router_ids", []),
                tags=g_data.get("tags", [])
            )
            db.add(group)
            results["groups"]["imported"] += 1
        except Exception:
            results["groups"]["skipped"] += 1
    
    templates_data = data.get("templates", [])
    for t_data in templates_data:
        try:
            existing = db.query(ConfigTemplate).filter(ConfigTemplate.name == t_data["name"]).first()
            if existing:
                results["templates"]["skipped"] += 1
                continue
            
            template = ConfigTemplate(
                name=t_data["name"],
                description=t_data.get("description"),
                category=t_data.get("category"),
                vendor=t_data["vendor"],
                content=t_data["content"],
                variables=t_data.get("variables", {})
            )
            db.add(template)
            results["templates"]["imported"] += 1
        except Exception:
            results["templates"]["skipped"] += 1
    
    db.commit()
    return results
