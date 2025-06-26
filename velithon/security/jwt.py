"""JWT token handling for Velithon authentication system."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    import jwt
    from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    jwt = None
    InvalidTokenError = Exception
    ExpiredSignatureError = Exception

from .exceptions import (
    InvalidTokenError as VelithonInvalidTokenError,
    TokenExpiredError,
)
from .models import TokenData
from .utils import SecurityConfig


class JWTHandler:
    """JWT token handler for authentication."""
    
    def __init__(
        self,
        config: SecurityConfig | None = None,
        secret_key: str | None = None,
        algorithm: str = "HS256",
        access_token_expire: timedelta | None = None
    ):
        """Initialize JWT handler with configuration.
        
        Args:
            config: Security configuration object
            secret_key: JWT secret key (alternative to config)
            algorithm: JWT algorithm (alternative to config)
            access_token_expire: Token expiration time (alternative to config)
        """
        if config is None and secret_key is not None:
            # Create config from parameters for convenience
            expire_minutes = 30
            if access_token_expire:
                expire_minutes = int(access_token_expire.total_seconds() / 60)
            config = SecurityConfig(
                secret_key=secret_key,
                algorithm=algorithm,
                access_token_expire_minutes=expire_minutes
            )
        
        self.config = config or SecurityConfig()
        if not JWT_AVAILABLE:
            raise ImportError(
                "PyJWT is required for JWT functionality. "
                "Install it with: pip install PyJWT"
            )
    
    def create_access_token(
        self,
        data: dict[str, Any],
        expires_delta: timedelta | None = None
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.config.access_token_expire_minutes
            )
        
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
        
        return jwt.encode(
            to_encode,
            self.config.secret_key,
            algorithm=self.config.algorithm
        )
    
    def encode_token(
        self,
        data: dict[str, Any],
        expires_delta: timedelta | None = None
    ) -> str:
        """Encode token (alias for create_access_token)."""
        return self.create_access_token(data, expires_delta)
    
    def create_refresh_token(
        self,
        data: dict[str, Any],
        expires_delta: timedelta | None = None
    ) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        to_encode.update({"type": "refresh"})
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                days=self.config.refresh_token_expire_days
            )
        
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
        
        return jwt.encode(
            to_encode,
            self.config.secret_key,
            algorithm=self.config.algorithm
        )
    
    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and verify a JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm]
            )
            return payload
        except ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except InvalidTokenError:
            raise VelithonInvalidTokenError("Invalid token")
    
    def extract_token_data(self, token: str) -> TokenData:
        """Extract token data from JWT token."""
        payload = self.decode_token(token)
        
        username = payload.get("sub")
        user_id = payload.get("user_id")
        scopes = payload.get("scopes", [])
        expires_at = None
        
        if "exp" in payload:
            expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        
        return TokenData(
            username=username,
            user_id=user_id,
            scopes=scopes,
            expires_at=expires_at
        )
    
    def is_token_valid(self, token: str) -> bool:
        """Check if a token is valid without raising exceptions."""
        try:
            self.decode_token(token)
            return True
        except (TokenExpiredError, VelithonInvalidTokenError):
            return False


# Global JWT handler instance
_jwt_handler: JWTHandler | None = None


def get_jwt_handler() -> JWTHandler:
    """Get or create the global JWT handler."""
    global _jwt_handler
    if _jwt_handler is None:
        _jwt_handler = JWTHandler()
    return _jwt_handler


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None
) -> str:
    """Create a JWT access token using the global handler."""
    return get_jwt_handler().create_access_token(data, expires_delta)


def decode_access_token(token: str) -> TokenData:
    """Decode a JWT access token using the global handler."""
    return get_jwt_handler().extract_token_data(token)


def verify_token(token: str) -> bool:
    """Verify a JWT token using the global handler."""
    return get_jwt_handler().is_token_valid(token)


def set_jwt_config(config: SecurityConfig) -> None:
    """Set the global JWT configuration."""
    global _jwt_handler
    _jwt_handler = JWTHandler(config)


# Fallback implementation when PyJWT is not available
if not JWT_AVAILABLE:
    
    def create_access_token(
        data: dict[str, Any],
        expires_delta: timedelta | None = None
    ) -> str:
        """Fallback token creation without JWT."""
        import base64
        import time
        
        expire_time = time.time() + (expires_delta.total_seconds() if expires_delta
                                   else 1800)  # 30 minutes default
        
        token_data = {
            "data": data,
            "exp": expire_time,
            "iat": time.time()
        }
        
        return base64.urlsafe_b64encode(
            json.dumps(token_data).encode()
        ).decode()
    
    def decode_access_token(token: str) -> TokenData:
        """Fallback token decoding without JWT."""
        import base64
        import time
        
        try:
            decoded = base64.urlsafe_b64decode(token.encode())
            token_data = json.loads(decoded.decode())
            
            if time.time() > token_data["exp"]:
                raise TokenExpiredError("Token has expired")
            
            data = token_data["data"]
            return TokenData(
                username=data.get("sub"),
                user_id=data.get("user_id"),
                scopes=data.get("scopes", [])
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            raise VelithonInvalidTokenError("Invalid token")
    
    def verify_token(token: str) -> bool:
        """Fallback token verification without JWT."""
        try:
            decode_access_token(token)
            return True
        except (TokenExpiredError, VelithonInvalidTokenError):
            return False
