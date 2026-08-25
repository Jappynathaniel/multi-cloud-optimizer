import base64
import hashlib
import json
from cryptography.fernet import Fernet

from app.config import get_settings


def _fernet() -> Fernet:
    key = get_settings().encryption_key
    if not key:
        # Safe only for a disposable local demo; Render must provide REDBRIDGE_ENCRYPTION_KEY.
        key = base64.urlsafe_b64encode(hashlib.sha256(b"redbridge-local-development-only").digest()).decode()
    return Fernet(key.encode())


def encrypt_config(config: dict) -> str:
    return _fernet().encrypt(json.dumps(config).encode()).decode()


def decrypt_config(value: str) -> dict:
    return json.loads(_fernet().decrypt(value.encode()).decode())

