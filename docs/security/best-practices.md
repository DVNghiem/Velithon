# Security Best Practices

This guide covers security best practices for developing secure Velithon applications.

## General Security Principles

### Defense in Depth

Implement multiple layers of security controls:

```python
from velithon import Velithon, Request
from velithon.responses import JSONResponse
from velithon.di import ServiceContainer
import logging
import hashlib
import secrets
from datetime import datetime, timedelta

# Configure security logging
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)

class SecurityLogger:
    @staticmethod
    def log_security_event(event_type: str, user_id: str = None, ip_address: str = None, details: dict = None):
        """Log security events for monitoring and auditing."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details or {}
        }
        security_logger.info(f"Security Event: {log_data}")

# Example of layered security
app = Velithon()

@app.middleware("http")
async def security_logging_middleware(request: Request, call_next):
    """Log security-relevant requests."""
    start_time = datetime.utcnow()
    
    # Log request
    SecurityLogger.log_security_event(
        "request",
        ip_address=request.client.host if request.client else "unknown",
        details={
            "method": request.method,
            "path": request.url.path,
            "user_agent": request.headers.get("User-Agent", "")
        }
    )
    
    response = await call_next(request)
    
    # Log response
    SecurityLogger.log_security_event(
        "response",
        ip_address=request.client.host if request.client else "unknown",
        details={
            "status_code": response.status_code,
            "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
        }
    )
    
    return response
```

### Input Validation and Sanitization

Always validate and sanitize user input:

```python
import re
from typing import Any, Optional
from html import escape

class InputValidator:
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format."""
        # Only alphanumeric and underscore, 3-30 characters
        pattern = r'^[a-zA-Z0-9_]{3,30}$'
        return bool(re.match(pattern, username))
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, list]:
        """Validate password strength."""
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Sanitize HTML input to prevent XSS."""
        return escape(text)
    
    @staticmethod
    def validate_integer(value: Any, min_val: int = None, max_val: int = None) -> Optional[int]:
        """Validate and convert integer input."""
        try:
            int_val = int(value)
            if min_val is not None and int_val < min_val:
                return None
            if max_val is not None and int_val > max_val:
                return None
            return int_val
        except (ValueError, TypeError):
            return None

@app.post("/register")
async def register_user(request: Request):
    """User registration with input validation."""
    data = await request.json()
    
    # Validate required fields
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not username or not email or not password:
        SecurityLogger.log_security_event(
            "invalid_registration_attempt",
            ip_address=request.client.host if request.client else "unknown",
            details={"reason": "missing_fields"}
        )
        return JSONResponse(
            {"error": "Username, email, and password are required"},
            status_code=400
        )
    
    # Validate input formats
    if not InputValidator.validate_username(username):
        return JSONResponse(
            {"error": "Username must be 3-30 characters, alphanumeric and underscore only"},
            status_code=400
        )
    
    if not InputValidator.validate_email(email):
        return JSONResponse(
            {"error": "Invalid email format"},
            status_code=400
        )
    
    # Validate password strength
    is_strong, password_errors = InputValidator.validate_password_strength(password)
    if not is_strong:
        return JSONResponse(
            {"error": "Password requirements not met", "details": password_errors},
            status_code=400
        )
    
    # Sanitize inputs
    username = InputValidator.sanitize_html(username)
    
    SecurityLogger.log_security_event(
        "user_registration_attempt",
        details={"username": username, "email": email}
    )
    
    return JSONResponse({
        "message": "User registered successfully",
        "username": username
    })
```

## Authentication Security

### Secure Password Handling

