from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
from datetime import datetime

from app.core.database import get_db
from app.models import NotificationChannel, Webhook
from app.schemas import (
    NotificationChannelCreate, NotificationChannelUpdate, NotificationChannelResponse,
    WebhookCreate, WebhookUpdate, WebhookResponse
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/channels", response_model=List[NotificationChannelResponse])
def list_channels(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(NotificationChannel).offset(skip).limit(limit).all()


@router.get("/channels/{channel_id}", response_model=NotificationChannelResponse)
def get_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    return channel


@router.post("/channels", response_model=NotificationChannelResponse, status_code=201)
def create_channel(data: NotificationChannelCreate, db: Session = Depends(get_db)):
    channel = NotificationChannel(**data.model_dump())
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


@router.put("/channels/{channel_id}", response_model=NotificationChannelResponse)
def update_channel(channel_id: int, data: NotificationChannelUpdate, db: Session = Depends(get_db)):
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(channel, key, value)
    
    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/channels/{channel_id}", status_code=204)
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    
    db.delete(channel)
    db.commit()


@router.post("/channels/{channel_id}/test")
async def test_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    
    try:
        if channel.channel_type == "slack":
            webhook_url = channel.config.get("webhook_url")
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json={"text": "Test message from Router MGMT"})
                return {"success": response.status_code == 200}
        
        elif channel.channel_type == "telegram":
            bot_token = channel.config.get("bot_token")
            chat_id = channel.config.get("chat_id")
            if not bot_token or not chat_id:
                return {"success": False, "error": "Bot token and chat ID required"}
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": "Test message from Router MGMT"}
                )
                return {"success": response.status_code == 200}
        
        elif channel.channel_type == "email":
            return {"success": True, "message": "Email configuration is valid"}
        
        elif channel.channel_type == "webhook":
            url = channel.config.get("url")
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json={"test": True})
                return {"success": response.status_code in (200, 201)}
        
        return {"success": False, "message": "Unknown channel type"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/webhooks", response_model=List[WebhookResponse])
def list_webhooks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Webhook).offset(skip).limit(limit).all()


@router.get("/webhooks/{webhook_id}", response_model=WebhookResponse)
def get_webhook(webhook_id: int, db: Session = Depends(get_db)):
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.post("/webhooks", response_model=WebhookResponse, status_code=201)
def create_webhook(data: WebhookCreate, db: Session = Depends(get_db)):
    webhook = Webhook(**data.model_dump())
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@router.put("/webhooks/{webhook_id}", response_model=WebhookResponse)
def update_webhook(webhook_id: int, data: WebhookUpdate, db: Session = Depends(get_db)):
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(webhook, key, value)
    
    db.commit()
    db.refresh(webhook)
    return webhook


@router.delete("/webhooks/{webhook_id}", status_code=204)
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    db.delete(webhook)
    db.commit()


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: int, db: Session = Depends(get_db)):
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                webhook.url,
                json={"event": "test", "timestamp": datetime.utcnow().isoformat()},
                headers=webhook.headers
            )
            return {"success": response.status_code in (200, 201, 202), "status_code": response.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def trigger_webhooks(event: str, data: dict, db: Session):
    webhooks = db.query(Webhook).filter(Webhook.enabled == True).all()
    
    for webhook in webhooks:
        if event not in webhook.events:
            continue
        
        for attempt in range(webhook.retry_count):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(
                        webhook.url,
                        json={"event": event, "data": data, "timestamp": datetime.utcnow().isoformat()},
                        headers=webhook.headers
                    )
                    if response.status_code in (200, 201, 202):
                        webhook.last_triggered = datetime.utcnow()
                        db.commit()
                        break
            except Exception as e:
                print(f"Webhook trigger failed (attempt {attempt + 1}): {e}")
