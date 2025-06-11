import inspect
import logging

from velithon._velithon import (
    configure_logger as rust_configure_logger,
)
from velithon._velithon import (
    is_enabled_for as rust_is_enabled_for,
)
from velithon._velithon import (
    log_critical as rust_log_critical,
)
from velithon._velithon import (
    log_critical_with_extra as rust_log_critical_with_extra,
)
from velithon._velithon import (
    log_debug as rust_log_debug,
)
from velithon._velithon import (
    log_debug_with_extra as rust_log_debug_with_extra,
)
from velithon._velithon import (
    log_error as rust_log_error,
)
from velithon._velithon import (
    log_error_with_extra as rust_log_error_with_extra,
)
from velithon._velithon import (
    log_info as rust_log_info,
)
from velithon._velithon import (
    log_info_with_extra as rust_log_info_with_extra,
)
from velithon._velithon import (
    log_warn as rust_log_warn,
)
from velithon._velithon import (
    log_warn_with_extra as rust_log_warn_with_extra,
)


class RustLoggingHandler(logging.Handler):
    """
    Python logging Handler that forwards log records to the Rust logging implementation.
    This allows standard Python logging calls to use the high-performance Rust backend.
    """
    
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        
    def emit(self, record):
        """Process a logging record and forward it to Rust."""
        try:
            # Format the message
            if record.args:
                msg = record.getMessage()
            else:
                msg = record.msg
                
            # Get caller info
            module = getattr(record, 'name', 'python')
            line = getattr(record, 'lineno', 0)
            
            # Extract extra fields for structured logging
            extra_fields = {}
            if hasattr(record, '__dict__'):
                extra_fields = {k: v for k, v in record.__dict__.items() 
                              if k not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                                         'pathname', 'filename', 'module', 'lineno', 'funcName',
                                         'created', 'msecs', 'relativeCreated', 'thread', 
                                         'threadName', 'processName', 'process', 'getMessage',
                                         'exc_info', 'exc_text', 'stack_info']}
            
            # Convert extra fields to string dict for Rust compatibility
            extra_str_dict = {k: str(v) for k, v in extra_fields.items()} if extra_fields else {}
            
            # Map Python log levels to our Rust functions
            if record.levelno >= logging.CRITICAL:
                if extra_str_dict:
                    rust_log_critical_with_extra(str(msg), module, line, extra_str_dict)
                else:
                    rust_log_critical(str(msg), module, line)
            elif record.levelno >= logging.ERROR:
                if extra_str_dict:
                    rust_log_error_with_extra(str(msg), module, line, extra_str_dict)
                else:
                    rust_log_error(str(msg), module, line)
            elif record.levelno >= logging.WARNING:
                if extra_str_dict:
                    rust_log_warn_with_extra(str(msg), module, line, extra_str_dict)
                else:
                    rust_log_warn(str(msg), module, line)
            elif record.levelno >= logging.INFO:
                if extra_str_dict:
                    rust_log_info_with_extra(str(msg), module, line, extra_str_dict)
                else:
                    rust_log_info(str(msg), module, line)
            else:  # DEBUG level
                if extra_str_dict:
                    rust_log_debug_with_extra(str(msg), module, line, extra_str_dict)
                else:
                    rust_log_debug(str(msg), module, line)
                
        except Exception as e:
            # Fallback to stderr if logging fails
            import sys
            print(f"Rust logging error: {e}", file=sys.stderr)


