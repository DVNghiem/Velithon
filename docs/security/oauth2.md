# OAuth2

This guide covers implementing OAuth2 authentication and authorization in Velithon applications.

## OAuth2 Authorization Code Flow

```python
from velithon import Velithon, Request
from velithon.responses import JSONResponse, RedirectResponse, HTMLResponse
from velithon.di import inject, Provide, ServiceContainer
import secrets
import urllib.parse
import httpx
import jwt
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, Any
import base64
import hashlib

@dataclass
class OAuthClient:
    client_id: str
    client_secret: str
    redirect_uris: list
    scopes: list
    name: str
    is_confidential: bool = True

@dataclass
class AuthorizationCode:
    code: str
    client_id: str
    user_id: str
    scopes: list
    redirect_uri: str
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None
    expires_at: datetime = None

@dataclass
class AccessToken:
    token: str
    client_id: str
    user_id: str
    scopes: list
    expires_at: datetime
    refresh_token: Optional[str] = None

class OAuth2Service:
    def __init__(self):
        # Mock storage - replace with database
        self.clients: Dict[str, OAuthClient] = {}
        self.authorization_codes: Dict[str, AuthorizationCode] = {}
        self.access_tokens: Dict[str, AccessToken] = {}
        self.refresh_tokens: Dict[str, str] = {}  # refresh_token -> access_token
        
        # Register demo clients
        self._register_demo_clients()
    
    def _register_demo_clients(self):
        """Register demo OAuth2 clients."""
        # Web application client
        self.clients["webapp_client"] = OAuthClient(
            client_id="webapp_client",
            client_secret="webapp_secret_123",
            redirect_uris=["http://localhost:3000/callback", "http://localhost:8080/callback"],
            scopes=["read", "write", "profile"],
            name="Demo Web App",
            is_confidential=True
        )
        
        # Mobile/SPA client (public client)
        self.clients["mobile_client"] = OAuthClient(
            client_id="mobile_client",
            client_secret="",  # Public client has no secret
            redirect_uris=["com.example.app://callback"],
            scopes=["read", "profile"],
            name="Demo Mobile App",
            is_confidential=False
        )
    
    def generate_authorization_code(self) -> str:
        """Generate authorization code."""
        return secrets.token_urlsafe(32)
    
    def generate_access_token(self) -> str:
        """Generate access token."""
        return secrets.token_urlsafe(48)
    
    def generate_refresh_token(self) -> str:
        """Generate refresh token."""
        return secrets.token_urlsafe(48)
    
    def validate_client(self, client_id: str, client_secret: str = None) -> Optional[OAuthClient]:
        """Validate OAuth2 client."""
        client = self.clients.get(client_id)
        if not client:
            return None
        
        # Public clients don't have secrets
        if not client.is_confidential:
            return client
        
        # Confidential clients must provide valid secret
        if client_secret == client.client_secret:
            return client
        
        return None
    
    def validate_redirect_uri(self, client_id: str, redirect_uri: str) -> bool:
        """Validate redirect URI."""
        client = self.clients.get(client_id)
        if not client:
            return False
        
        return redirect_uri in client.redirect_uris
    
    def create_authorization_code(
        self,
        client_id: str,
        user_id: str,
        scopes: list,
        redirect_uri: str,
        code_challenge: str = None,
        code_challenge_method: str = None
    ) -> str:
        """Create authorization code."""
        code = self.generate_authorization_code()
        
        auth_code = AuthorizationCode(
            code=code,
            client_id=client_id,
            user_id=user_id,
            scopes=scopes,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=datetime.utcnow() + timedelta(minutes=10)  # 10 minutes
        )
        
        self.authorization_codes[code] = auth_code
        return code
    
    def exchange_code_for_token(
        self,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_verifier: str = None
    ) -> Optional[AccessToken]:
        """Exchange authorization code for access token."""
        auth_code = self.authorization_codes.get(code)
        
        if not auth_code:
            return None
        
        # Validate code
        if (auth_code.client_id != client_id or
            auth_code.redirect_uri != redirect_uri or
            auth_code.expires_at < datetime.utcnow()):
            return None
        
        # Validate PKCE if present
        if auth_code.code_challenge:
            if not code_verifier:
                return None
            
            if auth_code.code_challenge_method == "S256":
                verifier_hash = base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode()).digest()
                ).decode().rstrip("=")
                if verifier_hash != auth_code.code_challenge:
                    return None
            elif auth_code.code_challenge_method == "plain":
                if code_verifier != auth_code.code_challenge:
                    return None
        
        # Create access token
        access_token = self.generate_access_token()
        refresh_token = self.generate_refresh_token()
        
        token_data = AccessToken(
            token=access_token,
            client_id=client_id,
            user_id=auth_code.user_id,
            scopes=auth_code.scopes,
            expires_at=datetime.utcnow() + timedelta(hours=1),  # 1 hour
            refresh_token=refresh_token
        )
        
        self.access_tokens[access_token] = token_data
        self.refresh_tokens[refresh_token] = access_token
        
        # Remove used authorization code
        del self.authorization_codes[code]
        
        return token_data
    
    def validate_access_token(self, token: str) -> Optional[AccessToken]:
        """Validate access token."""
        token_data = self.access_tokens.get(token)
        
        if not token_data or token_data.expires_at < datetime.utcnow():
            return None
        
        return token_data
    
    def refresh_access_token(self, refresh_token: str) -> Optional[AccessToken]:
        """Refresh access token."""
        old_access_token = self.refresh_tokens.get(refresh_token)
        if not old_access_token:
            return None
        
        old_token_data = self.access_tokens.get(old_access_token)
        if not old_token_data:
            return None
        
        # Create new access token
        new_access_token = self.generate_access_token()
        new_refresh_token = self.generate_refresh_token()
        
        new_token_data = AccessToken(
            token=new_access_token,
            client_id=old_token_data.client_id,
            user_id=old_token_data.user_id,
            scopes=old_token_data.scopes,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            refresh_token=new_refresh_token
        )
        
        # Update storage
        self.access_tokens[new_access_token] = new_token_data
        self.refresh_tokens[new_refresh_token] = new_access_token
        
        # Remove old tokens
        del self.access_tokens[old_access_token]
        del self.refresh_tokens[refresh_token]
        
        return new_token_data

def require_oauth2_scope(*required_scopes):
    """Decorator to require OAuth2 access token with specific scopes."""
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            auth_header = request.headers.get("Authorization")
            
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    {"error": "access_denied", "error_description": "Access token required"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            token = auth_header.split(" ")[1]
            oauth2_service = ServiceContainer.get(OAuth2Service)
            
            token_data = oauth2_service.validate_access_token(token)
            if not token_data:
                return JSONResponse(
                    {"error": "invalid_token", "error_description": "Invalid or expired access token"},
                    status_code=401
                )
            
            # Check scopes
            if required_scopes:
                for scope in required_scopes:
                    if scope not in token_data.scopes:
                        return JSONResponse(
                            {"error": "insufficient_scope", "error_description": f"Scope '{scope}' required"},
                            status_code=403
                        )
            
            # Add token data to request state
            request.state.oauth2_token = token_data
            request.state.user_id = token_data.user_id
            request.state.client_id = token_data.client_id
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

app = Velithon()

# Register services
ServiceContainer.register(OAuth2Service, OAuth2Service())

# Mock user authentication - replace with real authentication
def authenticate_user(username: str, password: str) -> Optional[str]:
    """Mock user authentication."""
    users = {
        "demo_user": "password123",
        "admin": "admin123"
    }
    
    if users.get(username) == password:
        return username
    
    return None

@app.get("/oauth2/authorize")
async def authorize(request: Request):
    """OAuth2 authorization endpoint."""
    # Parse query parameters
    client_id = request.query_params.get("client_id")
    redirect_uri = request.query_params.get("redirect_uri")
    response_type = request.query_params.get("response_type")
    scope = request.query_params.get("scope", "")
    state = request.query_params.get("state")
    code_challenge = request.query_params.get("code_challenge")
    code_challenge_method = request.query_params.get("code_challenge_method")
    
    # Validate parameters
    if not client_id or not redirect_uri or response_type != "code":
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Missing or invalid parameters"},
            status_code=400
        )
    
    oauth2_service = ServiceContainer.get(OAuth2Service)
    
    # Validate client
    client = oauth2_service.clients.get(client_id)
    if not client:
        return JSONResponse(
            {"error": "invalid_client", "error_description": "Unknown client"},
            status_code=400
        )
    
    # Validate redirect URI
    if not oauth2_service.validate_redirect_uri(client_id, redirect_uri):
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Invalid redirect URI"},
            status_code=400
        )
    
    # Show authorization form
    scopes = scope.split() if scope else []
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>OAuth2 Authorization</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .auth-form {{ max-width: 400px; margin: 0 auto; padding: 20px; border: 1px solid #ccc; border-radius: 10px; }}
            .client-info {{ background: #f0f0f0; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
            .scopes {{ margin: 15px 0; }}
            .scope {{ margin: 5px 0; }}
            button {{ padding: 10px 20px; margin: 5px; }}
            .approve {{ background: #28a745; color: white; border: none; }}
            .deny {{ background: #dc3545; color: white; border: none; }}
        </style>
    </head>
    <body>
        <div class="auth-form">
            <h2>Authorization Request</h2>
            
            <div class="client-info">
                <strong>{client.name}</strong> is requesting access to your account.
            </div>
            
            <div class="scopes">
                <strong>Requested permissions:</strong>
                <ul>
                    {"".join(f"<li>{scope}</li>" for scope in scopes)}
                </ul>
            </div>
            
            <form method="post" action="/oauth2/authorize">
                <input type="hidden" name="client_id" value="{client_id}">
                <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                <input type="hidden" name="response_type" value="{response_type}">
                <input type="hidden" name="scope" value="{scope}">
                <input type="hidden" name="state" value="{state or ''}">
                <input type="hidden" name="code_challenge" value="{code_challenge or ''}">
                <input type="hidden" name="code_challenge_method" value="{code_challenge_method or ''}">
                
                <div>
                    <label>Username:</label>
                    <input type="text" name="username" required>
                </div>
                <div>
                    <label>Password:</label>
                    <input type="password" name="password" required>
                </div>
                
                <div>
                    <button type="submit" name="action" value="approve" class="approve">Approve</button>
                    <button type="submit" name="action" value="deny" class="deny">Deny</button>
                </div>
            </form>
        </div>
    </body>
    </html>
    """)

@app.post("/oauth2/authorize")
async def authorize_post(request: Request):
    """Handle authorization form submission."""
    form = await request.form()
    
    client_id = form.get("client_id")
    redirect_uri = form.get("redirect_uri")
    scope = form.get("scope", "")
    state = form.get("state")
    code_challenge = form.get("code_challenge")
    code_challenge_method = form.get("code_challenge_method")
    action = form.get("action")
    username = form.get("username")
    password = form.get("password")
    
    # Build redirect URL
    redirect_params = {}
    if state:
        redirect_params["state"] = state
    
    if action != "approve":
        # User denied authorization
        redirect_params["error"] = "access_denied"
        redirect_params["error_description"] = "User denied authorization"
    else:
        # Authenticate user
        user_id = authenticate_user(username, password)
        if not user_id:
            redirect_params["error"] = "access_denied"
            redirect_params["error_description"] = "Invalid credentials"
        else:
            # Create authorization code
            oauth2_service = ServiceContainer.get(OAuth2Service)
            scopes = scope.split() if scope else []
            
            code = oauth2_service.create_authorization_code(
                client_id=client_id,
                user_id=user_id,
                scopes=scopes,
                redirect_uri=redirect_uri,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method
            )
            
            redirect_params["code"] = code
    
    # Build redirect URL
    redirect_url = redirect_uri + "?" + urllib.parse.urlencode(redirect_params)
    return RedirectResponse(redirect_url, status_code=302)

@app.post("/oauth2/token")
async def token(request: Request):
    """OAuth2 token endpoint."""
    form = await request.form()
    
    grant_type = form.get("grant_type")
    
    if grant_type == "authorization_code":
        return await handle_authorization_code_grant(form)
    elif grant_type == "refresh_token":
        return await handle_refresh_token_grant(form)
    else:
        return JSONResponse(
            {"error": "unsupported_grant_type", "error_description": "Grant type not supported"},
            status_code=400
        )

async def handle_authorization_code_grant(form):
    """Handle authorization code grant."""
    code = form.get("code")
    client_id = form.get("client_id")
    client_secret = form.get("client_secret")
    redirect_uri = form.get("redirect_uri")
    code_verifier = form.get("code_verifier")
    
    if not code or not client_id or not redirect_uri:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Missing required parameters"},
            status_code=400
        )
    
    oauth2_service = ServiceContainer.get(OAuth2Service)
    
    # Validate client
    client = oauth2_service.validate_client(client_id, client_secret)
    if not client:
        return JSONResponse(
            {"error": "invalid_client", "error_description": "Client authentication failed"},
            status_code=401
        )
    
    # Exchange code for token
    token_data = oauth2_service.exchange_code_for_token(
        code=code,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier
    )
    
    if not token_data:
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "Invalid authorization code"},
            status_code=400
        )
    
    response_data = {
        "access_token": token_data.token,
        "token_type": "Bearer",
        "expires_in": int((token_data.expires_at - datetime.utcnow()).total_seconds()),
        "scope": " ".join(token_data.scopes)
    }
    
    if token_data.refresh_token:
        response_data["refresh_token"] = token_data.refresh_token
    
    return JSONResponse(response_data)

async def handle_refresh_token_grant(form):
    """Handle refresh token grant."""
    refresh_token = form.get("refresh_token")
    client_id = form.get("client_id")
    client_secret = form.get("client_secret")
    
    if not refresh_token or not client_id:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Missing required parameters"},
            status_code=400
        )
    
    oauth2_service = ServiceContainer.get(OAuth2Service)
    
    # Validate client
    client = oauth2_service.validate_client(client_id, client_secret)
    if not client:
        return JSONResponse(
            {"error": "invalid_client", "error_description": "Client authentication failed"},
            status_code=401
        )
    
    # Refresh token
    token_data = oauth2_service.refresh_access_token(refresh_token)
    if not token_data:
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "Invalid refresh token"},
            status_code=400
        )
    
    response_data = {
        "access_token": token_data.token,
        "token_type": "Bearer",
        "expires_in": int((token_data.expires_at - datetime.utcnow()).total_seconds()),
        "scope": " ".join(token_data.scopes),
        "refresh_token": token_data.refresh_token
    }
    
    return JSONResponse(response_data)

# Protected resource endpoints

@app.get("/api/profile")
@require_oauth2_scope("profile")
async def get_profile(request: Request):
    """Get user profile - requires 'profile' scope."""
    token_data = request.state.oauth2_token
    
    # Mock user data - replace with real user service
    user_data = {
        "user_id": token_data.user_id,
        "username": token_data.user_id,
        "email": f"{token_data.user_id}@example.com",
        "name": f"User {token_data.user_id.title()}"
    }
    
    return JSONResponse(user_data)

@app.get("/api/data")
@require_oauth2_scope("read")
async def get_data(request: Request):
    """Get user data - requires 'read' scope."""
    token_data = request.state.oauth2_token
    
    return JSONResponse({
        "data": [
            {"id": 1, "value": "Item 1"},
            {"id": 2, "value": "Item 2"},
            {"id": 3, "value": "Item 3"}
        ],
        "user_id": token_data.user_id,
        "client_id": token_data.client_id
    })

@app.post("/api/data")
@require_oauth2_scope("write")
async def create_data(request: Request):
    """Create data - requires 'write' scope."""
    data = await request.json()
    token_data = request.state.oauth2_token
    
    return JSONResponse({
        "message": "Data created successfully",
        "data": data,
        "created_by": token_data.user_id,
        "client_id": token_data.client_id
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## OAuth2 Client Example

```python
import httpx
import urllib.parse
import secrets
import base64
import hashlib
from typing import Dict, Any

