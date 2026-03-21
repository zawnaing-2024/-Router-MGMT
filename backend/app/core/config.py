from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "Router MGMT"
    DEBUG: bool = True
    
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/router_mgmt"
    
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ENCRYPTION_KEY: str = "32-byte-encryption-key-here!!"
    
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    SSH_TIMEOUT: int = 30
    BACKUP_DIR: str = "/var/router-mgmt/backups"
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
