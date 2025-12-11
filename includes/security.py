"""Security utilities for encryption and data protection."""
import base64
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

import config
from .logger import setup_logger

logger = setup_logger(__name__)


def encrypt_data(data: str) -> Optional[str]:
    """Encrypt sensitive data.
    
    Args:
        data: Plain text data
        
    Returns:
        Encrypted data as base64 string or None on error
    """
    try:
        if not data:
            return None
        
        fernet = Fernet(config.ENCRYPTION_KEY)
        encrypted = fernet.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return None


def decrypt_data(encrypted_data: str) -> Optional[str]:
    """Decrypt sensitive data.
    
    Args:
        encrypted_data: Encrypted data as base64 string
        
    Returns:
        Decrypted plain text or None on error
    """
    try:
        if not encrypted_data:
            return None
        
        fernet = Fernet(config.ENCRYPTION_KEY)
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
    except InvalidToken:
        logger.error("Invalid encryption key or corrupted data")
        return None
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return None


def generate_encryption_key() -> str:
    """Generate a new encryption key.
    
    Returns:
        New Fernet key as string
    """
    return Fernet.generate_key().decode()
