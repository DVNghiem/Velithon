"""Documentation Generator for Velithon API.

Generates comprehensive API documentation from routes, type hints, and docstrings.
Supports Markdown and PDF export formats.
"""

import inspect
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path as PathLibPath
from typing import Annotated, Any, Union, get_args, get_origin

try:
    import markdown
    from jinja2 import DictLoader, Environment

    MARKDOWN_AVAILABLE = True
except ImportError as e:
    MARKDOWN_AVAILABLE = False
    markdown_error = e

try:
    import weasyprint

    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

try:
    from pydantic import BaseModel
    from pydantic.fields import FieldInfo

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = None
    FieldInfo = None

from velithon.application import Velithon
from velithon.params.params import Body, Cookie, File, Form, Header, Path, Query
from velithon.routing import Route


@dataclass
class ParameterInfo:
    """Information about a function parameter."""

    name: str
    type_annotation: str
    param_type: str
    required: bool
    default_value: Any = None
    description: str | None = None
    detailed_description: str | None = None


@dataclass
class ResponseInfo:
    """Information about a response."""

    status_code: int
    description: str
    content_type: str = 'application/json'


@dataclass
class RouteInfo:
    """Comprehensive information about a route."""

    path: str
    methods: list[str]
    summary: str
    description: str
    parameters: list[ParameterInfo]
    responses: list[ResponseInfo]
    tags: list[str] = field(default_factory=list)
    endpoint_function: Any = None


class DocumentationConfig:
    """Configuration for documentation generation."""

    def __init__(
        self,
        title: str = 'API Documentation',
        version: str = '1.0.0',
        description: str = 'Generated API Documentation',
        contact_name: str | None = None,
        contact_email: str | None = None,
        license_name: str | None = None,
        license_url: str | None = None,
        servers: list[dict[str, str]] | None = None,
        include_examples: bool = True,
        include_schemas: bool = True,
        group_by_tags: bool = False,
        exclude_routes: list[str] | None = None,
        include_only_routes: list[str] | None = None,
    ):
        """Initialize documentation configuration."""
        self.title = title
        self.version = version
        self.description = description
        self.contact_name = contact_name
        self.contact_email = contact_email
        self.license_name = license_name
        self.license_url = license_url
        self.servers = servers or [
            {'url': 'http://localhost:8000', 'description': 'Development server'}
        ]
        self.include_examples = include_examples
        self.include_schemas = include_schemas
        self.group_by_tags = group_by_tags
        # Default to excluding /docs
        self.exclude_routes = set(exclude_routes or ['/docs']) 
        self.include_only_routes = (
            set(include_only_routes or []) if include_only_routes else None
        )


