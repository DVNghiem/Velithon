import importlib
import pathlib
import sys
import traceback
from typing import Any

import click
import granian
import granian.http

from velithon.logging import get_logger

logger = get_logger(__name__)

project_root = pathlib.Path.cwd()  # Use current working directory
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))  # Insert at the beginning to prioritize


class ImportFromStringError(Exception):
    pass


def import_from_string(import_str: Any) -> Any:
    if not isinstance(import_str, str):
        return import_str

    module_str, _, attrs_str = import_str.partition(":")
    if not module_str or not attrs_str:
        message = (
            'Import string "{import_str}" must be in format "<module>:<attribute>".'
        )
        raise ImportFromStringError(message.format(import_str=import_str))

    try:
        module = importlib.import_module(module_str)
    except ModuleNotFoundError as exc:
        if exc.name != module_str:
            raise exc from None
        message = 'Could not import module "{module_str}".'
        raise ImportFromStringError(message.format(module_str=module_str))

    instance = module
    try:
        for attr_str in attrs_str.split("."):
            instance = getattr(instance, attr_str)
    except AttributeError:
        message = 'Attribute "{attrs_str}" not found in module "{module_str}".'
        raise ImportFromStringError(
            message.format(attrs_str=attrs_str, module_str=module_str)
        )

    return instance


@click.group()
def cli() -> None:
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
@click.option("--log-file", default="velithon.log", help="Log file path.")
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Logging level.",
)
@click.option(
    "--log-format",
    default="text",
    type=click.Choice(["text", "json"]),
    help="Log format.",
)
@click.option("--log-to-file", is_flag=True, help="Enable logging to file.")
@click.option(
    "--max-bytes",
    default=10 * 1024 * 1024,
    type=int,
    help="Max bytes for log file rotation.",
)
@click.option(
    "--backup-count", default=7, type=int, help="Number of backup log files. (days)"
)
@click.option(
    "--blocking-threads", default=None, type=int, help="Number of blocking threads."
)
@click.option(
    "--blocking-threads-idle-timeout",
    default=30,
    type=int,
    help="Idle timeout for blocking threads.",
)
@click.option(
    "--runtime-threads", default=1, type=int, help="Number of runtime threads."
)
@click.option(
    "--runtime-blocking-threads",
    default=None,
    type=int,
    help="Number of blocking threads for runtime.",
)
@click.option(
    "--runtime-mode",
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
    "--task-impl",
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
@click.option(
    "--vsp-host",
    default="127.0.0.1",
    help="Host for the Velithon Server Protocol (VSP) server.",
)
@click.option(
    "--vsp-port",
    default=8001,
    type=int,
    help="Port for the Velithon Server Protocol (VSP) server.",
)
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
    vsp_host,
    vsp_port,
):
    """Run the Velithon application."""
    try:
        app_instance = import_from_string(app)
        print(f"Importing application from: {app}")
        if not callable(app_instance):
            raise ImportFromStringError(
                f"'{app}' is not a callable application instance."
            )
        print(f"Starting Velithon server with app: {app_instance}")
        app_instance._serve(
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
            vsp_host,
            vsp_port,
        )

    except ValueError as e:
        traceback.print_exc()
        logger.error(f"Error: {str(e)}")
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Failed to start server: {str(e)}")


if __name__ == "__main__":
    cli()
