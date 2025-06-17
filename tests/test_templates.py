"""
Tests for the Velithon Template Engine.

This module tests the high-performance template engine built in Rust
with Handlebars-style syntax.
"""

import tempfile
from pathlib import Path

import pytest

from velithon.responses import HTMLResponse
from velithon.templates import TemplateEngine, TemplateResponse, render_template


class TestTemplateEngine:
    """Test the template engine functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.template_dir = Path(self.temp_dir)

        # Create test templates
        (self.template_dir / 'simple.html').write_text('<h1>Hello {{name}}!</h1>')

        (self.template_dir / 'complex.html').write_text(
            """
<!DOCTYPE html>
<html>
<head><title>{{title}}</title></head>
<body>
    <h1>{{title}}</h1>
    {{#if user}}
        <p>Welcome, {{upper user.name}}!</p>
        <p>Email: {{user.email}}</p>
    {{else}}
        <p>Please log in.</p>
    {{/if}}
    
    {{#if items}}
        <ul>
        {{#each items}}
            <li>{{name}} - ${{price}}</li>
        {{/each}}
        </ul>
        <p>Total items: {{len items}}</p>
    {{/if}}
</body>
</html>
        """.strip()
        )

        (self.template_dir / 'helpers.html').write_text(
            '<p>{{upper name}} - {{lower name}} - {{len items}}</p>'
        )

    def test_engine_initialization(self):
        """Test template engine initialization."""
        engine = TemplateEngine(self.template_dir)
        assert engine.template_dir == self.template_dir
        assert len(engine.get_template_names()) > 0

    def test_engine_initialization_invalid_dir(self):
        """Test template engine initialization with invalid directory."""
        with pytest.raises(FileNotFoundError):
            TemplateEngine('/non/existent/path')

    def test_simple_rendering(self):
        """Test simple template rendering."""
        engine = TemplateEngine(self.template_dir)

        result = engine.render('simple.html', {'name': 'World'})
        assert result == '<h1>Hello World!</h1>'

    def test_complex_rendering_with_user(self):
        """Test complex template rendering with user context."""
        engine = TemplateEngine(self.template_dir)

        context = {
            'title': 'My Page',
            'user': {'name': 'alice', 'email': 'alice@example.com'},
            'items': [
                {'name': 'Apple', 'price': 1.50},
                {'name': 'Banana', 'price': 0.75},
            ],
        }

        result = engine.render('complex.html', context)

        assert 'My Page' in result
        assert 'Welcome, ALICE!' in result
        assert 'alice@example.com' in result
        assert 'Apple - $1.5' in result
        assert 'Banana - $0.75' in result
        assert 'Total items: 2' in result

    def test_complex_rendering_without_user(self):
        """Test complex template rendering without user context."""
        engine = TemplateEngine(self.template_dir)

        context = {'title': 'My Page', 'items': []}

        result = engine.render('complex.html', context)

        assert 'My Page' in result
        assert 'Please log in.' in result
        assert 'Welcome' not in result

    def test_helper_functions(self):
        """Test built-in helper functions."""
        engine = TemplateEngine(self.template_dir)

        context = {'name': 'Alice', 'items': [1, 2, 3, 4, 5]}

        result = engine.render('helpers.html', context)
        assert 'ALICE - alice - 5' in result

    def test_template_registration(self):
        """Test registering templates from string."""
        engine = TemplateEngine(self.template_dir)

        template_content = '<p>Hello {{name}}! You have {{len messages}} messages.</p>'
        engine.register_template('custom', template_content)

        result = engine.render(
            'custom', {'name': 'Bob', 'messages': ['msg1', 'msg2', 'msg3']}
        )

        assert 'Hello Bob!' in result
        assert 'You have 3 messages' in result

    def test_template_not_found(self):
        """Test rendering non-existent template."""
        engine = TemplateEngine(self.template_dir)

        with pytest.raises(FileNotFoundError):
            engine.render('nonexistent.html', {})

    def test_path_traversal_protection(self):
        """Test path traversal attack prevention."""
        engine = TemplateEngine(self.template_dir)

        with pytest.raises(Exception):  # Should raise SecurityWarning
            engine.render('../../../etc/passwd', {})

        with pytest.raises(Exception):
            engine.render('..\\..\\windows\\system32', {})

    def test_template_names_management(self):
        """Test template name management."""
        engine = TemplateEngine(self.template_dir)

        initial_names = engine.get_template_names()
        assert len(initial_names) >= 3
        assert 'simple.html' in initial_names
        assert 'complex.html' in initial_names
        assert 'helpers.html' in initial_names

        # Register a new template
        engine.register_template('new_template', '<p>{{message}}</p>')

        updated_names = engine.get_template_names()
        assert len(updated_names) == len(initial_names) + 1
        assert 'new_template' in updated_names

        # Check if template is registered
        assert engine.is_template_registered('new_template')
        assert not engine.is_template_registered('non_existent')

    def test_render_response(self):
        """Test render_response method."""
        engine = TemplateEngine(self.template_dir)

        response = engine.render_response('simple.html', {'name': 'World'})

        assert isinstance(response, HTMLResponse)
        assert response.status_code == 200
        assert response.media_type == 'text/html'

        # Test with custom status code and headers
        response = engine.render_response(
            'simple.html',
            {'name': 'Test'},
            status_code=201,
            headers={'X-Custom': 'value'},
        )

        assert response.status_code == 201

    def test_strict_mode(self):
        """Test strict mode functionality."""
        engine = TemplateEngine(self.template_dir, strict_mode=True)

        # This should work fine
        result = engine.render('simple.html', {'name': 'Test'})
        assert 'Hello Test!' in result

        # Test toggling strict mode
        engine.set_strict_mode(False)
        engine.set_strict_mode(True)

    def test_template_loading(self):
        """Test explicit template loading."""
        engine = TemplateEngine(self.template_dir)

        # Clear templates
        engine.clear_templates()
        assert len(engine.get_template_names()) == 0

        # Load specific template
        engine.load_template('simple.html')
        assert engine.is_template_registered('simple.html')

        # Load all templates
        loaded_templates = engine.load_templates()
        assert len(loaded_templates) >= 3
        assert 'simple.html' in loaded_templates


class TestTemplateResponse:
    """Test the TemplateResponse class."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.template_dir = Path(self.temp_dir)

        (self.template_dir / 'test.html').write_text(
            '<h1>{{title}}</h1><p>{{message}}</p>'
        )

        self.engine = TemplateEngine(self.template_dir)

    def test_template_response_creation(self):
        """Test TemplateResponse creation."""
        context = {'title': 'Test', 'message': 'Hello World'}

        template_response = TemplateResponse(
            self.engine, 'test.html', context, status_code=200
        )

        assert template_response.status_code == 200

        # Test rendering
        html = template_response.render()
        assert '<h1>Test</h1>' in html
        assert '<p>Hello World</p>' in html

    def test_template_response_to_response(self):
        """Test converting TemplateResponse to HTMLResponse."""
        context = {'title': 'Test', 'message': 'Hello World'}

        template_response = TemplateResponse(
            self.engine, 'test.html', context, status_code=201
        )

        html_response = template_response.to_response()

        assert isinstance(html_response, HTMLResponse)
        assert html_response.status_code == 201

    def test_template_response_headers(self):
        """Test TemplateResponse header management."""
        template_response = TemplateResponse(
            self.engine,
            'test.html',
            {'title': 'Test', 'message': 'Hello'},
        )

        # Set individual header
        template_response.set_header('X-Custom', 'value')

        # Add multiple headers
        template_response.add_headers(
            {'X-Another': 'another-value', 'X-Third': 'third-value'}
        )

        html_response = template_response.to_response()

        # Note: headers might be transformed, so we check the raw headers
        assert any('x-custom' in h[0].lower() for h in html_response.raw_headers)


class TestConvenienceFunctions:
    """Test convenience functions."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.template_dir = Path(self.temp_dir)

        (self.template_dir / 'quick.html').write_text('<h1>{{title}}</h1>')

    def test_render_template_function(self):
        """Test the render_template convenience function."""
        result = render_template(
            self.template_dir, 'quick.html', {'title': 'Quick Test'}
        )

        assert '<h1>Quick Test</h1>' in result

    def test_render_template_no_context(self):
        """Test render_template without context."""
        (self.template_dir / 'no_context.html').write_text('<h1>No Context Needed</h1>')

        result = render_template(self.template_dir, 'no_context.html')
        assert '<h1>No Context Needed</h1>' in result


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.template_dir = Path(self.temp_dir)

        (self.template_dir / 'empty.html').write_text('')
        (self.template_dir / 'syntax_error.html').write_text(
            '{{#if unclosed condition}}<p>This will fail</p>'
        )

    def test_empty_template(self):
        """Test rendering empty template."""
        engine = TemplateEngine(self.template_dir)

        result = engine.render('empty.html', {'name': 'Test'})
        assert result == ''

    def test_empty_context(self):
        """Test rendering with empty context."""
        engine = TemplateEngine(self.template_dir)

        (self.template_dir / 'no_vars.html').write_text('<h1>Static Content</h1>')

        result = engine.render('no_vars.html', {})
        assert result == '<h1>Static Content</h1>'

    def test_none_context(self):
        """Test rendering with None context."""
        engine = TemplateEngine(self.template_dir)

        (self.template_dir / 'no_vars.html').write_text('<h1>Static Content</h1>')

        result = engine.render('no_vars.html', None)
        assert result == '<h1>Static Content</h1>'

    def test_complex_context_types(self):
        """Test rendering with complex context types."""
        engine = TemplateEngine(self.template_dir)

        (self.template_dir / 'complex_types.html').write_text(
            """
        <p>String: {{str_val}}</p>
        <p>Integer: {{int_val}}</p>
        <p>Float: {{float_val}}</p>
        <p>Boolean: {{bool_val}}</p>
        <p>List length: {{len list_val}}</p>
        """.strip()
        )

        context = {
            'str_val': 'hello',
            'int_val': 42,
            'float_val': 3.14,
            'bool_val': True,
            'list_val': [1, 2, 3, 4, 5],
        }

        result = engine.render('complex_types.html', context)

        assert 'String: hello' in result
        assert 'Integer: 42' in result
        assert 'Float: 3.14' in result
        assert 'Boolean: true' in result
        assert 'List length: 5' in result
