"""
Tests for OpenAPI security documentation integration.
"""
import pytest

from velithon import Velithon
from velithon.security import HTTPBearer, HTTPBasic, APIKeyHeader, OAuth2PasswordBearer
from velithon.openapi.docs import get_security_schemes


class TestOpenAPISecurityIntegration:
    """Test OpenAPI security documentation."""
    
    def test_get_security_schemes(self):
        """Test that security schemes are properly generated."""
        schemes = get_security_schemes()
        
        # Check that all expected schemes are present
        expected_schemes = ["bearerAuth", "basicAuth", "apiKeyAuth", "oauth2"]
        
        for scheme_name in expected_schemes:
            assert scheme_name in schemes
        
        # Check bearerAuth scheme
        bearer_scheme = schemes["bearerAuth"]
        assert bearer_scheme["type"] == "http"
        assert bearer_scheme["scheme"] == "bearer"
        assert bearer_scheme["bearerFormat"] == "JWT"
        
        # Check basicAuth scheme
        basic_scheme = schemes["basicAuth"]
        assert basic_scheme["type"] == "http"
        assert basic_scheme["scheme"] == "basic"
        
        # Check apiKeyAuth scheme
        api_key_scheme = schemes["apiKeyAuth"]
        assert api_key_scheme["type"] == "apiKey"
        assert api_key_scheme["in"] == "header"
        assert api_key_scheme["name"] == "X-API-Key"
        
        # Check oauth2 scheme
        oauth2_scheme = schemes["oauth2"]
        assert oauth2_scheme["type"] == "oauth2"
        assert "flows" in oauth2_scheme
        assert "password" in oauth2_scheme["flows"]
        assert oauth2_scheme["flows"]["password"]["tokenUrl"] == "/token"
    
    def test_app_openapi_includes_security_schemes(self):
        """Test that Velithon app includes security schemes in OpenAPI spec."""
        app = Velithon(
            title="Test App",
            description="Test application with security"
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        openapi_spec = app.get_openapi()
        
        # Check that security schemes are included
        assert "components" in openapi_spec
        assert "securitySchemes" in openapi_spec["components"]
        
        security_schemes = openapi_spec["components"]["securitySchemes"]
        
        # Verify specific schemes
        assert "bearerAuth" in security_schemes
        assert "basicAuth" in security_schemes
        assert "apiKeyAuth" in security_schemes
        assert "oauth2" in security_schemes
    
    def test_individual_security_scheme_definitions(self):
        """Test individual security scheme OpenAPI definitions."""
        # Test HTTPBearer
        bearer = HTTPBearer()
        bearer_def = bearer.get_openapi_security_definition()
        assert bearer_def["type"] == "http"
        assert bearer_def["scheme"] == "bearer"
        
        # Test HTTPBasic
        basic = HTTPBasic()
        basic_def = basic.get_openapi_security_definition()
        assert basic_def["type"] == "http"
        assert basic_def["scheme"] == "basic"
        
        # Test APIKeyHeader
        api_key = APIKeyHeader(name="X-Custom-Key")
        api_key_def = api_key.get_openapi_security_definition()
        assert api_key_def["type"] == "apiKey"
        assert api_key_def["in"] == "header"
        assert api_key_def["name"] == "X-Custom-Key"
        
        # Test OAuth2PasswordBearer
        oauth2 = OAuth2PasswordBearer(token_url="/custom/token")
        oauth2_def = oauth2.get_openapi_security_definition()
        assert oauth2_def["type"] == "oauth2"
        assert oauth2_def["flows"]["password"]["tokenUrl"] == "/custom/token"
    
    def test_openapi_spec_structure(self):
        """Test complete OpenAPI specification structure with security."""
        app = Velithon(
            title="Security Test API",
            version="1.0.0",
            description="API with comprehensive security testing"
        )
        
        @app.get("/public")
        async def public_endpoint():
            """Public endpoint requiring no authentication."""
            return {"message": "public"}
        
        @app.get("/protected")
        async def protected_endpoint():
            """Protected endpoint requiring authentication."""
            return {"message": "protected"}
        
        openapi_spec = app.get_openapi()
        
        # Test basic structure
        assert openapi_spec["openapi"] == "3.0.0"
        assert openapi_spec["info"]["title"] == "Security Test API"
        assert openapi_spec["info"]["version"] == "1.0.0"
        
        # Test components section
        assert "components" in openapi_spec
        components = openapi_spec["components"]
        
        # Test security schemes
        assert "securitySchemes" in components
        security_schemes = components["securitySchemes"]
        
        # Verify all security schemes are present
        expected_schemes = ["bearerAuth", "basicAuth", "apiKeyAuth", "oauth2"]
        for scheme in expected_schemes:
            assert scheme in security_schemes
        
        # Test paths
        assert "paths" in openapi_spec
        paths = openapi_spec["paths"]
        
        # Verify endpoints are documented
        assert "/public" in paths
        assert "/protected" in paths
        
        # Check endpoint structure
        public_endpoint = paths["/public"]["get"]
        assert "responses" in public_endpoint
        
        protected_endpoint = paths["/protected"]["get"]
        assert "responses" in protected_endpoint


class TestSecuritySchemeValidation:
    """Test security scheme validation and error handling."""
    
    def test_http_bearer_validation(self):
        """Test HTTPBearer scheme validation."""
        scheme = HTTPBearer()
        
        # Test valid scheme
        definition = scheme.get_openapi_security_definition()
        assert definition["type"] == "http"
        assert definition["scheme"] == "bearer"
        
        # Test bearer format
        assert "bearerFormat" in definition
        assert definition["bearerFormat"] == "JWT"
    
    def test_api_key_header_validation(self):
        """Test APIKeyHeader scheme validation."""
        # Test with custom name
        scheme = APIKeyHeader(name="X-Custom-API-Key")
        definition = scheme.get_openapi_security_definition()
        
        assert definition["type"] == "apiKey"
        assert definition["in"] == "header"
        assert definition["name"] == "X-Custom-API-Key"
    
    def test_oauth2_password_bearer_validation(self):
        """Test OAuth2PasswordBearer scheme validation."""
        scheme = OAuth2PasswordBearer(
            token_url="/auth/token",
            scopes={"read": "Read access", "write": "Write access"}
        )
        definition = scheme.get_openapi_security_definition()
        
        assert definition["type"] == "oauth2"
        assert "flows" in definition
        assert "password" in definition["flows"]
        
        password_flow = definition["flows"]["password"]
        assert password_flow["tokenUrl"] == "/auth/token"
        assert "scopes" in password_flow
        assert password_flow["scopes"]["read"] == "Read access"
        assert password_flow["scopes"]["write"] == "Write access"


if __name__ == "__main__":
    pytest.main([__file__])
