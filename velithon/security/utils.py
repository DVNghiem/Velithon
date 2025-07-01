"""Security utilities for Velithon authentication system."""

import hashlib
import hmac
import secrets
from typing import Any

try:
    from passlib.context import CryptContext
    PASSLIB_AVAILABLE = True
    
    # Create password context with bcrypt
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
except ImportError:
    PASSLIB_AVAILABLE = False
    pwd_context = None


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt if available, fallback to pbkdf2."""
    if PASSLIB_AVAILABLE and pwd_context:
        return pwd_context.hash(password)
    
    # Fallback to pbkdf2_hmac
    salt = secrets.token_bytes(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt.hex() + ':' + key.hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    if PASSLIB_AVAILABLE and pwd_context:
        return pwd_context.verify(plain_password, hashed_password)
    
    # Fallback verification for pbkdf2_hmac
    try:
        salt_hex, key_hex = hashed_password.split(':')
        salt = bytes.fromhex(salt_hex)
        stored_key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt, 100000)
        return hmac.compare_digest(stored_key, new_key)
    except (ValueError, TypeError):
        return False


def generate_secret_key(length: int = 32) -> str:
    """Generate a secure random secret key."""
    return secrets.token_urlsafe(length)


def constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks."""
    return hmac.compare_digest(a.encode(), b.encode())


def generate_api_key(prefix: str = "", length: int = 32) -> str:
    """Generate a secure API key with optional prefix."""
    key = secrets.token_urlsafe(length)
    return f"{prefix}_{key}" if prefix else key


def hash_api_key(api_key: str, secret: str) -> str:
    """Hash an API key with a secret for secure storage."""
    return hmac.new(
        secret.encode(),
        api_key.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_api_key(api_key: str, hashed_key: str, secret: str) -> bool:
    """Verify an API key against its hash."""
    expected_hash = hash_api_key(api_key, secret)
    return constant_time_compare(expected_hash, hashed_key)


class SecurityConfig:
    """Configuration for security settings."""
    
    def __init__(
        self,
        secret_key: str | None = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        auto_error: bool = True,
        require_https: bool = False,
        cookie_secure: bool = False,
        cookie_httponly: bool = True,
        cookie_samesite: str = "lax",
    ):
        """Initialize security configuration."""
        self.secret_key = secret_key or generate_secret_key()
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.auto_error = auto_error
        self.require_https = require_https
        self.cookie_secure = cookie_secure
        self.cookie_httponly = cookie_httponly
        self.cookie_samesite = cookie_samesite