class OAuth2Client:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        authorization_url: str,
        token_url: str,
        redirect_uri: str
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorization_url = authorization_url
        self.token_url = token_url
        self.redirect_uri = redirect_uri
    
    def generate_pkce_challenge(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge."""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")
        
        return code_verifier, code_challenge
    
    def get_authorization_url(
        self,
        scopes: list = None,
        state: str = None,
        use_pkce: bool = True
    ) -> tuple[str, Dict[str, str]]:
        """Get authorization URL and return state information."""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }
        
        if scopes:
            params["scope"] = " ".join(scopes)
        
        if state:
            params["state"] = state
        
        state_info = {}
        
        if use_pkce:
            code_verifier, code_challenge = self.generate_pkce_challenge()
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
            state_info["code_verifier"] = code_verifier
        
        url = self.authorization_url + "?" + urllib.parse.urlencode(params)
        return url, state_info
    
    async def exchange_code_for_token(
        self,
        code: str,
        state_info: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri
        }
        
        if state_info and "code_verifier" in state_info:
            data["code_verifier"] = state_info["code_verifier"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Token exchange failed: {response.text}")
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token."""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Token refresh failed: {response.text}")

# Usage example
async def oauth2_client_example():
    """Example OAuth2 client usage."""
    client = OAuth2Client(
        client_id="webapp_client",
        client_secret="webapp_secret_123",
        authorization_url="http://localhost:8000/oauth2/authorize",
        token_url="http://localhost:8000/oauth2/token",
        redirect_uri="http://localhost:3000/callback"
    )
    
    # Step 1: Get authorization URL
    auth_url, state_info = client.get_authorization_url(
        scopes=["read", "write", "profile"],
        state="random_state_value"
    )
    
    print(f"Visit this URL to authorize: {auth_url}")
    
    # Step 2: After user authorizes, you get a code in the callback
    # This would typically come from your web framework's callback handler
    authorization_code = "received_authorization_code"
    
    # Step 3: Exchange code for token
    try:
        token_response = await client.exchange_code_for_token(
            code=authorization_code,
            state_info=state_info
        )
        
        access_token = token_response["access_token"]
        refresh_token = token_response.get("refresh_token")
        
        print(f"Access token: {access_token}")
        
        # Step 4: Use access token to make API calls
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                "http://localhost:8000/api/profile",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"User data: {user_data}")
            
        # Step 5: Refresh token when needed
        if refresh_token:
            new_token_response = await client.refresh_token(refresh_token)
            new_access_token = new_token_response["access_token"]
            print(f"New access token: {new_access_token}")
            
    except Exception as e:
        print(f"OAuth2 flow failed: {e}")
