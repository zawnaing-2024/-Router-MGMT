from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models import ConfigTemplate, Router
from app.schemas import (
    ConfigTemplateCreate, ConfigTemplateUpdate, ConfigTemplateResponse,
    TemplateRenderRequest, TemplateRenderResponse,
    AISuggestionRequest, AISuggestionResponse
)
from app.services import TemplateService
from app.services.ai_service import ai_service
from app.core.security import decrypt_password
from app.services.ssh_service import SSHService


class PromptGenerateRequest(BaseModel):
    prompt: str
    vendor: str


class PromptGenerateResponse(BaseModel):
    prompt: str
    vendor: str
    configuration: str
    explanation: str


class ApplyConfigRequest(BaseModel):
    configuration: str
    router_id: int


class ApplyConfigResponse(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("", response_model=List[ConfigTemplateResponse])
def list_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    vendor: str = None,
    category: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(ConfigTemplate)
    
    if vendor:
        query = query.filter(ConfigTemplate.vendor == vendor)
    if category:
        query = query.filter(ConfigTemplate.category == category)
    
    return query.order_by(ConfigTemplate.name).offset(skip).limit(limit).all()


@router.get("/{template_id}", response_model=ConfigTemplateResponse)
def get_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("", response_model=ConfigTemplateResponse, status_code=201)
def create_template(template_data: ConfigTemplateCreate, db: Session = Depends(get_db)):
    template_service = TemplateService()
    valid, msg = template_service.validate(template_data.content)
    
    if not valid:
        raise HTTPException(status_code=400, detail=f"Invalid template: {msg}")
    
    template = ConfigTemplate(
        name=template_data.name,
        description=template_data.description,
        category=template_data.category,
        vendor=template_data.vendor,
        content=template_data.content,
        variables=template_data.variables
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.put("/{template_id}", response_model=ConfigTemplateResponse)
def update_template(template_id: int, template_data: ConfigTemplateUpdate, db: Session = Depends(get_db)):
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_data = template_data.model_dump(exclude_unset=True)
    
    if "content" in update_data:
        template_service = TemplateService()
        valid, msg = template_service.validate(update_data["content"])
        if not valid:
            raise HTTPException(status_code=400, detail=f"Invalid template: {msg}")
    
    for key, value in update_data.items():
        setattr(template, key, value)
    
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()


@router.post("/{template_id}/render", response_model=TemplateRenderResponse)
def render_template(template_id: int, render_data: TemplateRenderRequest, db: Session = Depends(get_db)):
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template_service = TemplateService()
    rendered = template_service.render(template.content, render_data.variables)
    
    return TemplateRenderResponse(rendered=rendered)


@router.post("/ai-suggest", response_model=AISuggestionResponse)
async def get_ai_suggestion(request: AISuggestionRequest):
    result = await ai_service.get_suggestion(
        category=request.category.value,
        vendor=request.vendor,
        description=request.description,
        network_info=request.network_info
    )
    return AISuggestionResponse(**result)


@router.get("/categories/list")
def list_categories():
    return {
        "categories": [
            {"value": "ospf", "label": "OSPF", "icon": "Route"},
            {"value": "bgp", "label": "BGP", "icon": "Globe"},
            {"value": "vlan", "label": "VLAN", "icon": "Network"},
            {"value": "interface", "label": "Interface", "icon": "Ethernet"},
            {"value": "qos", "label": "QoS", "icon": "Gauge"},
            {"value": "firewall", "label": "Firewall", "icon": "Shield"},
            {"value": "nat", "label": "NAT", "icon": "RefreshCw"},
            {"value": "routing", "label": "Routing", "icon": "ArrowRight"},
            {"value": "security", "label": "Security", "icon": "Lock"},
            {"value": "wireless", "label": "Wireless", "icon": "Wifi"},
            {"value": "vpn", "label": "VPN", "icon": "Key"},
            {"value": "other", "label": "Other", "icon": "MoreHorizontal"},
        ]
    }


@router.post("/prompt/generate", response_model=PromptGenerateResponse)
async def generate_from_prompt(request: PromptGenerateRequest):
    result = await ai_service.generate_from_prompt(
        prompt=request.prompt,
        vendor=request.vendor
    )
    return PromptGenerateResponse(**result)


@router.post("/prompt/apply", response_model=ApplyConfigResponse)
def apply_configuration(request: ApplyConfigRequest, db: Session = Depends(get_db)):
    router_obj = db.query(Router).filter(Router.id == request.router_id).first()
    if not router_obj:
        raise HTTPException(status_code=404, detail="Router not found")
    
    password = decrypt_password(router_obj.password_encrypted) if router_obj.password_encrypted else None
    
    ssh = SSHService(
        host=router_obj.ip_address,
        port=router_obj.port,
        username=router_obj.username,
        password=password
    )
    
    success, ssh_msg = ssh.connect()
    if not success:
        return ApplyConfigResponse(
            success=False,
            output="",
            error=f"SSH connection failed: {ssh_msg}"
        )
    
    commands = _parse_config_commands(request.configuration, router_obj.vendor)
    
    all_output = []
    all_errors = []
    
    for cmd in commands:
        if cmd.strip().startswith("#") or not cmd.strip():
            continue
        
        success, output, error = ssh.execute_command(cmd, timeout=30)
        if success:
            all_output.append(f"{cmd}\n{output}")
        else:
            all_errors.append(f"Error executing '{cmd}': {error}")
            all_output.append(f"{cmd}\n{error}")
    
    ssh.close()
    
    return ApplyConfigResponse(
        success=len(all_errors) == 0,
        output="\n".join(all_output),
        error="\n".join(all_errors) if all_errors else None
    )


def _parse_config_commands(config: str, vendor: str) -> List[str]:
    commands = []
    
    if vendor == "mikrotik_routeros":
        current_path = ""
        for line in config.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue
            
            if line.startswith("/"):
                parts = line.split(None, 1)
                if len(parts) > 1:
                    current_path = parts[0]
                    remaining = parts[1]
                    if remaining.startswith("add ") or remaining.startswith("set ") or remaining.startswith("remove ") or remaining.startswith("enable ") or remaining.startswith("disable "):
                        commands.append(f"{current_path} {remaining}")
                    else:
                        commands.append(line)
                else:
                    current_path = line
                    commands.append(line)
            elif line.startswith("add ") or line.startswith("set ") or line.startswith("remove ") or line.startswith("enable ") or line.startswith("disable "):
                if current_path:
                    commands.append(f"{current_path} {line}")
                else:
                    commands.append(line)
            else:
                if current_path and line:
                    commands.append(f"{current_path} {line}")
                elif line:
                    commands.append(line)
    else:
        for line in config.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue
            commands.append(line)
    
    return commands
