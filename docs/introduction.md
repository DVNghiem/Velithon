# Introduction

Velithon is a lightweight, high-performance, asynchronous web framework for Python built on top of the RSGI protocol and powered by [Granian](https://github.com/emmett-framework/granian). It provides a simple yet powerful way to build web applications with features like Dependency Injection (DI), input handling, middleware, and lifecycle management.

## Key Features

- **High Performance**: Optimized for speed with Granian and RSGI, delivering ~110,000-115,000 req/s
- **Dependency Injection (DI)**: Seamless DI with `Provide` and `inject` for managing dependencies
- **Input Handling**: Robust handling of path and query parameters
- **File Uploads**: Comprehensive file upload and form parsing with configurable limits
- **Background Tasks**: Execute tasks asynchronously after response with concurrency control
- **WebSocket Support**: Full WebSocket support with connection management and routing integration
- **Middleware**: Built-in middleware for logging, CORS, compression, sessions, and custom middleware support
- **Session Support**: Multiple session backends (memory, signed cookies) with secure HMAC signing
- **Lifecycle Management**: Application startup and shutdown hooks
- **Command Line Interface**: Flexible CLI for running applications
- **OpenAPI Support**: Automatic API documentation generation