```

## Testing OAuth2 Implementation

```python
import pytest
import httpx
from urllib.parse import parse_qs, urlparse

@pytest.mark.asyncio
async def test_oauth2_authorization_endpoint():
    """Test OAuth2 authorization endpoint."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/oauth2/authorize", params={
            "client_id": "webapp_client",
            "redirect_uri": "http://localhost:3000/callback",
            "response_type": "code",
            "scope": "read write",
            "state": "test_state"
        })
        
        assert response.status_code == 200
        assert "Authorization Request" in response.text
        assert "webapp_client" in response.text

@pytest.mark.asyncio
async def test_oauth2_authorization_flow():
    """Test complete OAuth2 authorization flow."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Step 1: POST to authorization endpoint
        response = await client.post("/oauth2/authorize", data={
            "client_id": "webapp_client",
            "redirect_uri": "http://localhost:3000/callback",
            "response_type": "code",
            "scope": "read write",
            "state": "test_state",
            "username": "demo_user",
            "password": "password123",
            "action": "approve"
        })
        
        # Should redirect with authorization code
        assert response.status_code == 302
        
        # Parse redirect URL
        redirect_url = response.headers["location"]
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        
        assert "code" in query_params
        assert query_params["state"][0] == "test_state"
        
        authorization_code = query_params["code"][0]
        
        # Step 2: Exchange code for token
        token_response = await client.post("/oauth2/token", data={
            "grant_type": "authorization_code",
            "code": authorization_code,
            "client_id": "webapp_client",
            "client_secret": "webapp_secret_123",
            "redirect_uri": "http://localhost:3000/callback"
        })
        
        assert token_response.status_code == 200
        token_data = token_response.json()
        
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "Bearer"
        
        access_token = token_data["access_token"]
        
        # Step 3: Use access token
        api_response = await client.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert api_response.status_code == 200
        profile_data = api_response.json()
        assert profile_data["user_id"] == "demo_user"

