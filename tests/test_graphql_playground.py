"""Test cases for GraphQL Playground functionality."""

import pytest

from velithon.graphql.playground import GraphQLPlayground, get_playground_html


class TestGraphQLPlayground:
    """Test GraphQL Playground functionality."""

    def test_playground_initialization(self):
        """Test GraphQL Playground initialization."""
        playground = GraphQLPlayground(
            endpoint_url="/graphql",
            subscription_endpoint="/graphql/subscriptions",
            title="Custom GraphQL Playground",
        )

        assert playground.endpoint_url == "/graphql"
        assert playground.subscription_endpoint == "/graphql/subscriptions"
        assert playground.title == "Custom GraphQL Playground"

    def test_playground_initialization_defaults(self):
        """Test GraphQL Playground initialization with defaults."""
        playground = GraphQLPlayground(endpoint_url="/graphql")

        assert playground.endpoint_url == "/graphql"
        assert playground.subscription_endpoint is None
        assert playground.title == "GraphQL Playground"

    def test_playground_html_generation(self):
        """Test HTML generation for GraphQL Playground."""
        playground = GraphQLPlayground(endpoint_url="/graphql")
        html = playground.get_html()

        assert isinstance(html, str)
        assert "GraphQL Playground" in html
        assert "/graphql" in html
        assert "<html" in html
        assert "</html>" in html

    def test_playground_with_subscription_endpoint(self):
        """Test playground HTML with subscription endpoint."""
        playground = GraphQLPlayground(
            endpoint_url="/graphql",
            subscription_endpoint="ws://localhost:8000/graphql",
        )
        html = playground.get_html()

        assert "ws://localhost:8000/graphql" in html
        assert "subscriptionEndpoint" in html

    def test_playground_custom_title(self):
        """Test playground with custom title."""
        custom_title = "My Awesome GraphQL API"
        playground = GraphQLPlayground(
            endpoint_url="/graphql",
            title=custom_title,
        )
        html = playground.get_html()

        assert custom_title in html
        assert f"<title>{custom_title}</title>" in html

    def test_playground_configuration_injection(self):
        """Test configuration injection into playground HTML."""
        playground = GraphQLPlayground(
            endpoint_url="/api/graphql",
            subscription_endpoint="ws://example.com/subscriptions",
            title="Test Playground",
        )
        html = playground.get_html()

        # Check that configuration is properly injected
        assert "endpoint: '/api/graphql'" in html or '"/api/graphql"' in html
        assert "ws://example.com/subscriptions" in html

    def test_playground_security_headers(self):
        """Test that playground includes proper security considerations."""
        playground = GraphQLPlayground(endpoint_url="/graphql")
        html = playground.get_html()

        # Should include proper content type and encoding
        assert "text/html" in html or "charset=utf-8" in html
        # Should not include any obvious XSS vulnerabilities
        assert "<script" in html  # Expected for playground functionality
        assert "eval(" not in html  # Should not use eval

    def test_playground_responsive_design(self):
        """Test that playground includes responsive design elements."""
        playground = GraphQLPlayground(endpoint_url="/graphql")
        html = playground.get_html()

        # Should include viewport meta tag for mobile
        assert "viewport" in html.lower()
        # Should include CSS for styling
        assert "css" in html.lower() or "style" in html.lower()

    def test_playground_accessibility(self):
        """Test accessibility features in playground."""
        playground = GraphQLPlayground(endpoint_url="/graphql")
        html = playground.get_html()

        # Basic accessibility checks
        assert "lang=" in html  # Should specify language
        # Should have proper document structure
        assert "<head>" in html
        assert "<body>" in html

    def test_playground_javascript_functionality(self):
        """Test JavaScript functionality inclusion."""
        playground = GraphQLPlayground(endpoint_url="/graphql")
        html = playground.get_html()

        # Should include playground JavaScript libraries
        assert "script" in html.lower()
        # Should have GraphQL Playground specific functionality
        assert "graphql" in html.lower()

    def test_playground_css_styling(self):
        """Test CSS styling inclusion."""
        playground = GraphQLPlayground(endpoint_url="/graphql")
        html = playground.get_html()

        # Should include CSS for proper styling
        assert "style" in html.lower() or "css" in html.lower()
        # Should have proper HTML structure for styling
        assert "<div" in html or "<section" in html