class DocumentationGenerator:
    """Main documentation generator class."""

    def __init__(self, app: Velithon, config: DocumentationConfig | None = None):
        """Initialize the documentation generator."""
        self.app = app
        self.config = config or DocumentationConfig()
        self.routes_info: list[RouteInfo] = []

    def _python_type_to_api_type(self, annotation: Any) -> str:
        """Convert Python type annotation to API-friendly type string."""
        if annotation is None or annotation is type(None):
            return 'null'

        # Handle Annotated types - extract the actual type
        origin = get_origin(annotation)
        if origin is Annotated:
            args = get_args(annotation)
            if args:
                annotation = args[0]
                origin = get_origin(annotation)

        # Map common Python types to API types
        type_mappings = {
            str: 'string',
            int: 'integer',
            float: 'number',
            bool: 'boolean',
            bytes: 'string',
            list: 'array',
            dict: 'object',
        }

        # Get the type name
        if hasattr(annotation, '__name__'):
            type_name = annotation.__name__
        elif hasattr(annotation, '_name'):
            type_name = annotation._name
        else:
            type_name = str(annotation)

        # Handle special type mappings by name
        name_mappings = {
            'UploadFile': 'file',
            'Request': 'request',
            'Response': 'response',
            'HTTPException': 'error',
            'datetime': 'string (datetime)',
            'date': 'string (date)',
            'time': 'string (time)',
            'UUID': 'string (uuid)',
            'Decimal': 'number (decimal)',
            'Path': 'string (path)',
            'AnyUrl': 'string (url)',
            'EmailStr': 'string (email)',
            'Json': 'object (json)',
            'UserStatus': 'string (enum)',
            'Priority': 'string (enum)',
            'NoneType': 'null',
        }

        # Check for special types by name (exact matches and specific patterns)
        for pattern, api_type in name_mappings.items():
            # Special handling for exact matches or specific patterns
            if pattern == 'Request' and type_name == 'Request':
                return api_type
            elif pattern == 'Response' and type_name == 'Response':
                return api_type
            elif pattern in ['UploadFile', 'HTTPException'] and pattern in type_name:
                return api_type
            elif (
                pattern
                in ['datetime', 'UUID', 'Decimal', 'Path', 'AnyUrl', 'EmailStr', 'Json']
                and pattern.lower() in type_name.lower()
            ):
                return api_type
            elif pattern == 'date' and (
                type_name == 'date' or type_name.endswith('.date')
            ):
                return api_type
            elif pattern == 'time' and (
                type_name == 'time' or type_name.endswith('.time')
            ):
                return api_type
            elif pattern == 'NoneType' and type_name == 'NoneType':
                return api_type

        # Check direct mappings
        if annotation in type_mappings:
            return type_mappings[annotation]

        # Check by name for built-in types
        if type_name in type_mappings:
            return type_mappings[type_name]

        args = get_args(annotation)

        # Handle Union types (including Optional)
        is_union = origin is Union or str(type(annotation)).startswith(
            "<class 'types.UnionType'>"
        )
        if is_union:
            if len(args) == 2 and type(None) in args:
                # Optional type
                non_none_type = next(arg for arg in args if arg is not type(None))
                base_type = self._python_type_to_api_type(non_none_type)
                return f'{base_type} (optional)'
            else:
                types = [self._python_type_to_api_type(arg) for arg in args if args]
                if not types:
                    # Fallback for complex union types
                    return 'string (union)'
                return f'one of: {", ".join(types)}'

        # Handle list/array types
        elif origin is list or 'list' in type_name.lower():
            if args:
                item_type = self._python_type_to_api_type(args[0])
                return f'array of {item_type}'
            return 'array'

        # Handle dict/object types
        elif origin is dict or 'dict' in type_name.lower():
            if len(args) >= 2:
                key_type = self._python_type_to_api_type(args[0])
                value_type = self._python_type_to_api_type(args[1])
                return f'object with {key_type} keys and {value_type} values'
            return 'object'

        # Check if it's a Pydantic model
        if self._is_pydantic_model(annotation):
            return f'object ({type_name})'

        # Handle enums
        if hasattr(annotation, '__members__'):
            return f'string (enum: {type_name})'

        # For other generic types
        if origin and args:
            arg_types = [self._python_type_to_api_type(arg) for arg in args]
            return f'{origin.__name__} of {", ".join(arg_types)}'
        elif origin:
            return origin.__name__.lower()

        # Default mappings for common patterns
        if 'id' in type_name.lower():
            return 'integer'
        elif 'name' in type_name.lower() or 'text' in type_name.lower():
            return 'string'
        elif 'count' in type_name.lower() or 'size' in type_name.lower():
            return 'integer'
        elif 'price' in type_name.lower() or 'amount' in type_name.lower():
            return 'number'

        # Default fallback
        return type_name.lower() if type_name else 'unknown'

    def _get_type_string(self, annotation: Any) -> str:
        """Convert type annotation to readable string."""
        if annotation is None or annotation is type(None):
            return 'None'

        # Handle Annotated types
        origin = get_origin(annotation)
        if origin is Annotated:
            args = get_args(annotation)
            if args:
                # Return the actual type (first argument of Annotated)
                return self._get_type_string(args[0])

        if hasattr(annotation, '__name__'):
            return annotation.__name__

        args = get_args(annotation)

        if origin is Union:
            if len(args) == 2 and type(None) in args:
                # Optional type - use modern syntax
                non_none_type = next(arg for arg in args if arg is not type(None))
                return f'{self._get_type_string(non_none_type)} | None'
            else:
                return f'Union[{", ".join(self._get_type_string(arg) for arg in args)}]'
        elif origin is list:
            if args:
                return f'list[{self._get_type_string(args[0])}]'
            return 'list'
        elif origin is dict:
            if len(args) >= 2:
                return f'dict[{self._get_type_string(args[0])}, {self._get_type_string(args[1])}]'
            return 'dict'
        elif origin:
            if args:
                return f'{origin.__name__}[{", ".join(self._get_type_string(arg) for arg in args)}]'
            return origin.__name__

        return str(annotation)

    def _is_pydantic_model(self, annotation: Any) -> bool:
        """Check if annotation is a Pydantic model."""
        if not PYDANTIC_AVAILABLE or BaseModel is None:
            return False

        try:
            # Check if it's a BaseModel class
            return inspect.isclass(annotation) and issubclass(annotation, BaseModel)
        except (TypeError, AttributeError):
            return False

    def _extract_pydantic_fields(self, model_class: Any) -> list[dict[str, Any]]:
        """Extract field information from a Pydantic model."""
        if not self._is_pydantic_model(model_class):
            return []

        fields_info = []
        try:
            # Get model fields using Pydantic v2 API
            if hasattr(model_class, 'model_fields'):
                model_fields = model_class.model_fields
                for field_name, field_info in model_fields.items():
                    field_data = {
                        'name': field_name,
                        'type': self._python_type_to_api_type(field_info.annotation),
                        'required': field_info.is_required(),
                        'default': getattr(field_info, 'default', None),
                        'description': getattr(field_info, 'description', None),
                    }
                    fields_info.append(field_data)
            # Fallback for Pydantic v1
            elif hasattr(model_class, '__fields__'):
                for field_name, field_info in model_class.__fields__.items():
                    field_data = {
                        'name': field_name,
                        'type': self._python_type_to_api_type(field_info.type_),
                        'required': field_info.required,
                        'default': field_info.default,
                        'description': getattr(
                            field_info.field_info, 'description', None
                        ),
                    }
                    fields_info.append(field_data)
        except Exception:
            # If we can't extract fields, return empty list
            pass

        return fields_info

    def _extract_parameter_info(
        self, func: Any, route_path: str = ''
    ) -> list[ParameterInfo]:
        """Extract parameter information from function signature with Pydantic support."""
        parameters = []

        if not inspect.isfunction(func) and not inspect.ismethod(func):
            return parameters

        sig = inspect.signature(func)

        for param_name, param in sig.parameters.items():
            # Skip 'self' and 'request' parameters
            if param_name in ('self', 'request'):
                continue

            annotation = (
                param.annotation if param.annotation != inspect.Parameter.empty else Any
            )

            # Extract type and constraints from Annotated types
            actual_type, constraints = self._extract_annotated_info(annotation)

            # Default parameter info
            param_info = ParameterInfo(
                name=param_name,
                type_annotation=self._python_type_to_api_type(actual_type),
                param_type='query',  # default
                required=param.default == inspect.Parameter.empty,
                default_value=param.default
                if param.default != inspect.Parameter.empty
                else None,
            )

            # Add constraint information to description
            constraint_text = self._format_constraints(constraints)
            base_description = constraints.get('description', '')

            if constraint_text and base_description:
                param_info.description = f'{base_description} ({constraint_text})'
            elif constraint_text:
                param_info.description = f'Constraints: {constraint_text}'
            elif base_description:
                param_info.description = base_description

            # Check for parameter constraints in default value
            if param.default != inspect.Parameter.empty:
                # Check most specific classes first (File -> Form -> Body inheritance)
                if isinstance(param.default, Path):
                    param_info.param_type = 'path'
                    param_info.description = getattr(param.default, 'description', None)
                elif isinstance(param.default, Query):
                    param_info.param_type = 'query'
                    param_info.description = getattr(param.default, 'description', None)
                elif isinstance(param.default, Header):
                    param_info.param_type = 'header'
                    param_info.description = getattr(param.default, 'description', None)
                elif isinstance(param.default, Cookie):
                    param_info.param_type = 'cookie'
                    param_info.description = getattr(param.default, 'description', None)
                elif isinstance(param.default, File):
                    param_info.param_type = 'file'
                    param_info.description = getattr(param.default, 'description', None)
                elif isinstance(param.default, Form):
                    param_info.param_type = 'form'
                    param_info.description = getattr(param.default, 'description', None)
                elif isinstance(param.default, Body):
                    param_info.param_type = 'body'
                    param_info.description = getattr(param.default, 'description', None)

            # Check for parameter constraints in Annotated metadata
            if get_origin(param.annotation) is Annotated:
                args = get_args(param.annotation)
                for metadata in args[1:]:
                    if isinstance(
                        metadata, Path | Query | Body | Header | Cookie | Form | File
                    ):
                        if isinstance(metadata, Path):
                            param_info.param_type = 'path'
                        elif isinstance(metadata, Query):
                            param_info.param_type = 'query'
                        elif isinstance(metadata, Header):
                            param_info.param_type = 'header'
                        elif isinstance(metadata, Cookie):
                            param_info.param_type = 'cookie'
                        elif isinstance(metadata, File):
                            param_info.param_type = 'file'
                        elif isinstance(metadata, Form):
                            param_info.param_type = 'form'
                        elif isinstance(metadata, Body):
                            param_info.param_type = 'body'

                        # Override description from annotation if available
                        if hasattr(metadata, 'description') and metadata.description:
                            param_info.description = metadata.description
                        break

            # Special handling for Pydantic models
            if self._is_pydantic_model(actual_type):
                # Infer location: body for complex models, query for simple cases
                if param_info.param_type == 'query':  # Not explicitly set
                    param_info.param_type = 'body'

                # Extract detailed field information
                model_fields = self._extract_pydantic_fields(actual_type)

                if model_fields:
                    # Create detailed description
                    type_name = (
                        actual_type.__name__
                        if hasattr(actual_type, '__name__')
                        else str(actual_type)
                    )
                    field_descriptions = []

                    for field in model_fields:
                        field_desc = f'- **{field["name"]}** ({field["type"]})'
                        if field['required']:
                            field_desc += ' *required*'
                        if field['description']:
                            field_desc += f': {field["description"]}'
                        field_descriptions.append(field_desc)

                    detailed_description = (
                        f'**{type_name} model with fields:**\n'
                        + '\n'.join(field_descriptions)
                    )

                    # For Pydantic models, create a clean table description and detailed description
                    if (
                        param_info.description
                        and param_info.description != detailed_description
                    ):
                        # Keep the custom description as table description, store detailed as extra
                        table_description = param_info.description
                        param_info.detailed_description = detailed_description
                    else:
                        # Use a clean summary for the table
                        table_description = f'{type_name} model (see details below)'
                        param_info.detailed_description = detailed_description

                    param_info.description = table_description
                    # Keep the API-friendly type annotation that was already set

            # Infer path parameter
            elif f'{{{param_name}}}' in route_path:
                param_info.param_type = 'path'

            parameters.append(param_info)

        return parameters

    def _extract_docstring_info(
        self, func: Any
    ) -> tuple[str, str, list[dict[str, str]]]:
        """Extract summary, description and parameter docs from docstring."""
        if not func or not hasattr(func, '__doc__') or not func.__doc__:
            return '', '', []

        docstring = inspect.getdoc(func)
        if not docstring:
            return '', '', []

        lines = docstring.strip().split('\n')
        summary = lines[0] if lines else ''

        # Find description (everything before Args/Parameters section)
        description_lines = []
        param_docs = []

        current_section = 'description'

        for line in lines[1:]:
            line = line.strip()

            if line.lower().startswith(
                ('args:', 'arguments:', 'parameters:', 'param:')
            ):
                current_section = 'params'
                continue
            elif line.lower().startswith(('returns:', 'return:')):
                current_section = 'returns'
                continue
            elif line.lower().startswith(
                ('raises:', 'raise:', 'examples:', 'example:')
            ):
                current_section = 'other'
                continue

            if current_section == 'description' and line:
                description_lines.append(line)
            elif current_section == 'params' and line:
                # Parse parameter documentation
                param_match = re.match(r'(\w+):\s*(.*)', line)
                if param_match:
                    param_name, param_desc = param_match.groups()
                    param_docs.append({'name': param_name, 'description': param_desc})

        description = '\n'.join(description_lines).strip()

        return summary, description, param_docs

    def _extract_response_info(self, func: Any) -> list[ResponseInfo]:
        """Extract response information from function."""
        responses = []

        # Default successful response
        responses.append(
            ResponseInfo(
                status_code=200,
                description='Successful response',
                content_type='application/json',
            )
        )

        # Try to extract from docstring
        if hasattr(func, '__doc__') and func.__doc__:
            docstring = func.__doc__.lower()

            # Look for common error responses mentioned in docstring
            if '404' in docstring or 'not found' in docstring:
                responses.append(
                    ResponseInfo(status_code=404, description='Resource not found')
                )

            if '400' in docstring or 'bad request' in docstring:
                responses.append(
                    ResponseInfo(status_code=400, description='Bad request')
                )

            if '401' in docstring or 'unauthorized' in docstring:
                responses.append(
                    ResponseInfo(status_code=401, description='Unauthorized')
                )

            if '403' in docstring or 'forbidden' in docstring:
                responses.append(ResponseInfo(status_code=403, description='Forbidden'))

            if '500' in docstring or 'internal server error' in docstring:
                responses.append(
                    ResponseInfo(status_code=500, description='Internal server error')
                )

        return responses

    def _should_include_route(self, route_path: str, route_name: str) -> bool:
        """Determine if route should be included in documentation."""
        # Check exclude list
        if (
            route_path in self.config.exclude_routes
            or route_name in self.config.exclude_routes
        ):
            return False

        # Check include only list
        if self.config.include_only_routes:
            return (
                route_path in self.config.include_only_routes
                or route_name in self.config.include_only_routes
            )

        return True

    def _extract_route_info(self, route: Route) -> RouteInfo:
        """Extract comprehensive information from a route."""
        endpoint = route.endpoint

        # Extract basic info
        summary, description, param_docs = self._extract_docstring_info(endpoint)
        parameters = self._extract_parameter_info(endpoint, route.path)
        responses = self._extract_response_info(endpoint)

        # Merge parameter documentation
        param_docs_dict = {doc['name']: doc['description'] for doc in param_docs}
        for param in parameters:
            if param.name in param_docs_dict and not param.description:
                param.description = param_docs_dict[param.name]

        # Create route info
        route_info = RouteInfo(
            path=route.path,
            methods=route.methods,
            summary=summary or f'{endpoint.__name__} endpoint',
            description=description,
            parameters=parameters,
            responses=responses,
            tags=[],  # TODO: Extract from decorators or function metadata
            endpoint_function=endpoint,
        )

        return route_info

    def collect_routes_info(self) -> list[RouteInfo]:
        """Collect information from all routes in the application."""
        routes_info = []

        def extract_from_routes(routes):
            for route in routes:
                if hasattr(route, 'endpoint') and route.endpoint:
                    route_name = getattr(
                        route.endpoint, '__name__', str(route.endpoint)
                    )
                    if self._should_include_route(route.path, route_name):
                        route_info = self._extract_route_info(route)
                        routes_info.append(route_info)
                elif hasattr(route, 'routes'):
                    # Recursively extract from nested routers
                    extract_from_routes(route.routes)

        # Extract from main router
        if hasattr(self.app, 'router') and hasattr(self.app.router, 'routes'):
            extract_from_routes(self.app.router.routes)
        elif hasattr(self.app, 'routes'):
            extract_from_routes(self.app.routes)

        self.routes_info = routes_info
        return routes_info

    def generate_markdown(self) -> str:
        """Generate comprehensive Markdown documentation."""
        if not MARKDOWN_AVAILABLE:
            raise ImportError(
                'Markdown and Jinja2 are required for Markdown generation. '
                'Please install with: pip install markdown jinja2'
            )

        if not self.routes_info:
            self.collect_routes_info()

        # Markdown template
        template = Environment(loader=DictLoader({'main': MARKDOWN_TEMPLATE}))

        # Group routes by tags if configured
        grouped_routes = {}
        if self.config.group_by_tags:
            for route in self.routes_info:
                tags = route.tags if route.tags else ['Untagged']
                for tag in tags:
                    if tag not in grouped_routes:
                        grouped_routes[tag] = []
                    grouped_routes[tag].append(route)
        else:
            grouped_routes['All Routes'] = self.routes_info

        # Render template
        content = template.get_template('main').render(
            config=self.config,
            grouped_routes=grouped_routes,
            routes=self.routes_info,
            generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )

        return content

    def generate_pdf(self, markdown_content: str | None = None) -> bytes:
        """Generate PDF documentation from Markdown content."""
        if not WEASYPRINT_AVAILABLE:
            raise ImportError(
                'WeasyPrint is required for PDF generation. '
                'Please install with: pip install weasyprint'
            )

        if not MARKDOWN_AVAILABLE:
            raise ImportError(
                'Markdown is required for PDF generation. '
                'Please install with: pip install markdown jinja2'
            )

        if markdown_content is None:
            markdown_content = self.generate_markdown()

        # Convert Markdown to HTML
        md = markdown.Markdown(
            extensions=['tables', 'toc', 'codehilite', 'fenced_code']
        )
        html_content = md.convert(markdown_content)

        # HTML template with CSS styling
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{self.config.title}</title>
            <style>
                {PDF_CSS_STYLES}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        # Generate PDF
        pdf_bytes = weasyprint.HTML(string=html_template).write_pdf()
        return pdf_bytes

    def export_markdown(self, file_path: str | PathLibPath) -> None:
        """Export documentation as Markdown file."""
        content = self.generate_markdown()
        PathLibPath(file_path).write_text(content, encoding='utf-8')

    def export_pdf(self, file_path: str | PathLibPath) -> None:
        """Export documentation as PDF file."""
        content = self.generate_pdf()
        PathLibPath(file_path).write_bytes(content)

    def _extract_annotated_info(self, annotation: Any) -> tuple[Any, dict[str, Any]]:
        """Extract type and metadata from Annotated types."""
        constraints = {}
        actual_type = annotation

        origin = get_origin(annotation)
        if origin is Annotated:
            args = get_args(annotation)
            if args:
                actual_type = args[0]
                # Extract constraints from metadata
                for metadata in args[1:]:
                    if hasattr(metadata, '__dict__'):
                        # Extract common constraint attributes
                        for attr in [
                            'description',
                            'ge',
                            'le',
                            'gt',
                            'lt',
                            'min_length',
                            'max_length',
                            'pattern',
                            'regex',
                        ]:
                            if hasattr(metadata, attr):
                                value = getattr(metadata, attr)
                                if value is not None:
                                    constraints[attr] = value
                    elif isinstance(metadata, str):
                        # String metadata could be description
                        if 'description' not in constraints:
                            constraints['description'] = metadata

        return actual_type, constraints

    def _format_constraints(self, constraints: dict[str, Any]) -> str:
        """Format parameter constraints into readable text."""
        if not constraints:
            return ''

        parts = []
        if 'ge' in constraints:
            parts.append(f'≥ {constraints["ge"]}')
        if 'le' in constraints:
            parts.append(f'≤ {constraints["le"]}')
        if 'gt' in constraints:
            parts.append(f'> {constraints["gt"]}')
        if 'lt' in constraints:
            parts.append(f'< {constraints["lt"]}')
        if 'min_length' in constraints:
            parts.append(f'min length: {constraints["min_length"]}')
        if 'max_length' in constraints:
            parts.append(f'max length: {constraints["max_length"]}')
        if 'pattern' in constraints:
            parts.append(f'pattern: {constraints["pattern"]}')
        if 'regex' in constraints:
            parts.append(f'regex: {constraints["regex"]}')

        return ' | '.join(parts) if parts else ''


