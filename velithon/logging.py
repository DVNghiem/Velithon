import logging
import os
import sys
import zipfile
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

import orjson


class VelithonFilter(logging.Filter):
    def filter(self, record):
        return record.name.startswith("velithon")


class TextFormatter(logging.Formatter):
    EXTRA_FIELDS = frozenset([
        "request_id",
        "method",
        "path",
        "client_ip",
        "user_agent",
        "duration_ms",
        "status",
    ])
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._time_fmt = "%Y-%m-%d %H:%M:%S"
        
    def format(self, record):
        """Format log records with custom formatting."""
        asctime = self.formatTime(record, self._time_fmt)
        
        msg = f"{asctime}.{int(record.msecs):03d} | {record.levelname:<8} | {record.name}:{record.lineno} - {record.getMessage()}"

        # check if any of the extra fields are present in the record
        # and only then create the extra_parts list
        has_extra = any(hasattr(record, field) for field in self.EXTRA_FIELDS)
        if has_extra:
            # create a list of extra fields to include in the log message
            extra_parts = []
            for field in self.EXTRA_FIELDS:
                if hasattr(record, field):
                    value = getattr(record, field)
                    if value is not None:
                        extra_parts.append(f"{field}={value}")
            
            # Only include extra_parts if they are not empty
            if extra_parts:
                msg = f"{msg} | {', '.join(extra_parts)}"
                
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
        return orjson.dumps(log_entry).decode("utf-8")


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

    logger = logging.getLogger("velithon")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = True

    # disable all logging from the velithon package
    for name in ["", "granian", "granian.access"]:
        velithon_logger = logging.getLogger(name)
        velithon_logger.handlers.clear()
        velithon_logger.propagate = False
        velithon_logger.setLevel(logging.CRITICAL + 1)

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
    logger.addHandler(console_handler)

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