class RustLogger:
    """
    A Python wrapper around the Rust logging implementation.
    Provides compatibility with Python's logging interface while leveraging
    Rust's performance for the actual logging operations.
    """

    def __init__(self, name: str = "velithon"):
        self.name = name
        self._configured = False

    def configure(
        self,
        log_file: str = "velithon.log",
        level: str = "INFO",
        log_format: str = "text",
        log_to_file: bool = False,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 7,
    ) -> None:
        """Configure the Rust logger with the specified parameters."""
        rust_configure_logger(
            log_file if log_to_file else None,
            level,
            log_format,
            log_to_file,
            max_bytes,
            backup_count,
        )
        self._configured = True

    def _get_caller_info(self) -> tuple[str, int]:
        """Get the module name and line number of the caller."""
        frame = inspect.currentframe()
        try:
            # Go up the stack to find the actual caller
            caller_frame = frame.f_back.f_back
            module = caller_frame.f_globals.get("__name__", "unknown")
            line = caller_frame.f_lineno
            return module, line
        finally:
            del frame

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log a debug message."""
        if args:
            msg = msg % args
        module, line = self._get_caller_info()
        rust_log_debug(msg, module, line)

    def info(self, msg: str, *args, **kwargs) -> None:
        """Log an info message."""
        if args:
            msg = msg % args
        module, line = self._get_caller_info()
        
        # Handle extra fields for structured logging
        extra = kwargs.get("extra", {})
        if extra:
            # Convert all values to strings for Rust compatibility
            extra_str = {k: str(v) for k, v in extra.items()}
            rust_log_info_with_extra(msg, module, line, extra_str)
        else:
            rust_log_info(msg, module, line)

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log a warning message."""
        if args:
            msg = msg % args
        module, line = self._get_caller_info()
        rust_log_warn(msg, module, line)

    def warn(self, msg: str, *args, **kwargs) -> None:
        """Alias for warning."""
        self.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        """Log an error message."""
        if args:
            msg = msg % args
        module, line = self._get_caller_info()
        rust_log_error(msg, module, line)

    def critical(self, msg: str, *args, **kwargs) -> None:
        """Log a critical message."""
        if args:
            msg = msg % args
        module, line = self._get_caller_info()
        rust_log_critical(msg, module, line)

    def isEnabledFor(self, level: int) -> bool:
        """Check if logging is enabled for the given level."""
        level_map = {
            10: "DEBUG",
            20: "INFO", 
            30: "WARNING",
            40: "ERROR",
            50: "CRITICAL",
        }
        level_str = level_map.get(level, "INFO")
        return rust_is_enabled_for(level_str)


# Global logger instance
_rust_logger = RustLogger()


def configure_logger(
    log_file: str = "velithon.log",
    level: str = "INFO",
    log_format: str = "text",
    log_to_file: bool = False,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 7,
) -> None:
    """
    Configure the Rust-based logger.
    
    Args:
        log_file: Path to the log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format for log messages ("text" or "json")
        log_to_file: Whether to log to file in addition to console
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    """
    # Configure the Rust logger backend
    _rust_logger.configure(
        log_file=log_file,
        level=level,
        log_format=log_format,
        log_to_file=log_to_file,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )
    
    # Set up Python logging to use our Rust handler
    root_logger = logging.getLogger()
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our Rust handler
    rust_handler = RustLoggingHandler()
    
    # Map string level to Python logging level
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    python_level = level_map.get(level.upper(), logging.INFO)
    
    root_logger.setLevel(python_level)
    rust_handler.setLevel(python_level)
    root_logger.addHandler(rust_handler)
    
    # Also configure the velithon logger specifically
    velithon_logger = logging.getLogger('velithon')
    velithon_logger.setLevel(python_level)
    # Clear existing handlers and add our Rust handler
    velithon_logger.handlers.clear()
    velithon_logger.addHandler(rust_handler)
    velithon_logger.propagate = False  # Don't propagate to root to avoid double logging


def get_logger(name: str = "velithon") -> RustLogger:
    """
    Get the configured Rust logger instance.
    
    Note: Currently returns the global logger instance regardless of name.
    The name parameter is kept for API compatibility but not used.
    """
    return _rust_logger



# Export the main functions and classes
__all__ = [
    "configure_logger",
    "get_logger", 
    "RustLogger",
]