# Markdown template for documentation generation
MARKDOWN_TEMPLATE = """
# {{ config.title }}

**Version:** {{ config.version }}
**Generated:** {{ generation_time }}

{{ config.description }}

{% if config.contact_name or config.contact_email %}

## Contact Information

{% if config.contact_name %}**Contact:** {{ config.contact_name }}{% endif %}
{% if config.contact_email %}**Email:** {{ config.contact_email }}{% endif %}
{% endif %}

{% if config.license_name %}

## License

**License:** {{ config.license_name }}{% if config.license_url %} - [{{ config.license_url }}]({{ config.license_url }}){% endif %}
{% endif %}

{% if config.servers %}

## Servers

{% for server in config.servers %}
- **{{ server.description }}:** `{{ server.url }}`
{% endfor %}
{% endif %}

## API Endpoints

{% for tag, routes in grouped_routes.items() %}

### {{ tag }}

{% for route in routes %}

#### {{ route.methods|join(', ') }} {{ route.path }}

**Summary:** {{ route.summary }}

{% if route.description %}
**Description:**
{{ route.description }}
{% endif %}

{% if route.parameters %}

**Parameters:**

| Name | Type | Location | Required | Description |
|------|------|----------|----------|-------------|
{% for param in route.parameters %}| {{ param.name }} | {{ param.type_annotation }} | {{ param.param_type }} | {{ 'Yes' if param.required else 'No' }} | {{ param.description or 'N/A' }} |
{% endfor %}

{% for param in route.parameters %}
{% if param.detailed_description %}

{{ param.detailed_description }}

{% endif %}
{% endfor %}
{% endif %}

**Responses:**

{% for response in route.responses %}
- **{{ response.status_code }}**: {{ response.description }}
{% endfor %}

---

{% endfor %}
{% endfor %}

## Generated by Velithon Documentation Generator
"""

# CSS styles for PDF generation
PDF_CSS_STYLES = """
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
}

h1, h2, h3, h4, h5, h6 {
    color: #2c3e50;
    margin-top: 2rem;
    margin-bottom: 1rem;
}

h1 {
    border-bottom: 3px solid #3498db;
    padding-bottom: 0.5rem;
}

h2 {
    border-bottom: 1px solid #bdc3c7;
    padding-bottom: 0.3rem;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1rem 0;
}

th, td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}

th {
    background-color: #f2f2f2;
    font-weight: bold;
}

code {
    background-color: #f8f9fa;
    padding: 0.2rem 0.4rem;
    border-radius: 3px;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

pre {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 5px;
    overflow-x: auto;
}

.endpoint {
    margin: 2rem 0;
    padding: 1rem;
    border-left: 4px solid #3498db;
    background-color: #f8f9fa;
}
"""
