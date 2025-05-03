import logging
import pathlib

import click
import granian
import granian.http

from velithon.logging import configure_logger

logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Velithon CLI - A lightweight RSGI-based web framework."""
    pass


@cli.command()
@click.option(
    "--app",
    default="simple_app:app",
    help="Application module and instance (format: module:app_instance).",
)
@click.option("--host", default="127.0.0.1", help="Host to bind.")
@click.option("--port", default=8000, type=int, help="Port to bind.")
@click.option("--workers", default=1, type=int, help="Number of worker processes.")
@click.option("--log_file", default="velithon.log", help="Log file path.")
@click.option(
    "--log_level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Logging level.",
)
@click.option(
    "--log_format",
    default="text",
    type=click.Choice(["text", "json"]),
    help="Log format.",
)
@click.option("--log_to_file", is_flag=True, help="Enable logging to file.")
@click.option(
    "--max_bytes",
    default=10 * 1024 * 1024,
    type=int,
    help="Max bytes for log file rotation.",
)
@click.option("--backup_count", default=7, type=int, help="Number of backup log files. (days)")
@click.option(
    "--blocking_threads", default=None, type=int, help="Number of blocking threads."
)
@click.option(
    "--blocking_threads_idle_timeout",
    default=30,
    type=int,
    help="Idle timeout for blocking threads.",
)
@click.option(
    "--runtime_threads", default=1, type=int, help="Number of runtime threads."
)
@click.option(
    "--runtime_blocking_threads",
    default=None,
    type=int,
    help="Number of blocking threads for runtime.",
)
@click.option(
    "--runtime_mode",
    default="st",
    type=click.Choice(["st", "mt"]),
    help="Runtime mode (single-threaded or multi-threaded).",
)
@click.option(
    "--loop",
    default="auto",
    type=click.Choice(["auto", "asyncio", "uvloop", "rloop"]),
    help="Event loop to use.",
)
@click.option(
    "--task_impl",
    default="asyncio",
    type=click.Choice(["asyncio", "rust"]),
    help="Task implementation to use. **Note**: `rust` is only support in python <= 3.12",
)
@click.option(
    "--http",
    default="auto",
    type=click.Choice(["auto", "1", "2"]),
    help="HTTP mode to use.",
)
@click.option(
    "--http1-buffer-size",
    type=click.IntRange(8192),
    default=granian.http.HTTP1Settings.max_buffer_size,
    help="Sets the maximum buffer size for HTTP/1 connections",
)
@click.option(
    "--http1-header-read-timeout",
    type=click.IntRange(1, 60_000),
    default=granian.http.HTTP1Settings.header_read_timeout,
    help="Sets a timeout (in milliseconds) to read headers",
)
@click.option(
    "--http1-keep-alive/--no-http1-keep-alive",
    default=granian.http.HTTP1Settings.keep_alive,
    help="Enables or disables HTTP/1 keep-alive",
)
@click.option(
    "--http1-pipeline-flush/--no-http1-pipeline-flush",
    default=granian.http.HTTP1Settings.pipeline_flush,
    help="Aggregates HTTP/1 flushes to better support pipelined responses (experimental)",
)
@click.option(
    "--http2-adaptive-window/--no-http2-adaptive-window",
    default=granian.http.HTTP2Settings.adaptive_window,
    help="Sets whether to use an adaptive flow control for HTTP2",
)
@click.option(
    "--http2-initial-connection-window-size",
    type=click.IntRange(1024),
    default=granian.http.HTTP2Settings.initial_connection_window_size,
    help="Sets the max connection-level flow control for HTTP2",
)
@click.option(
    "--http2-initial-stream-window-size",
    type=click.IntRange(1024),
    default=granian.http.HTTP2Settings.initial_stream_window_size,
    help="Sets the `SETTINGS_INITIAL_WINDOW_SIZE` option for HTTP2 stream-level flow control",
)
@click.option(
    "--http2-keep-alive-interval",
    type=click.IntRange(1, 60_000),
    default=granian.http.HTTP2Settings.keep_alive_interval,
    help="Sets an interval (in milliseconds) for HTTP2 Ping frames should be sent to keep a connection alive",
)
@click.option(
    "--http2-keep-alive-timeout",
    type=click.IntRange(1),
    default=granian.http.HTTP2Settings.keep_alive_timeout,
    help="Sets a timeout (in seconds) for receiving an acknowledgement of the HTTP2 keep-alive ping",
)
@click.option(
    "--http2-max-concurrent-streams",
    type=click.IntRange(10),
    default=granian.http.HTTP2Settings.max_concurrent_streams,
    help="Sets the SETTINGS_MAX_CONCURRENT_STREAMS option for HTTP2 connections",
)
@click.option(
    "--http2-max-frame-size",
    type=click.IntRange(1024),
    default=granian.http.HTTP2Settings.max_frame_size,
    help="Sets the maximum frame size to use for HTTP2",
)
@click.option(
    "--http2-max-headers-size",
    type=click.IntRange(1),
    default=granian.http.HTTP2Settings.max_headers_size,
    help="Sets the max size of received header frames",
)
@click.option(
    "--http2-max-send-buffer-size",
    type=click.IntRange(1024),
    default=granian.http.HTTP2Settings.max_send_buffer_size,
    help="Set the maximum write buffer size for each HTTP/2 stream",
)
@click.option(
    "--ssl-certificate",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        path_type=pathlib.Path,
    ),
    help="SSL certificate file",
)
@click.option(
    "--ssl-keyfile",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        path_type=pathlib.Path,
    ),
    help="SSL key file",
)
@click.option("--ssl-keyfile-password", help="SSL key password")
@click.option(
    "--backpressure",
    default=None,
    type=int,
    help=" Maximum number of requests to process concurrently (per worker)",
)
@click.option("--reload", is_flag=True, help="Enable auto-reload for development.")
def run(
    app,
    host,
    port,
    workers,
    log_file,
    log_level,
    log_format,
    log_to_file,
    max_bytes,
    backup_count,
    reload,
    blocking_threads,
    blocking_threads_idle_timeout,
    runtime_threads,
    runtime_blocking_threads,
    runtime_mode,
    loop,
    task_impl,
    http,
    http1_buffer_size,
    http1_header_read_timeout,
    http1_keep_alive,
    http1_pipeline_flush,
    http2_adaptive_window,
    http2_initial_connection_window_size,
    http2_initial_stream_window_size,
    http2_keep_alive_interval,
    http2_keep_alive_timeout,
    http2_max_concurrent_streams,
    http2_max_frame_size,
    http2_max_headers_size,
    http2_max_send_buffer_size,
    ssl_certificate,
    ssl_keyfile,
    ssl_keyfile_password,
    backpressure,
):
    """Run the Velithon application."""
    try:
        configure_logger(
            log_file=log_file,
            level=log_level,
            format_type=log_format,
            log_to_file=log_to_file,
            max_bytes=max_bytes,
            backup_count=backup_count,
        )
        # Configure Granian server
        server = granian.Granian(
            target=app,  # Velithon application instance
            address=host,
            port=port,
            interface="rsgi",  # Use RSGI interface
            workers=workers,
            reload=reload,
            log_enabled=False,
            blocking_threads=blocking_threads,
            blocking_threads_idle_timeout=blocking_threads_idle_timeout,
            runtime_threads=runtime_threads,
            runtime_blocking_threads=runtime_blocking_threads,
            runtime_mode=runtime_mode,
            loop=loop,
            task_impl=task_impl,
            http=http,
            ssl_cert=ssl_certificate,
            ssl_key=ssl_keyfile,
            ssl_key_password=ssl_keyfile_password,
            backpressure=backpressure,
            http1_settings=granian.http.HTTP1Settings(
                header_read_timeout=http1_header_read_timeout,
                keep_alive=http1_keep_alive,
                max_buffer_size=http1_buffer_size,
                pipeline_flush=http1_pipeline_flush,
            ),
            http2_settings=granian.http.HTTP2Settings(
                adaptive_window=http2_adaptive_window,
                initial_connection_window_size=http2_initial_connection_window_size,
                initial_stream_window_size=http2_initial_stream_window_size,
                keep_alive_interval=http2_keep_alive_interval,
                keep_alive_timeout=http2_keep_alive_timeout,
                max_concurrent_streams=http2_max_concurrent_streams,
                max_frame_size=http2_max_frame_size,
                max_headers_size=http2_max_headers_size,
                max_send_buffer_size=http2_max_send_buffer_size,
            ),
        )
        # check log level is debug then log all the parameters
        if log_level == "DEBUG":
            logger.debug(
                f"\n App: {app} \n Host: {host} \n Port: {port} \n Workers: {workers} \n "
                f"Log File: {log_file} \n Log Level: {log_level} \n Log Format: {log_format} \n "
                f"Log to File: {log_to_file} \n Max Bytes: {max_bytes} \n Backup Count: {backup_count} \n "
                f"Blocking Threads: {blocking_threads} \n Blocking Threads Idle Timeout: {blocking_threads_idle_timeout} \n "
                f"Runtime Threads: {runtime_threads} \n Runtime Blocking Threads: {runtime_blocking_threads} \n "
                f"Runtime Mode: {runtime_mode} \n Loop: {loop} \n Task Impl: {task_impl} \n "
                f"HTTP: {http} \n HTTP1 Buffer Size: {http1_buffer_size} \n "
                f"HTTP1 Header Read Timeout: {http1_header_read_timeout} \n "
                f"HTTP1 Keep Alive: {http1_keep_alive} \n HTTP1 Pipeline Flush: {http1_pipeline_flush} \n "
                f"HTTP2 Adaptive Window: {http2_adaptive_window} \n "
                f"HTTP2 Initial Connection Window Size: {http2_initial_connection_window_size} \n "
                f"HTTP2 Initial Stream Window Size: {http2_initial_stream_window_size} \n "
                f"HTTP2 Keep Alive Interval: {http2_keep_alive_interval} \n "
                f"HTTP2 Keep Alive Timeout: {http2_keep_alive_timeout} \n "
                f"HTTP2 Max Concurrent Streams: {http2_max_concurrent_streams} \n "
                f"HTTP2 Max Frame Size: {http2_max_frame_size} \n "
                f"HTTP2 Max Headers Size: {http2_max_headers_size} \n "
                f"HTTP2 Max Send Buffer Size: {http2_max_send_buffer_size} \n "
                "SSL Certificate: {ssl_certificate} \n SSL Keyfile: {ssl_keyfile} \n "
                f"SSL Keyfile Password: {'*' * len(ssl_keyfile_password) if ssl_keyfile_password else None} \n "
                f"Backpressure: {backpressure}"
            )

        logger.info(
            f"Starting Velithon server at http://{host}:{port} with {workers} workers..."
        )
        if reload:
            logger.debug("Auto-reload enabled.")

        # Run the server
        server.serve()
    except ValueError as e:
        logging.error(f"Error: {str(e)}", err=True)
    except Exception as e:
        logging.error(f"Failed to start server: {str(e)}", err=True)


if __name__ == "__main__":
    cli()