```python
import bcrypt
import secrets
from datetime import datetime, timedelta

class PasswordManager:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

class AccountSecurity:
    def __init__(self):
        self.failed_attempts = {}  # ip -> (count, last_attempt)
        self.locked_accounts = {}  # username -> unlock_time
        self.max_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        self.attempt_window = timedelta(minutes=5)
    
    def is_account_locked(self, username: str) -> bool:
        """Check if account is locked."""
        if username in self.locked_accounts:
            unlock_time = self.locked_accounts[username]
            if datetime.utcnow() < unlock_time:
                return True
            else:
                # Lock expired, remove it
                del self.locked_accounts[username]
        return False
    
    def record_failed_attempt(self, username: str, ip_address: str):
        """Record failed login attempt."""
        now = datetime.utcnow()
        
        # Clean old attempts
        if ip_address in self.failed_attempts:
            count, last_attempt = self.failed_attempts[ip_address]
            if now - last_attempt > self.attempt_window:
                count = 0
        else:
            count = 0
        
        count += 1
        self.failed_attempts[ip_address] = (count, now)
        
        # Lock account if too many attempts
        if count >= self.max_attempts:
            self.locked_accounts[username] = now + self.lockout_duration
            SecurityLogger.log_security_event(
                "account_locked",
                user_id=username,
                ip_address=ip_address,
                details={"failed_attempts": count}
            )
    
    def clear_failed_attempts(self, ip_address: str):
        """Clear failed attempts on successful login."""
        self.failed_attempts.pop(ip_address, None)

account_security = AccountSecurity()

@app.post("/login")
async def login(request: Request):
    """Secure login endpoint."""
    data = await request.json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    ip_address = request.client.host if request.client else "unknown"
    
    if not username or not password:
        return JSONResponse(
            {"error": "Username and password are required"},
            status_code=400
        )
    
    # Check if account is locked
    if account_security.is_account_locked(username):
        SecurityLogger.log_security_event(
            "login_attempt_locked_account",
            user_id=username,
            ip_address=ip_address
        )
        return JSONResponse(
            {"error": "Account is temporarily locked. Please try again later."},
            status_code=423
        )
    
    # Mock user lookup - replace with real database
    users = {
        "demo_user": {
            "password_hash": PasswordManager.hash_password("secure_password123"),
            "is_active": True
        }
    }
    
    user = users.get(username)
    
    if not user or not PasswordManager.verify_password(password, user["password_hash"]):
        account_security.record_failed_attempt(username, ip_address)
        SecurityLogger.log_security_event(
            "failed_login_attempt",
            user_id=username,
            ip_address=ip_address
        )
        return JSONResponse(
            {"error": "Invalid credentials"},
            status_code=401
        )
    
    if not user["is_active"]:
        SecurityLogger.log_security_event(
            "login_attempt_inactive_account",
            user_id=username,
            ip_address=ip_address
        )
        return JSONResponse(
            {"error": "Account is deactivated"},
            status_code=403
        )
    
    # Successful login
    account_security.clear_failed_attempts(ip_address)
    SecurityLogger.log_security_event(
        "successful_login",
        user_id=username,
        ip_address=ip_address
    )
    
    # Generate secure session token
    session_token = secrets.token_urlsafe(32)
    
    return JSONResponse({
        "message": "Login successful",
        "session_token": session_token
    })
```

## Data Protection

### Encryption and Hashing

```python
from cryptography.fernet import Fernet
import base64
import os

class DataProtection:
    def __init__(self, encryption_key: bytes = None):
        if encryption_key is None:
            encryption_key = os.environ.get("ENCRYPTION_KEY", "").encode()
            if not encryption_key:
                # Generate a new key (store this securely!)
                encryption_key = Fernet.generate_key()
        
        self.cipher = Fernet(encryption_key)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        encrypted = self.cipher.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted = self.cipher.decrypt(encrypted_bytes)
        return decrypted.decode()
    
    @staticmethod
    def hash_pii(data: str) -> str:
        """Hash PII for indexing without storing plaintext."""
        return hashlib.sha256(data.encode()).hexdigest()

data_protection = DataProtection()

@app.post("/store-sensitive-data")
async def store_sensitive_data(request: Request):
    """Store sensitive data with encryption."""
    data = await request.json()
    
    sensitive_info = data.get("sensitive_info", "")
    if not sensitive_info:
        return JSONResponse(
            {"error": "Sensitive information is required"},
            status_code=400
        )
    
    # Encrypt sensitive data
    encrypted_data = data_protection.encrypt_sensitive_data(sensitive_info)
    
    # Hash for indexing (if needed)
    data_hash = DataProtection.hash_pii(sensitive_info)
    
    # Store in database (mock)
    stored_record = {
        "id": secrets.token_hex(16),
        "encrypted_data": encrypted_data,
        "data_hash": data_hash,
        "created_at": datetime.utcnow().isoformat()
    }
    
    SecurityLogger.log_security_event(
        "sensitive_data_stored",
        details={"record_id": stored_record["id"]}
    )
    
    return JSONResponse({
        "message": "Sensitive data stored securely",
        "record_id": stored_record["id"]
    })
```

