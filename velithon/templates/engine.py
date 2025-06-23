"""Velithon Template Engine.

High-performance template engine with Handlebars-style syntax, built in Rust
for maximum performance and safety.

Features:
- Handlebars-style template syntax
- Template compilation and caching
- Context variable injection
- Template inheritance and partials
- XSS protection and security features
- Integration with Velithon responses
"""

from pathlib import Path
from typing import Any

from velithon._velithon import _TemplateResponse, create_template_engine
from velithon.responses import HTMLResponse


class TemplateEngine:
    """High-performance template engine with Handlebars syntax.

    This template engine is implemented in Rust for maximum performance and provides
    a familiar Handlebars-style syntax with additional security features.

    Example:
        ```python
        # Create template engine
        engine = TemplateEngine('templates/')

        # Render template
        html = engine.render('index.html', {'name': 'World', 'items': [1, 2, 3]})

        # Use with Velithon responses
        response = engine.render_response('page.html', {'title': 'My Page'})
        ```

    Template Syntax Examples:
        ```handlebars
        <!-- Variables -->
        <h1>Hello {{name}}!</h1>

        <!-- Conditionals -->
        {{#if user}}
            <p>Welcome, {{user.name}}!</p>
        {{else}}
            <p>Please log in.</p>
        {{/if}}

        <!-- Loops -->
        <ul>
        {{#each items}}
            <li>{{this}}</li>
        {{/each}}
        </ul>

        <!-- Built-in helpers -->
        <p>{{upper name}} - {{len items}} items</p>
        <p>Today: {{format_date today}}</p>
        ```

    """

    def __init__(
        self,
        template_dir: str | Path,
        *,
        auto_reload: bool = True,
        cache_enabled: bool = True,
        strict_mode: bool = True,
    ) -> None:
        """Initialize the template engine.

        Args:
            template_dir: Directory containing template files
            auto_reload: Whether to automatically reload templates when changed
            cache_enabled: Whether to enable template caching
            strict_mode: Whether to use strict mode (recommended for security)

        Raises:
            FileNotFoundError: If template directory doesn't exist

        """
        self.template_dir = Path(template_dir)
        if not self.template_dir.exists():
            raise FileNotFoundError(f'Template directory not found: {template_dir}')

        self._engine = create_template_engine(
            str(self.template_dir),
            auto_reload,
            cache_enabled,
            strict_mode,
        )

        # Load all templates on initialization (skip files with syntax errors)
        try:
            self.load_templates()
        except Exception as e:
            # If loading fails, continue but log the error
            import warnings

            warnings.warn(f'Some templates failed to load during initialization: {e}')

    def render(self, template_name: str, context: dict[str, Any] | None = None) -> str:
        """Render a template with the given context.

        Args:
            template_name: Name of the template file (relative to template_dir)
            context: Dictionary of variables to pass to the template

        Returns:
            Rendered HTML string

        Raises:
            FileNotFoundError: If template doesn't exist
            RuntimeError: If template has syntax errors or render fails
            SecurityWarning: If path traversal attempt is detected

        Example:
            ```python
            html = engine.render(
                'user.html',
                {
                    'user': {'name': 'Alice', 'email': 'alice@example.com'},
                    'items': ['apple', 'banana', 'cherry'],
                },
            )
            ```

        """
        return self._engine.render(template_name, context)

    def render_response(
        self,
        template_name: str,
        context: dict[str, Any] | None = None,
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> HTMLResponse:
        """Render a template and return an HTMLResponse.

        Args:
            template_name: Name of the template file
            context: Dictionary of variables to pass to the template
            status_code: HTTP status code (default: 200)
            headers: Additional HTTP headers

        Returns:
            HTMLResponse object ready to be returned from an endpoint

        Example:
            ```python
            @app.get('/')
            async def home():
                return engine.render_response('home.html', {'title': 'Welcome'})
            ```

        """
        html_content = self.render(template_name, context)
        response = HTMLResponse(html_content, status_code=status_code, headers=headers)
        return response

    def load_template(self, template_name: str) -> None:
        """Load and register a specific template.

        Args:
            template_name: Name of the template file to load

        Raises:
            IOError: If template file cannot be read
            SyntaxError: If template has syntax errors

        """
        self._engine.load_template(template_name)

    def load_templates(self) -> list[str]:
        """Load all templates from the template directory.

        Returns:
            List of loaded template names

        Raises:
            IOError: If template directory cannot be read

        """
        return self._engine.load_templates()

    def register_template(self, name: str, content: str) -> None:
        """Register a template from string content.

        Args:
            name: Name to register the template under
            content: Template content as string

        Raises:
            SyntaxError: If template has syntax errors

        Example:
            ```python
            engine.register_template('hello', 'Hello {{name}}!')
            html = engine.render('hello', {'name': 'World'})
            ```

        """
        self._engine.register_template(name, content)

    def clear_templates(self) -> None:
        """Clear all registered templates."""
        self._engine.clear_templates()

    def get_template_names(self) -> list[str]:
        """Get list of registered template names.

        Returns:
            List of template names

        """
        return self._engine.get_template_names()

    def is_template_registered(self, name: str) -> bool:
        """Check if a template is registered.

        Args:
            name: Template name to check

        Returns:
            True if template is registered, False otherwise

        """
        return self._engine.is_template_registered(name)

    def set_strict_mode(self, strict: bool) -> None:
        """Enable or disable strict mode.

        Args:
            strict: Whether to enable strict mode

        """
        self._engine.set_strict_mode(strict)

    @property
    def template_dir(self) -> Path:
        """Get the template directory path."""
        return self._template_dir

    @template_dir.setter
    def template_dir(self, value: str | Path) -> None:
        """Set the template directory path."""
        self._template_dir = Path(value)


class TemplateResponse:
    """Template response for convenient HTTP responses.

    This class provides a convenient way to create HTTP responses from templates
    with proper content type headers and status codes.

    Example:
        ```python
        @app.get('/profile')
        async def profile():
            template_response = TemplateResponse(
                engine, 'profile.html', {'user': current_user}, status_code=200
            )
            return template_response.to_response()
        ```

    """

    def __init__(
        self,
        engine: TemplateEngine,
        template_name: str,
        context: dict[str, Any] | None = None,
        *,
        status_code: int = 200,
    ) -> None:
        """Initialize template response.

        Args:
            engine: Template engine instance
            template_name: Name of the template to render
            context: Context variables for the template
            status_code: HTTP status code

        """
        self._response = _TemplateResponse(
            engine._engine,
            template_name,
            context,
            status_code,
        )

    def render(self) -> str:
        """Render the template and return HTML content.

        Returns:
            Rendered HTML string

        """
        return self._response.render()

    def to_response(self) -> HTMLResponse:
        """Convert to Velithon HTMLResponse.

        Returns:
            HTMLResponse object

        """
        html_content = self.render()
        return HTMLResponse(
            html_content,
            status_code=self._response.get_status_code(),
            headers=self._response.get_headers(),
        )

    @property
    def status_code(self) -> int:
        """Get the status code."""
        return self._response.get_status_code()

    @status_code.setter
    def status_code(self, value: int) -> None:
        """Set the status code."""
        self._response.set_status_code(value)

    def set_header(self, key: str, value: str) -> None:
        """Set a response header.

        Args:
            key: Header name
            value: Header value

        """
        self._response.set_header(key, value)

    def add_headers(self, headers: dict[str, str]) -> None:
        """Add multiple headers.

        Args:
            headers: Dictionary of headers to add

        """
        self._response.add_headers(headers)


def create_template_engine_from_config(config: dict[str, Any]) -> TemplateEngine:
    """Create a template engine from configuration dictionary.

    Args:
        config: Configuration dictionary with keys:
            - template_dir: Template directory path
            - auto_reload: Whether to auto-reload templates (default: True)
            - cache_enabled: Whether to enable caching (default: True)
            - strict_mode: Whether to use strict mode (default: True)

    Returns:
        Configured TemplateEngine instance

    Example:
        ```python
        config = {
            'template_dir': 'templates/',
            'auto_reload': False,  # Production setting
            'cache_enabled': True,
            'strict_mode': True,
        }
        engine = create_template_engine_from_config(config)
        ```

    """
    return TemplateEngine(
        template_dir=config['template_dir'],
        auto_reload=config.get('auto_reload', True),
        cache_enabled=config.get('cache_enabled', True),
        strict_mode=config.get('strict_mode', True),
    )


# Convenience function for quick template rendering
def render_template(
    template_dir: str | Path,
    template_name: str,
    context: dict[str, Any] | None = None,
) -> str:
    """Quick template rendering function.

    Args:
        template_dir: Directory containing templates
        template_name: Name of template to render
        context: Template context variables

    Returns:
        Rendered HTML string

    Example:
        ```python
        html = render_template('templates/', 'hello.html', {'name': 'World'})
        ```

    """
    engine = TemplateEngine(template_dir)
    return engine.render(template_name, context)


# Export the main classes
__all__ = [
    'TemplateEngine',
    'TemplateResponse',
    'create_template_engine_from_config',
    'render_template',
]