@pytest.mark.asyncio
async def test_oauth2_refresh_token():
    """Test OAuth2 refresh token flow."""
    oauth2_service = OAuth2Service()
    
    # Create a token directly for testing
    token_data = AccessToken(
        token="test_access_token",
        client_id="webapp_client",
        user_id="demo_user",
        scopes=["read", "write"],
        expires_at=datetime.utcnow() + timedelta(hours=1),
        refresh_token="test_refresh_token"
    )
    
    oauth2_service.access_tokens["test_access_token"] = token_data
    oauth2_service.refresh_tokens["test_refresh_token"] = "test_access_token"
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/oauth2/token", data={
            "grant_type": "refresh_token",
            "refresh_token": "test_refresh_token",
            "client_id": "webapp_client",
            "client_secret": "webapp_secret_123"
        })
        
        assert response.status_code == 200
        new_token_data = response.json()
        
        assert "access_token" in new_token_data
        assert "refresh_token" in new_token_data
        assert new_token_data["access_token"] != "test_access_token"

@pytest.mark.asyncio
async def test_oauth2_scope_enforcement():
    """Test OAuth2 scope enforcement."""
    oauth2_service = OAuth2Service()
    
    # Create token with limited scopes
    token_data = AccessToken(
        token="limited_token",
        client_id="webapp_client",
        user_id="demo_user",
        scopes=["read"],  # Only read scope
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    oauth2_service.access_tokens["limited_token"] = token_data
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Can access read endpoint
        response = await client.get(
            "/api/data",
            headers={"Authorization": "Bearer limited_token"}
        )
        assert response.status_code == 200
        
        # Cannot access write endpoint
        response = await client.post(
            "/api/data",
            json={"test": "data"},
            headers={"Authorization": "Bearer limited_token"}
        )
        assert response.status_code == 403
        assert "insufficient_scope" in response.json()["error"]

@pytest.mark.asyncio
async def test_oauth2_invalid_client():
    """Test OAuth2 with invalid client credentials."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/oauth2/token", data={
            "grant_type": "authorization_code",
            "code": "test_code",
            "client_id": "invalid_client",
            "client_secret": "invalid_secret",
            "redirect_uri": "http://localhost:3000/callback"
        })
        
        assert response.status_code == 401
        assert "invalid_client" in response.json()["error"]

@pytest.mark.asyncio
async def test_oauth2_pkce_flow():
    """Test OAuth2 PKCE (Proof Key for Code Exchange) flow."""
    import base64
    import hashlib
    import secrets
    
    # Generate PKCE parameters
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Authorization with PKCE
        response = await client.post("/oauth2/authorize", data={
            "client_id": "mobile_client",  # Public client
            "redirect_uri": "com.example.app://callback",
            "response_type": "code",
            "scope": "read",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "username": "demo_user",
            "password": "password123",
            "action": "approve"
        })
        
        assert response.status_code == 302
        
        # Extract authorization code
        redirect_url = response.headers["location"]
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        authorization_code = query_params["code"][0]
        
        # Exchange code with PKCE
        token_response = await client.post("/oauth2/token", data={
            "grant_type": "authorization_code",
            "code": authorization_code,
            "client_id": "mobile_client",
            # No client_secret for public client
            "redirect_uri": "com.example.app://callback",
            "code_verifier": code_verifier
        })
        
        assert token_response.status_code == 200
        token_data = token_response.json()
        assert "access_token" in token_data
```

## Best Practices

1. **Use HTTPS**: Always use HTTPS in production
2. **Short-lived Tokens**: Keep access tokens short-lived (1 hour or less)
3. **Secure Storage**: Store client secrets and tokens securely
4. **PKCE for Public Clients**: Always use PKCE for mobile/SPA clients
5. **Scope Limitation**: Use minimal required scopes
6. **State Parameter**: Always use state parameter to prevent CSRF
7. **Token Revocation**: Implement token revocation endpoints
8. **Audit Logging**: Log all OAuth2 operations
9. **Rate Limiting**: Implement rate limiting on OAuth2 endpoints
10. **Client Validation**: Thoroughly validate client registrations