## API Security

### Secure API Design

```python
import jwt
from functools import wraps

class APISecurityService:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.api_keys = {}  # In production, use database
        self.rate_limits = {}
    
    def create_api_key(self, user_id: str, scopes: list) -> str:
        """Create API key with specific scopes."""
        api_key = secrets.token_urlsafe(32)
        self.api_keys[api_key] = {
            "user_id": user_id,
            "scopes": scopes,
            "created_at": datetime.utcnow(),
            "last_used": None,
            "is_active": True
        }
        return api_key
    
    def validate_api_key(self, api_key: str) -> dict:
        """Validate API key and return metadata."""
        key_data = self.api_keys.get(api_key)
        if key_data and key_data["is_active"]:
            key_data["last_used"] = datetime.utcnow()
            return key_data
        return None

def require_api_key_with_scope(required_scope: str):
    """Decorator requiring API key with specific scope."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                return JSONResponse(
                    {"error": "API key required"},
                    status_code=401
                )
            
            api_service = ServiceContainer.get(APISecurityService)
            key_data = api_service.validate_api_key(api_key)
            
            if not key_data:
                SecurityLogger.log_security_event(
                    "invalid_api_key_attempt",
                    ip_address=request.client.host if request.client else "unknown",
                    details={"api_key_prefix": api_key[:8] + "..."}
                )
                return JSONResponse(
                    {"error": "Invalid API key"},
                    status_code=401
                )
            
            if required_scope not in key_data["scopes"]:
                SecurityLogger.log_security_event(
                    "insufficient_api_scope",
                    user_id=key_data["user_id"],
                    ip_address=request.client.host if request.client else "unknown",
                    details={"required_scope": required_scope, "available_scopes": key_data["scopes"]}
                )
                return JSONResponse(
                    {"error": f"Scope '{required_scope}' required"},
                    status_code=403
                )
            
            request.state.api_user_id = key_data["user_id"]
            request.state.api_scopes = key_data["scopes"]
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Register API security service
ServiceContainer.register(APISecurityService, APISecurityService("your-secret-key"))

@app.get("/api/secure-data")
@require_api_key_with_scope("read:data")
async def get_secure_data(request: Request):
    """Secure API endpoint requiring specific scope."""
    return JSONResponse({
        "data": "This is secure data",
        "accessed_by": request.state.api_user_id,
        "scopes": request.state.api_scopes
    })
```

## File Upload Security

