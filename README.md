# Velithon

Velithon is a lightweight, high-performance, asynchronous web framework for Python, built on top of the RSGI protocol and powered by [Granian](https://github.com/emmett-framework/granian). It provides a simple yet powerful way to build web applications with features like Dependency Injection (DI), input handling, middleware, and lifecycle management (startup/shutdown). Velithon is designed for ultra-high performance.

## Features

- **Ultra-High Performance**: Optimized for maximum speed with advanced JSON processing and memory optimizations.
- **Dependency Injection (DI)**: Seamless DI with `Provide` and `inject` for managing dependencies.
- **Input Handling**: Robust handling of path and query parameters.
- **WebSocket Support**: Full WebSocket support with connection management, routing integration, and lifecycle hooks.
- **Middleware**: Built-in middleware for logging (`LoggingMiddleware`), CORS (`CORSMiddleware`), compression (`CompressionMiddleware`), and DI (`DIMiddleware`).
- **Lifecycle Management**: Application startup and shutdown hooks for initialization and cleanup.
- **Command Line Interface**: Flexible CLI for running applications with customizable options.

## Installation

### Prerequisites

- Python 3.12 or higher
- `pip` for installing dependencies

### Install Velithon

   ```bash
   pip3 install velithon
   ```

## Command Line Interface (CLI)

Velithon provides a powerful CLI for running applications with customizable options. The CLI is implemented using `click` and supports a wide range of configurations for Granian, logging, and SSL.

### Run the Application with CLI

Use the `velithon run` command to start your application. Below is an example using the sample app in `examples/`:

```bash
velithon run --app examples.main:app --host 0.0.0.0 --port 8080 --workers 4 --log-level DEBUG --log-to-file --log-file app.log
```

### CLI Options

- `--app`: Application module and instance (format: `module:app_instance`). Default: `simple_app:app`.
- `--host`: Host to bind. Default: `127.0.0.1`.
- `--port`: Port to bind. Default: `8000`.
- `--workers`: Number of worker processes. Default: `1`.
- `--log-file`: Log file path. Default: `velithon.log`.
- `--log-level`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). Default: `INFO`.
- `--log-format`: Log format (`text`, `json`). Default: `text`.
- `--log-to-file`: Enable logging to file.
- `--max-bytes`: Max bytes for log file rotation. Default: `10MB`.
- `--backup-count`: Number of backup log files (days). Default: `7`.
- `--blocking-threads`: Number of blocking threads. Default: `None`.
- `--blocking-threads-idle-timeout`: Idle timeout for blocking threads. Default: `30`.
- `--runtime-threads`: Number of runtime threads. Default: `1`.
- `--runtime-blocking-threads`: Number of blocking threads for runtime. Default: `None`.
- `--runtime-mode`: Runtime mode (`st` for single-threaded, `mt` for multi-threaded). Default: `st`.
- `--loop`: Event loop (`auto`, `asyncio`, `uvloop`, `rloop`). Default: `auto`.
- `--task-impl`: Task implementation (`asyncio`, `rust`). Note: `rust` only supported in Python <= 3.12. Default: `asyncio`.
- `--http`: HTTP mode (`auto`, `1`, `2`). Default: `auto`.
- `--http1-buffer-size`: Max buffer size for HTTP/1 connections. Default: Granian default.
- `--http1-header-read-timeout`: Timeout (ms) to read headers. Default: Granian default.
- `--http1-keep-alive/--no-http1-keep-alive`: Enable/disable HTTP/1 keep-alive. Default: Granian default.
- `--http1-pipeline-flush/--no-http1-pipeline-flush`: Aggregate HTTP/1 flushes (experimental). Default: Granian default.
- `--http2-adaptive-window/--no-http2-adaptive-window`: Use adaptive flow control for HTTP2. Default: Granian default.
- `--http2-initial-connection-window-size`: Max connection-level flow control for HTTP2. Default: Granian default.
- `--http2-initial-stream-window-size`: Stream-level flow control for HTTP2. Default: Granian default.
- `--http2-keep-alive-interval`: Interval (ms) for HTTP2 Ping frames. Default: Granian default.
- `--http2-keep-alive-timeout`: Timeout (s) for HTTP2 keep-alive ping. Default: Granian default.
- `--http2-max-concurrent-streams`: Max concurrent streams for HTTP2. Default: Granian default.
- `--http2-max-frame-size`: Max frame size for HTTP2. Default: Granian default.
- `--http2-max-headers-size`: Max size of received header frames. Default: Granian default.
- `--http2-max-send-buffer-size`: Max write buffer size for HTTP/2 streams. Default: Granian default.
- `--ssl-certificate`: Path to SSL certificate file.
- `--ssl-keyfile`: Path to SSL key file.
- `--ssl-keyfile-password`: SSL key password.
- `--backpressure`: Max concurrent requests per worker. Default: `None`.
- `--reload`: Enable auto-reload for development.

### Example CLI Commands

- Run with SSL and JSON logging:

  ```bash
  velithon run --app examples.main:app --ssl-certificate cert.pem --ssl-keyfile key.pem --log-format json --log-to-file
  ```

- Run with auto-reload for development:

  ```bash
  velithon run --app examples.main:app --reload --log-level DEBUG
  ```

- Run with 4 workers and HTTP/2:

  ```bash
  velithon run --app examples.main:app --workers 4 --http 2
  ```

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/YourFeature`).
3. Commit your changes (`git commit -m "Add YourFeature"`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Open a Pull Request.

## License

Velithon is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Contact

For questions or feedback, please open an issue on the [GitHub repository](https://github.com/DVNghiem/Velithon).