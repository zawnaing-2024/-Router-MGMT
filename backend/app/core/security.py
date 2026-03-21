from cryptography.fernet import Fernet
from app.core.config import settings
import base64
import hashlib


def get_encryption_key():
    key = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key)


fernet = Fernet(get_encryption_key())


def encrypt_password(password: str) -> str:
    return fernet.encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    return fernet.decrypt(encrypted.encode()).decode()
