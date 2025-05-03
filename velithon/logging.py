import logging
import os
import sys
import zipfile
from datetime import datetime, timezone
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from queue import SimpleQueue

import orjson


class VelithonFilter(logging.Filter):
    def filter(self, record):
        return record.name.startswith("velithon")


class TextFormatter(logging.Formatter):
    def format(self, record):
        """Format log records with custom formatting.

        This method formats log records with a standardized format that includes:
        - Timestamp with millisecond precision (YYYY-MM-DD HH:MM:SS.mmm)
        - Log level with fixed width (8 characters, left-aligned)
        - Logger name and line number
        - Log message
        - Optional HTTP request fields when present (request_id, method, path, etc.)

        Extra HTTP request fields that will be included when available:
        - request_id: Unique identifier for the request
        - method: HTTP method (GET, POST, etc.)
        - path: Request path
        - client_ip: Client's IP address
        - query_params: URL query parameters
        - headers: HTTP headers
        - duration_ms: Request processing duration in milliseconds
        - status: HTTP response status code

        Returns:
            str: The formatted log message
        """
        asctime = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        microsecond = record.msecs / 1000
        asctime = f"{asctime}.{int(microsecond * 1000):03d}"
        msg = f"{asctime} | {record.levelname:<8} | {record.name}:{record.lineno} - {record.getMessage()}"

        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k
            in [
                "request_id",
                "method",
                "path",
                "client_ip",
                "query_params",
                "headers",
                "duration_ms",
                "status",
                "response_headers",
            ]
        }
        if extra_fields:
            extra_str = ", ".join(f"{k}={str(v)}" for k, v in extra_fields.items())
            if extra_str:
                msg += f" | {extra_str}"
        return msg

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.name,
            "line": record.lineno,
        }
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k
            in [
                "request_id",
                "method",
                "path",
                "client_ip",
                "query_params",
                "headers",
                "duration_ms",
                "status",
                "response_headers",
            ]
        }
        log_entry.update(extra_fields)
        return orjson.dumps(log_entry, option=orjson.OPT_SERIALIZE_NUMPY).decode(
            "utf-8"
        )


class ZipRotatingFileHandler(RotatingFileHandler):
    """
    A subclass of RotatingFileHandler that compresses log files during rotation.

    This handler inherits from the RotatingFileHandler and extends it by automatically 
    compressing rotated log files into zip format. After each rotation, log files are 
    stored as zip files, which helps save disk space.

    Notes
    -----
    When rotation occurs, each backup file is compressed individually into a zip file
    with the naming pattern: baseFilename.N.zip
    After compression, the original uncompressed file is removed.
    """
    def doRollover(self):
        super().doRollover()
        for i in range(self.backupCount - 1, 0, -1):
            src = f"{self.baseFilename}.{i}"
            dst = f"{self.baseFilename}.{i}.zip"
            if os.path.exists(src):
                with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.write(src, os.path.basename(src))
                os.remove(src)


def configure_logger(
    log_file: str = "velithon.log",
    level: str = "INFO",
    format_type: str = "text",
    log_to_file: bool = False,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 7,
):
    level = getattr(logging, level, logging.INFO)

    log_queue = SimpleQueue()

    logger = logging.getLogger("velithon")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    # remove all handlers from the root logger
    root_logger = logging.getLogger("")
    root_logger.handlers.clear()
    root_logger.setLevel(logging.CRITICAL + 1)  # prevent root logger from logging

    # remove all handlers from the granian logger
    granian_logger = logging.getLogger("granian")
    granian_logger.handlers.clear()
    granian_logger.propagate = False
    granian_logger.setLevel(logging.CRITICAL + 1)

    # remove all handlers from the granian.access logger
    granian_access_logger = logging.getLogger("granian.access")
    granian_access_logger.handlers.clear()
    granian_access_logger.propagate = False
    granian_access_logger.setLevel(logging.CRITICAL + 1)

    # Formatter
    text_formatter = TextFormatter()
    json_formatter = JsonFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.addFilter(VelithonFilter())
    console_handler.setFormatter(
        text_formatter if format_type == "text" else json_formatter
    )

    # File handler
    if log_to_file:
        file_handler = ZipRotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setLevel(level)
        file_handler.addFilter(VelithonFilter())
        file_handler.setFormatter(json_formatter)
    else:
        file_handler = None

    # Custom queue handler
    queue_handler = QueueHandler(log_queue)
    logger.addHandler(queue_handler)

    # Queue listener
    handlers = [console_handler]
    if file_handler:
        handlers.append(file_handler)
    listener = QueueListener(log_queue, *handlers, respect_handler_level=True)
    listener.start()
