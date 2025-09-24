#!/usr/bin/env python3
"""
Example GraphQL server using Velithon framework.

This example demonstrates a complete GraphQL server implementation with:
- GraphQL schema and query execution
- GraphQL Playground interface
- Health check endpoints
- High-performance Rust backend
"""

from velithon import Velithon
from velithon.graphql import GraphQLSchema
from velithon.responses import HTMLResponse, JSONResponse


def create_app():
    """Create and configure the Velithon application."""
    app = Velithon()

    # Create GraphQL schema
    schema = GraphQLSchema()

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return JSONResponse({"status": "healthy", "service": "graphql-server"})

    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return JSONResponse({
            "name": "Velithon GraphQL Server",
            "version": "1.0.0",
            "endpoints": {
                "/graphql": "GraphQL API endpoint",
                "/playground": "GraphQL Playground (GET)",
                "/health": "Health check"
            }
        })

    @app.get("/playground")
    async def playground():
        """GraphQL Playground interface."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>GraphQL Playground</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <link
                rel="stylesheet"
                href="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.8/build/static/css/index.css"
            />
            <link
                rel="shortcut icon"
                href="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.8/build/favicon.png"
            />
        </head>
        <body>
            <div id="root"></div>
            <script
                src="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.8/build/static/js/middleware.js"
            ></script>
            <script>
                window.GraphQLPlayground.init(document.getElementById('root'), {
                    endpoint: '/graphql',
                    settings: {
                        'editor.theme': 'dark',
                        'editor.fontSize': 14,
                        'request.credentials': 'same-origin'
                    }
                });
            </script>
        </body>
        </html>
        """
        return HTMLResponse(html)

    @app.post("/graphql")
    async def graphql_endpoint(request):
        """GraphQL API endpoint."""
        try:
            # Parse request body
            content_type = request.headers.get("content-type", "").lower()
            
            if "application/json" not in content_type:
                return JSONResponse(
                    {"errors": [{"message": "Content-Type must be application/json"}]}, 
                    status_code=400
                )

            body = await request.json()
            
            if isinstance(body, list):
                # Batch query
                responses = schema.execute_batch(body)
                return JSONResponse([resp.to_dict() for resp in responses])
            else:
                # Single query
                query = body.get("query", "")
                variables = body.get("variables")
                operation_name = body.get("operationName")
                
                response = schema.execute(query, variables, operation_name)
                return JSONResponse(response.to_dict())
                
        except Exception as e:
            return JSONResponse(
                {"errors": [{"message": f"Server error: {e!s}"}]}, 
                status_code=500
            )

    return app


def main():
    """Run the GraphQL server."""
    try:
        print("🚀 Starting Velithon GraphQL Server...")
        print("📊 Server Info:")
        print("   - GraphQL API: http://localhost:8000/graphql")
        print("   - GraphQL Playground: http://localhost:8000/playground")
        print("   - Health Check: http://localhost:8000/health")
        print("   - API Info: http://localhost:8000/")
        print()
        print("💡 Try these sample queries in the playground:")
        print('   query { hello }')
        print('   query { hello(name: "World") }')
        print('   query { serverTime }')
        print('   query { hello serverTime }')
        print()
        
        # Use Granian server (comes with Velithon)
        import granian
        
        server = granian.Granian(
            target="__main__:create_app",
            interface='rsgi',
            address="0.0.0.0",
            port=8000,
            workers=1,
        )
        
        server.serve()
        
    except KeyboardInterrupt:
        print("\n👋 GraphQL Server stopped gracefully")
    except Exception as e:
        print(f"❌ Server error: {e}")


if __name__ == "__main__":
    main()