```python
import mimetypes
import os
from pathlib import Path

class FileUploadSecurity:
    def __init__(self):
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.txt', '.docx'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.upload_path = Path("uploads")
        self.upload_path.mkdir(exist_ok=True)
    
    def validate_file(self, filename: str, content: bytes) -> tuple[bool, str]:
        """Validate uploaded file."""
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            return False, f"File type not allowed: {file_ext}"
        
        # Check file size
        if len(content) > self.max_file_size:
            return False, f"File too large: {len(content)} bytes"
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            allowed_mimes = {
                'image/jpeg', 'image/png', 'image/gif',
                'application/pdf', 'text/plain',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            }
            if mime_type not in allowed_mimes:
                return False, f"MIME type not allowed: {mime_type}"
        
        # Basic content validation
        if file_ext in {'.jpg', '.jpeg', '.png', '.gif'}:
            # Simple image header check
            if not self._is_valid_image(content, file_ext):
                return False, "Invalid image file"
        
        return True, "File is valid"
    
    def _is_valid_image(self, content: bytes, file_ext: str) -> bool:
        """Basic image validation."""
        if file_ext in {'.jpg', '.jpeg'}:
            return content.startswith(b'\xff\xd8\xff')
        elif file_ext == '.png':
            return content.startswith(b'\x89PNG\r\n\x1a\n')
        elif file_ext == '.gif':
            return content.startswith(b'GIF87a') or content.startswith(b'GIF89a')
        return True
    
    def generate_safe_filename(self, original_filename: str) -> str:
        """Generate safe filename to prevent directory traversal."""
        # Remove path components
        safe_name = os.path.basename(original_filename)
        
        # Remove potentially dangerous characters
        safe_name = re.sub(r'[^\w\-_\.]', '', safe_name)
        
        # Add timestamp to prevent conflicts
        name_parts = safe_name.rsplit('.', 1)
        if len(name_parts) == 2:
            name, ext = name_parts
            safe_name = f"{name}_{int(datetime.utcnow().timestamp())}.{ext}"
        
        return safe_name

file_upload_security = FileUploadSecurity()

@app.post("/upload")
async def upload_file(request: Request):
    """Secure file upload endpoint."""
    form = await request.form()
    file = form.get("file")
    
    if not file or not file.filename:
        return JSONResponse(
            {"error": "No file provided"},
            status_code=400
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file
    is_valid, validation_message = file_upload_security.validate_file(file.filename, content)
    
    if not is_valid:
        SecurityLogger.log_security_event(
            "file_upload_rejected",
            ip_address=request.client.host if request.client else "unknown",
            details={
                "filename": file.filename,
                "reason": validation_message,
                "size": len(content)
            }
        )
        return JSONResponse(
            {"error": validation_message},
            status_code=400
        )
    
    # Generate safe filename
    safe_filename = file_upload_security.generate_safe_filename(file.filename)
    file_path = file_upload_security.upload_path / safe_filename
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
    SecurityLogger.log_security_event(
        "file_uploaded",
        ip_address=request.client.host if request.client else "unknown",
        details={
            "original_filename": file.filename,
            "safe_filename": safe_filename,
            "size": len(content),
            "mime_type": file.content_type
        }
    )
    
    return JSONResponse({
        "message": "File uploaded successfully",
        "filename": safe_filename,
        "size": len(content)
    })
```

## Database Security

### SQL Injection Prevention

```python
import sqlite3
from typing import List, Dict, Any

class SecureDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database with secure settings."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        conn.close()
    
    def get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        return conn
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SELECT query with parameters."""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query with parameters."""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount

# Example secure database operations
db = SecureDatabase("secure_app.db")

@app.get("/users/{user_id}")
async def get_user(request: Request):
    """Get user by ID - demonstrates parameterized query."""
    user_id = request.path_params["user_id"]
    
    # Validate user_id is integer
    try:
        user_id = int(user_id)
    except ValueError:
        return JSONResponse(
            {"error": "Invalid user ID"},
            status_code=400
        )
    
    # Use parameterized query to prevent SQL injection
    users = db.execute_query(
        "SELECT id, username, email, created_at FROM users WHERE id = ?",
        (user_id,)
    )
    
    if not users:
        return JSONResponse(
            {"error": "User not found"},
            status_code=404
        )
    
    return JSONResponse({"user": users[0]})

@app.get("/search/users")
async def search_users(request: Request):
    """Search users - demonstrates safe search implementation."""
    query = request.query_params.get("q", "").strip()
    
    if not query:
        return JSONResponse(
            {"error": "Search query is required"},
            status_code=400
        )
    
    # Validate and sanitize search query
    if len(query) < 2:
        return JSONResponse(
            {"error": "Search query must be at least 2 characters"},
            status_code=400
        )
    
    # Limit search query length
    if len(query) > 50:
        query = query[:50]
    
    # Use parameterized query with LIKE
    search_pattern = f"%{query}%"
    users = db.execute_query(
        "SELECT id, username, email FROM users WHERE username LIKE ? OR email LIKE ? LIMIT 20",
        (search_pattern, search_pattern)
    )
    
    return JSONResponse({"users": users})
```

## Error Handling and Information Disclosure

```python
import traceback
from velithon.responses import JSONResponse

class SecureErrorHandler:
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
    
    def handle_error(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle errors securely without information disclosure."""
        # Log the full error for developers
        SecurityLogger.log_security_event(
            "application_error",
            ip_address=request.client.host if request.client else "unknown",
            details={
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc() if self.debug_mode else None
            }
        )
        
        # Return safe error message to client
        if self.debug_mode:
            # In development, return detailed error
            return JSONResponse(
                {
                    "error": "Internal server error",
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc()
                },
                status_code=500
            )
        else:
            # In production, return generic error
            return JSONResponse(
                {"error": "Internal server error"},
                status_code=500
            )

# Error handler
error_handler = SecureErrorHandler(debug_mode=False)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return error_handler.handle_error(request, exc)
```

