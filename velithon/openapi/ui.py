"""OpenAPI UI components for Velithon framework.

This module provides Swagger UI and ReDoc UI integration for displaying
interactive OpenAPI documentation in web browsers.
"""

from typing import Any

import orjson

from velithon.responses import HTMLResponse

swagger_ui_default_parameters = {
    'dom_id': '#swagger-ui',
    'layout': 'BaseLayout',
    'deepLinking': True,
    'showExtensions': True,
    'showCommonExtensions': True,
}


def get_swagger_ui_html(
    *,
    openapi_url: str,
    title: str,
    swagger_js_url: str = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js',
    swagger_css_url: str = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css',
    swagger_favicon_url: str = 'https://res.cloudinary.com/dslpmba3s/image/upload/v1746254848/logo_wgobg2.svg',
    oauth2_redirect_url: str | None = None,
    init_oauth: dict[str, Any] | None = None,
) -> HTMLResponse:
    """
    Generate an HTMLResponse containing the Swagger UI for interactive OpenAPI documentation.

    Parameters
    ----------
    openapi_url : str
        The URL to the OpenAPI schema.
    title : str
        The title for the Swagger UI page.
    swagger_js_url : str, optional
        The URL to the Swagger UI JavaScript bundle.
    swagger_css_url : str, optional
        The URL to the Swagger UI CSS file.
    swagger_favicon_url : str, optional
        The URL to the favicon for the Swagger UI page.
    oauth2_redirect_url : str | None, optional
        The OAuth2 redirect URL for authentication flows.
    init_oauth : dict[str, Any] | None, optional
        Initialization parameters for OAuth2.

    Returns
    -------
    HTMLResponse
        An HTMLResponse object containing the Swagger UI HTML.

    """  # noqa: E501
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link type="text/css" rel="stylesheet" href="{swagger_css_url}">
    <link rel="shortcut icon" href="{swagger_favicon_url}">
    <title>{title}</title>
    </head>
    <body>
    <div id="swagger-ui">
    </div>
    <script src="{swagger_js_url}"></script>
    <!-- `SwaggerUIBundle` is now available on the page -->
    <script>
    const ui = SwaggerUIBundle({{
        url: '{openapi_url}',
    """
    for key, value in swagger_ui_default_parameters.items():
        html += f'{orjson.dumps(key).decode()}: {orjson.dumps(value).decode()},\n'

    if oauth2_redirect_url:
        html += f"oauth2RedirectUrl: window.location.origin + '{oauth2_redirect_url}',"

    html += """
    presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
    })"""

    if init_oauth:
        html += f"""
        ui.initOAuth({orjson.dumps(init_oauth).decode()})
        """

    html += """
    </script>
    </body>
    </html>
    """
    return HTMLResponse(html)
