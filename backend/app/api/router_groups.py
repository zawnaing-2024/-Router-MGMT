from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models import RouterGroup
from app.schemas import (
    RouterGroupCreate, RouterGroupUpdate, RouterGroupResponse
)

router = APIRouter(prefix="/router-groups", tags=["Router Groups"])


@router.get("", response_model=List[RouterGroupResponse])
def list_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    return db.query(RouterGroup).order_by(RouterGroup.name).offset(skip).limit(limit).all()


@router.get("/{group_id}", response_model=RouterGroupResponse)
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(RouterGroup).filter(RouterGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Router group not found")
    return group


@router.post("", response_model=RouterGroupResponse, status_code=201)
def create_group(group_data: RouterGroupCreate, db: Session = Depends(get_db)):
    existing = db.query(RouterGroup).filter(RouterGroup.name == group_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Router group with this name already exists")
    
    group = RouterGroup(
        name=group_data.name,
        description=group_data.description,
        router_ids=group_data.router_ids,
        tags=group_data.tags
    )
    
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.put("/{group_id}", response_model=RouterGroupResponse)
def update_group(group_id: int, group_data: RouterGroupUpdate, db: Session = Depends(get_db)):
    group = db.query(RouterGroup).filter(RouterGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Router group not found")
    
    if group_data.name and group_data.name != group.name:
        existing = db.query(RouterGroup).filter(RouterGroup.name == group_data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Router group with this name already exists")
    
    update_data = group_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(group, key, value)
    
    group.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(RouterGroup).filter(RouterGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Router group not found")
    
    db.delete(group)
    db.commit()


@router.post("/{group_id}/routers/{router_id}")
def add_router_to_group(group_id: int, router_id: int, db: Session = Depends(get_db)):
    from app.models import Router
    
    group = db.query(RouterGroup).filter(RouterGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Router group not found")
    
    router = db.query(Router).filter(Router.id == router_id).first()
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")
    
    if router_id not in group.router_ids:
        group.router_ids.append(router_id)
        group.updated_at = datetime.utcnow()
        db.commit()
    
    return {"message": "Router added to group"}


@router.delete("/{group_id}/routers/{router_id}")
def remove_router_from_group(group_id: int, router_id: int, db: Session = Depends(get_db)):
    group = db.query(RouterGroup).filter(RouterGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Router group not found")
    
    if router_id in group.router_ids:
        group.router_ids.remove(router_id)
        group.updated_at = datetime.utcnow()
        db.commit()
    
    return {"message": "Router removed from group"}
