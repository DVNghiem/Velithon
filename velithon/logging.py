import logging
import os
import sys
import zipfile
from datetime import datetime
from logging.handlers import RotatingFileHandler

import orjson


class VelithonFilter(logging.Filter):
    """Optimized filter that only allows velithon package logs."""
    
    def __init__(self):
        super().__init__()
        # Cache the prefix for faster string comparison
        self._velithon_prefix = "velithon"
    
    def filter(self, record):
        # Use startswith with cached prefix for better performance
        return record.name.startswith(self._velithon_prefix)


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
        # Pre-compute format string for better performance
        self._base_format = "{asctime}.{msecs:03d} | {levelname:<8} | {name}:{lineno} - {message}"
        
    def format(self, record):
        """Format log records with optimized performance."""
        # Use faster time formatting
        asctime = datetime.fromtimestamp(record.created).strftime(self._time_fmt)
        
        # Build base message with format string (faster than f-strings for this case)
        msg = self._base_format.format(
            asctime=asctime,
            msecs=int(record.msecs),
            levelname=record.levelname,
            name=record.name,
            lineno=record.lineno,
            message=record.getMessage()
        )

        # Fast path: only build extra parts if we have extra fields
        extra_parts = []
        for field in self.EXTRA_FIELDS:
            if hasattr(record, field):
                value = getattr(record, field)
                if value is not None:
                    extra_parts.append(f"{field}={value}")

        if extra_parts:
            msg = f"{msg} | {', '.join(extra_parts)}"
                
        return msg


class JsonFormatter(logging.Formatter):
    # Pre-define the set of extra fields for faster lookup
    EXTRA_FIELDS = frozenset([
        "request_id",
        "method",
        "path",
        "client_ip",
        "query_params",
        "headers",
        "duration_ms",
        "status",
        "response_headers",
    ])
    
    def format(self, record):
        # Use faster datetime formatting without timezone conversion for performance
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        log_entry = {
            "timestamp": timestamp,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.name,
            "line": record.lineno,
        }
        
        # Optimized extra fields extraction - only check known fields
        for field in self.EXTRA_FIELDS:
            if hasattr(record, field):
                value = getattr(record, field)
                if value is not None:
                    log_entry[field] = value
        
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

    # disable all logging from other packages for performance
    for name in ["", "granian", "granian.access"]:
        other_logger = logging.getLogger(name)
        other_logger.handlers.clear()
        other_logger.propagate = False
        other_logger.setLevel(logging.CRITICAL + 1)

    # Create filter once and reuse
    velithon_filter = VelithonFilter()

    # Only create the formatter we need
    if format_type == "text":
        formatter = TextFormatter()
    else:
        formatter = JsonFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.addFilter(velithon_filter)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler - always use JSON for files for consistency
    if log_to_file:
        file_formatter = JsonFormatter() if format_type == "text" else formatter
        file_handler = ZipRotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setLevel(level)
        file_handler.addFilter(velithon_filter)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
