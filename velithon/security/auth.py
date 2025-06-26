"""Authentication schemes for Velithon security system.

Inspired by FastAPI's excellent security design but adapted for Velithon's
architecture with enhanced features and better integration.
"""

import base64
from typing import Any

from velithon.datastructures import Scope
from velithon.requests import Request

from .exceptions import AuthenticationError, MissingTokenError
from .models import Token, User


class SecurityBase:
    """Base class for all security schemes."""
    
    def __init__(self, auto_error: bool = True):
        """Initialize security base."""
        self.auto_error = auto_error
    
    async def __call__(self, request: Request) -> str | None:
        """Extract security credentials from request."""
        raise NotImplementedError()
    
    def get_openapi_security_definition(self) -> dict[str, Any]:
        """Get OpenAPI security scheme definition."""
        raise NotImplementedError()


class HTTPBasic(SecurityBase):
    """HTTP Basic authentication scheme."""
    
    def __init__(
        self,
        realm: str = "Velithon API",
        auto_error: bool = True
    ):
        """Initialize HTTP Basic authentication."""
        super().__init__(auto_error)
        self.realm = realm
    
    async def __call__(self, request: Request) -> str | None:
        """Extract Basic authentication credentials."""
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            if self.auto_error:
                raise MissingTokenError("Missing Authorization header")
            return None
        
        try:
            scheme, credentials = authorization.split(" ", 1)
            if scheme.lower() != "basic":
                if self.auto_error:
                    raise AuthenticationError("Invalid authentication scheme")
                return None
            
            # Decode base64 credentials
            decoded = base64.b64decode(credentials).decode("utf-8")
            username, password = decoded.split(":", 1)
            return f"{username}:{password}"
            
        except (ValueError, UnicodeDecodeError):
            if self.auto_error:
                raise AuthenticationError("Invalid Basic authentication format")
            return None
    
    def get_openapi_security_definition(self) -> dict[str, Any]:
        """Get OpenAPI security scheme definition."""
        return {
            "type": "http",
            "scheme": "basic",
            "description": f"HTTP Basic authentication. Realm: {self.realm}"
        }


class HTTPBearer(SecurityBase):
    """HTTP Bearer token authentication scheme."""
    
    def __init__(
        self,
        bearer_format: str = "JWT",
        auto_error: bool = True
    ):
        """Initialize HTTP Bearer authentication."""
        super().__init__(auto_error)
        self.bearer_format = bearer_format
    
    async def __call__(self, request: Request) -> str | None:
        """Extract Bearer token from request."""
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            if self.auto_error:
                raise MissingTokenError("Missing Authorization header")
            return None
        
        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                if self.auto_error:
                    raise AuthenticationError("Invalid authentication scheme")
                return None
            
            return token
            
        except ValueError:
            if self.auto_error:
                raise AuthenticationError("Invalid Bearer token format")
            return None
    
    def get_openapi_security_definition(self) -> dict[str, Any]:
        """Get OpenAPI security scheme definition."""
        definition = {
            "type": "http",
            "scheme": "bearer",
            "description": "HTTP Bearer token authentication"
        }
        if self.bearer_format:
            definition["bearerFormat"] = self.bearer_format
        return definition


class APIKeyHeader(SecurityBase):
    """API Key authentication via header."""
    
    def __init__(
        self,
        name: str = "X-API-Key",
        auto_error: bool = True
    ):
        """Initialize API Key header authentication."""
        super().__init__(auto_error)
        self.name = name
    
    async def __call__(self, request: Request) -> str | None:
        """Extract API key from header."""
        api_key = request.headers.get(self.name)
        
        if not api_key:
            if self.auto_error:
                raise MissingTokenError(f"Missing {self.name} header")
            return None
        
        return api_key
    
    def get_openapi_security_definition(self) -> dict[str, Any]:
        """Get OpenAPI security scheme definition."""
        return {
            "type": "apiKey",
            "in": "header",
            "name": self.name,
            "description": f"API key authentication via {self.name} header"
        }


