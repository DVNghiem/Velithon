"""GraphQL Playground HTML generator for Velithon.

This module provides functionality to serve GraphQL Playground,
an interactive GraphQL IDE for development and testing.
"""

from __future__ import annotations


class GraphQLPlayground:
    """GraphQL Playground integration for Velithon."""

    def __init__(
        self,
        endpoint_url: str = "/graphql",
        subscription_endpoint: str | None = None,
        title: str = "GraphQL Playground",
    ):
        """Initialize GraphQL Playground.

        Args:
            endpoint_url: The GraphQL endpoint URL
            subscription_endpoint: WebSocket endpoint for subscriptions
            title: Page title

        """
        self.endpoint_url = endpoint_url
        self.subscription_endpoint = subscription_endpoint
        self.title = title

    def create_html(self) -> str:
        """Create GraphQL Playground HTML.

        Returns:
            str: HTML content for GraphQL Playground

        """
        return get_playground_html(
            self.endpoint_url, self.subscription_endpoint, self.title
        )

    @staticmethod
    def create_html_static(
        endpoint_url: str = "/graphql",
        subscription_endpoint: str | None = None,
        title: str = "GraphQL Playground",
    ) -> str:
        """Create GraphQL Playground HTML (static method).

        Args:
            endpoint_url: The GraphQL endpoint URL
            subscription_endpoint: WebSocket endpoint for subscriptions
            title: Page title

        Returns:
            str: HTML content for GraphQL Playground

        """
        return get_playground_html(endpoint_url, subscription_endpoint, title)


def get_playground_html(
    endpoint_url: str = "/graphql",
    subscription_endpoint: str | None = None,
    title: str = "GraphQL Playground",
) -> str:
    """Generate HTML for GraphQL Playground.

    Args:
        endpoint_url: The GraphQL endpoint URL
        subscription_endpoint: WebSocket endpoint for subscriptions
        title: Page title

    Returns:
        str: HTML content for GraphQL Playground

    """
    subscription_config = ""
    if subscription_endpoint:
        subscription_config = f"""
        subscriptionEndpoint: '{subscription_endpoint}',
        """

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset=utf-8/>
  <meta name="viewport" content="user-scalable=no, initial-scale=1.0, \
minimum-scale=1.0, maximum-scale=1.0, minimal-ui">
  <title>{title}</title>
  <link rel="stylesheet" \
href="//cdn.jsdelivr.net/npm/graphql-playground-react/build/static/css/index.css" />
  <link rel="shortcut icon" \
href="//cdn.jsdelivr.net/npm/graphql-playground-react/build/favicon.png" />
  <script \
src="//cdn.jsdelivr.net/npm/graphql-playground-react/build/static/js/middleware.js">\
</script>
</head>
<body>
  <div id="root">
    <style>
      body {{
        background-color: rgb(23, 42, 58);
        font-family: Open Sans, sans-serif;
        height: 90vh;
      }}
      #root {{
        height: 100%;
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
      }}
      .loading {{
        font-size: 32px;
        font-weight: 200;
        color: rgba(255, 255, 255, .6);
        margin-left: 20px;
      }}
      img {{
        width: 78px;
        height: 78px;
      }}
      .title {{
        font-weight: 400;
      }}
    </style>
    <img src="//cdn.jsdelivr.net/npm/graphql-playground-react/build/logo.png" alt="">
    <div class="loading"> Loading
      <span class="title">GraphQL Playground</span>
    </div>
  </div>
  <script>window.addEventListener('load', function (event) {{
      GraphQLPlayground.init(document.getElementById('root'), {{
        endpoint: '{endpoint_url}',{subscription_config}
        settings: {{
          'general.betaUpdates': false,
          'editor.theme': 'dark',
          'editor.reuseHeaders': true,
          'tracing.hideTracingResponse': true,
          'editor.fontSize': 14,
        }}
      }})
    }})</script>
</body>
</html>"""