## Security Testing

```python
import pytest
import httpx

@pytest.mark.asyncio
async def test_input_validation():
    """Test input validation security."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Test SQL injection attempt
        response = await client.get("/users/'; DROP TABLE users; --")
        assert response.status_code == 400
        
        # Test XSS attempt
        response = await client.post("/register", json={
            "username": "<script>alert('xss')</script>",
            "email": "test@example.com",
            "password": "ValidPassword123!"
        })
        assert response.status_code == 400

@pytest.mark.asyncio
async def test_authentication_security():
    """Test authentication security measures."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Test account lockout
        for i in range(6):  # Exceed max attempts
            response = await client.post("/login", json={
                "username": "test_user",
                "password": "wrong_password"
            })
        
        # Account should be locked
        response = await client.post("/login", json={
            "username": "test_user",
            "password": "correct_password"
        })
        assert response.status_code == 423  # Locked

@pytest.mark.asyncio
async def test_file_upload_security():
    """Test file upload security."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Test malicious file upload
        malicious_content = b"<?php system($_GET['cmd']); ?>"
        
        response = await client.post(
            "/upload",
            files={"file": ("malicious.php", malicious_content, "application/php")}
        )
        assert response.status_code == 400
        assert "not allowed" in response.json()["error"]

@pytest.mark.asyncio
async def test_api_security():
    """Test API security measures."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Test without API key
        response = await client.get("/api/secure-data")
        assert response.status_code == 401
        
        # Test with invalid API key
        response = await client.get(
            "/api/secure-data",
            headers={"X-API-Key": "invalid_key"}
        )
        assert response.status_code == 401
```

## Security Checklist

### Development Phase
- [ ] Input validation on all user inputs
- [ ] Parameterized queries for database operations
- [ ] Secure password hashing (bcrypt)
- [ ] HTTPS enforcement
- [ ] Security headers implementation
- [ ] Error handling without information disclosure
- [ ] File upload validation
- [ ] Rate limiting implementation
- [ ] CSRF protection
- [ ] XSS prevention

### Testing Phase
- [ ] Penetration testing
- [ ] Vulnerability scanning
- [ ] Authentication bypass testing
- [ ] SQL injection testing
- [ ] XSS testing
- [ ] File upload security testing
- [ ] API security testing
- [ ] Rate limiting testing

### Deployment Phase
- [ ] Security configuration review
- [ ] Secrets management
- [ ] Environment variable security
- [ ] Database security configuration
- [ ] Network security
- [ ] SSL/TLS configuration
- [ ] Monitoring and alerting
- [ ] Backup security
- [ ] Access control review
- [ ] Security documentation

### Ongoing Maintenance
- [ ] Regular security updates
- [ ] Security log monitoring
- [ ] Incident response procedures
- [ ] Security awareness training
- [ ] Regular security audits
- [ ] Dependency vulnerability scanning
- [ ] Performance monitoring
- [ ] Compliance requirements
- [ ] Data privacy compliance
- [ ] Security policy updates

## Security Resources

### Tools and Libraries
- **Static Analysis**: bandit, semgrep, CodeQL
- **Dependency Scanning**: safety, pip-audit
- **Web Security**: OWASP ZAP, Burp Suite
- **Cryptography**: cryptography, bcrypt, PyJWT
- **Monitoring**: fail2ban, ELK stack, Prometheus

### Standards and Guidelines
- **OWASP Top 10**: Web application security risks
- **NIST Cybersecurity Framework**: Security guidelines
- **ISO 27001**: Information security management
- **PCI DSS**: Payment card industry security
- **GDPR**: Data protection regulation
- **HIPAA**: Healthcare information security

### Best Practices Summary
1. **Never trust user input** - Always validate and sanitize
2. **Use secure defaults** - Fail securely
3. **Implement defense in depth** - Multiple security layers
4. **Keep software updated** - Regular security patches
5. **Use strong authentication** - Multi-factor when possible
6. **Encrypt sensitive data** - At rest and in transit
7. **Log security events** - Monitor for threats
8. **Test security regularly** - Continuous security testing
9. **Train developers** - Security awareness
10. **Plan for incidents** - Have response procedures