class APIKeyQuery(SecurityBase):
    """API Key authentication via query parameter."""
    
    def __init__(
        self,
        name: str = "api_key",
        auto_error: bool = True
    ):
        """Initialize API Key query authentication."""
        super().__init__(auto_error)
        self.name = name
    
    async def __call__(self, request: Request) -> str | None:
        """Extract API key from query parameters."""
        api_key = request.query_params.get(self.name)
        
        if not api_key:
            if self.auto_error:
                raise MissingTokenError(f"Missing {self.name} query parameter")
            return None
        
        return api_key
    
    def get_openapi_security_definition(self) -> dict[str, Any]:
        """Get OpenAPI security scheme definition."""
        return {
            "type": "apiKey",
            "in": "query",
            "name": self.name,
            "description": f"API key authentication via {self.name} query parameter"
        }


class APIKeyCookie(SecurityBase):
    """API Key authentication via cookie."""
    
    def __init__(
        self,
        name: str = "api_key",
        auto_error: bool = True
    ):
        """Initialize API Key cookie authentication."""
        super().__init__(auto_error)
        self.name = name
    
    async def __call__(self, request: Request) -> str | None:
        """Extract API key from cookies."""
        api_key = request.cookies.get(self.name)
        
        if not api_key:
            if self.auto_error:
                raise MissingTokenError(f"Missing {self.name} cookie")
            return None
        
        return api_key
    
    def get_openapi_security_definition(self) -> dict[str, Any]:
        """Get OpenAPI security scheme definition."""
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": self.name,
            "description": f"API key authentication via {self.name} cookie"
        }


class OAuth2PasswordBearer(HTTPBearer):
    """OAuth2 password bearer token authentication."""
    
    def __init__(
        self,
        token_url: str,
        scopes: dict[str, str] | None = None,
        auto_error: bool = True
    ):
        """Initialize OAuth2 password bearer authentication."""
        super().__init__(bearer_format="JWT", auto_error=auto_error)
        self.token_url = token_url
        self.scopes = scopes or {}
    
    def get_openapi_security_definition(self) -> dict[str, Any]:
        """Get OpenAPI security scheme definition."""
        definition = {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": self.token_url,
                    "scopes": self.scopes
                }
            },
            "description": "OAuth2 password flow with Bearer token"
        }
        return definition


class OAuth2AuthorizationCodeBearer(HTTPBearer):
    """OAuth2 authorization code bearer token authentication."""
    
    def __init__(
        self,
        authorization_url: str,
        token_url: str,
        scopes: dict[str, str] | None = None,
        auto_error: bool = True
    ):
        """Initialize OAuth2 authorization code bearer authentication."""
        super().__init__(bearer_format="JWT", auto_error=auto_error)
        self.authorization_url = authorization_url
        self.token_url = token_url
        self.scopes = scopes or {}
    
    def get_openapi_security_definition(self) -> dict[str, Any]:
        """Get OpenAPI security scheme definition."""
        return {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": self.authorization_url,
                    "tokenUrl": self.token_url,
                    "scopes": self.scopes
                }
            },
            "description": "OAuth2 authorization code flow with Bearer token"
        }


# Convenient aliases following FastAPI conventions
BearerAuth = HTTPBearer
BasicAuth = HTTPBasic
APIKeyAuth = APIKeyHeader


class OAuth2PasswordRequestForm:
    """OAuth2 password request form data."""
    
    def __init__(
        self,
        username: str,
        password: str,
        scope: str = "",
        client_id: str | None = None,
        client_secret: str | None = None
    ):
        """Initialize OAuth2 password request form."""
        self.username = username
        self.password = password
        self.scopes = scope.split() if scope else []
        self.client_id = client_id
        self.client_secret = client_secret


def Security(scheme: SecurityBase, scopes: list[str] | None = None):
    """Security dependency factory similar to FastAPI's Security."""
    
    async def security_dependency(request: Request) -> str | None:
        """Security dependency implementation."""
        credentials = await scheme(request)
        
        # TODO: Implement scope validation when user context is available
        if scopes and credentials:
            # This would be validated against user's actual scopes
            pass
        
        return credentials
    
    # Attach security scheme for OpenAPI generation
    security_dependency.security_scheme = scheme
    security_dependency.scopes = scopes or []
    
    return security_dependency
