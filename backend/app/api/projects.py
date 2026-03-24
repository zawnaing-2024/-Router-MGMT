from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy import text

from app.core.database import get_db

router = APIRouter(prefix="/projects", tags=["Projects"])


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    model_config = {"from_attributes": True}
    
    id: int
    created_at: datetime


@router.get("", response_model=List[ProjectResponse])
def list_projects(authorization: str = Header(None), db: Session = Depends(get_db)):
    results = db.execute(text("SELECT * FROM projects")).fetchall()
    return [
        {"id": r[0], "name": r[1], "description": r[2], "created_at": r[3]}
        for r in results
    ]


@router.post("", response_model=ProjectResponse)
def create_project(data: ProjectCreate, authorization: str = Header(None), db: Session = Depends(get_db)):
    db.execute(
        text("INSERT INTO projects (name, description) VALUES (:name, :description)"),
        {"name": data.name, "description": data.description}
    )
    db.commit()
    result = db.execute(text("SELECT * FROM projects ORDER BY id DESC LIMIT 1")).fetchone()
    return {
        "id": result[0],
        "name": result[1],
        "description": result[2],
        "created_at": result[3]
    }


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, data: ProjectCreate, authorization: str = Header(None), db: Session = Depends(get_db)):
    db.execute(
        text("UPDATE projects SET name = :name, description = :description WHERE id = :id"),
        {"name": data.name, "description": data.description, "id": project_id}
    )
    db.commit()
    result = db.execute(text("SELECT * FROM projects WHERE id = :id"), {"id": project_id}).fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": result[0],
        "name": result[1],
        "description": result[2],
        "created_at": result[3]
    }


@router.delete("/{project_id}")
def delete_project(project_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM projects WHERE id = :id"), {"id": project_id})
    db.commit()
    return {"message": "Project deleted"}