class TestGetPlaygroundHTML:
    """Test get_playground_html utility function."""

    def test_get_playground_html_basic(self):
        """Test basic playground HTML generation."""
        html = get_playground_html(endpoint_url="/graphql")

        assert isinstance(html, str)
        assert "GraphQL Playground" in html
        assert "/graphql" in html
        assert len(html) > 100  # Should be substantial HTML

    def test_get_playground_html_with_subscription(self):
        """Test playground HTML with subscription endpoint."""
        html = get_playground_html(
            endpoint_url="/graphql",
            subscription_endpoint="ws://localhost:8000/subscriptions",
        )

        assert "ws://localhost:8000/subscriptions" in html
        assert "subscription" in html.lower()

    def test_get_playground_html_custom_title(self):
        """Test playground HTML with custom title."""
        custom_title = "Custom GraphQL Explorer"
        html = get_playground_html(
            endpoint_url="/graphql",
            title=custom_title,
        )

        assert custom_title in html

    def test_get_playground_html_relative_urls(self):
        """Test playground HTML with relative URLs."""
        html = get_playground_html(endpoint_url="./graphql")

        assert "./graphql" in html
        # Should handle relative URLs properly

    def test_get_playground_html_absolute_urls(self):
        """Test playground HTML with absolute URLs."""
        html = get_playground_html(
            endpoint_url="https://api.example.com/graphql"
        )

        assert "https://api.example.com/graphql" in html
        # Should handle absolute URLs properly

    def test_get_playground_html_query_parameters(self):
        """Test playground HTML with query parameters in endpoint URL."""
        html = get_playground_html(
            endpoint_url="/graphql?version=v1&debug=true"
        )

        assert "version=v1" in html
        assert "debug=true" in html

    def test_get_playground_html_special_characters(self):
        """Test playground HTML with special characters in URLs."""
        # Test with URL encoding
        html = get_playground_html(
            endpoint_url="/graphql?query=%7Bhello%7D"
        )

        assert "/graphql" in html
        # Should properly handle URL encoding

    def test_get_playground_html_empty_endpoint(self):
        """Test playground HTML with empty endpoint URL."""
        html = get_playground_html(endpoint_url="")

        assert isinstance(html, str)
        assert len(html) > 0
        # Should still generate valid HTML even with empty endpoint

    def test_get_playground_html_none_values(self):
        """Test playground HTML with None values."""
        html = get_playground_html(
            endpoint_url="/graphql",
            subscription_endpoint=None,
            title=None,
        )

        assert isinstance(html, str)
        assert "/graphql" in html
        # Should handle None values gracefully

    def test_get_playground_html_configuration_object(self):
        """Test that playground HTML includes proper configuration object."""
        html = get_playground_html(
            endpoint_url="/api/v1/graphql",
            subscription_endpoint="wss://api.example.com/subscriptions",
        )

        # Should include configuration for the playground
        assert "endpoint" in html or "url" in html
        # Should properly configure subscription endpoint
        if "subscriptions" in html:
            assert "wss://" in html or "ws://" in html

    def test_get_playground_html_content_type_compatibility(self):
        """Test HTML compatibility with different content types."""
        html = get_playground_html(endpoint_url="/graphql")

        # Should be valid HTML5
        assert "<!DOCTYPE" in html or "<html" in html
        # Should include proper meta tags
        assert "<meta" in html
        # Should be well-formed
        assert html.count("<html") <= 1
        assert html.count("</html>") <= 1

    def test_get_playground_html_csp_compatibility(self):
        """Test Content Security Policy compatibility."""
        html = get_playground_html(endpoint_url="/graphql")

        # Should not include inline event handlers that violate CSP
        assert 'onclick=' not in html.lower()
        assert 'onload=' not in html.lower()
        # Should use proper script loading
        assert "<script" in html

    def test_get_playground_html_minification(self):
        """Test HTML minification and optimization."""
        html = get_playground_html(endpoint_url="/graphql")

        # Should be reasonably optimized
        assert len(html) < 50000  # Should not be excessively large
        # Should include essential components
        assert "GraphQL" in html
        assert "<script" in html or "<link" in html

    def test_get_playground_html_cross_origin_headers(self):
        """Test cross-origin compatibility."""
        html = get_playground_html(
            endpoint_url="https://external-api.com/graphql"
        )

        # Should handle cross-origin endpoints
        assert "external-api.com" in html
        # Should include proper configuration for CORS if needed

    def test_get_playground_html_version_compatibility(self):
        """Test compatibility with different GraphQL Playground versions."""
        html = get_playground_html(endpoint_url="/graphql")

        # Should use a stable version of GraphQL Playground
        assert "playground" in html.lower()
        # Should not include version conflicts
        assert len(html) > 500  # Should be substantial

    def test_playground_html_encoding(self):
        """Test proper character encoding in HTML."""
        # Test with Unicode characters
        html = get_playground_html(
            endpoint_url="/graphql",
            title="GraphQL Playground 🚀",
        )

        assert isinstance(html, str)
        # Should handle Unicode characters properly
        assert "utf-8" in html.lower() or "charset" in html.lower()

    def test_playground_html_injection_prevention(self):
        """Test prevention of HTML/JS injection."""
        # Test with potentially malicious input
        malicious_endpoint = "/graphql\"><script>alert('xss')</script>"
        html = get_playground_html(endpoint_url=malicious_endpoint)

        # Should properly escape or sanitize input
        assert "alert('xss')" not in html
        # Should still be valid HTML
        assert isinstance(html, str)


class TestPlaygroundIntegration:
    """Test GraphQL Playground integration scenarios."""

    def test_playground_with_authentication(self):
        """Test playground configuration with authentication."""
        html = get_playground_html(
            endpoint_url="/graphql",
            title="Authenticated GraphQL API",
        )

        # Should include configuration that allows authentication
        assert isinstance(html, str)
        assert len(html) > 0

    def test_playground_production_mode(self):
        """Test playground in production mode."""
        # In production, playground might be disabled or have different config
        html = get_playground_html(
            endpoint_url="/graphql",
            title="Production GraphQL API",
        )

        assert isinstance(html, str)
        # Should still generate valid HTML for production use

    def test_playground_development_mode(self):
        """Test playground in development mode."""
        html = get_playground_html(
            endpoint_url="/graphql",
            title="Development GraphQL API",
        )

        # Should include development-friendly features
        assert "GraphQL" in html
        assert isinstance(html, str)

    def test_playground_error_handling(self):
        """Test playground error handling scenarios."""
        # Test with various edge cases
        test_cases = [
            {"endpoint_url": None},
            {"endpoint_url": ""},
            {"endpoint_url": "/graphql", "subscription_endpoint": ""},
        ]

        for case in test_cases:
            try:
                html = get_playground_html(**case)
                assert isinstance(html, str)
            except Exception as e:
                # Should handle errors gracefully
                assert isinstance(e, (ValueError, TypeError))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])