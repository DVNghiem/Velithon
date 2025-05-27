import logging
import os
import sys
import zipfile
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
import threading
import orjson
import queue
import time


class VelithonFilter(logging.Filter):
    def filter(self, record):
        return record.name.startswith("velithon")
    
class LocalQueueHandler(QueueHandler):

    def emit(self, record):
        return super().emit(record)

class ThreadTrace(threading.Thread): 
    def __init__(self, *args, **keywords): 
        threading.Thread.__init__(self, *args, **keywords) 

    def run(self):
        try:
            time.sleep(0.1)
        except Exception as e:
            logging.error(f"Error in thread run loop: {e}")
        super().run()

    def join(self, timeout = None):
        return super().join(timeout)

class LocalQueueListener(QueueListener):

    def dequeue(self, block):
        return self.queue.get(block)
    def start(self):
        self._thread = t = ThreadTrace(target=self._monitor)
        t.daemon = True
        t.start()
    def stop(self):
        super().stop()
    def _monitor(self):
        q = self.queue
        has_task_done = hasattr(q, 'task_done')
        while True:
            try:
                record = self.dequeue(True)
                if record is self._sentinel:
                    if has_task_done:
                        q.task_done()
                    break
                self.handle(record)
                if has_task_done:
                    q.task_done()
            except queue.Empty:
                break
    def handle(self, record):
        super().handle(record)

class TextFormatter(logging.Formatter):
    EXTRA_FIELDS = frozenset([
        "request_id",
        "client_ip",
        "user_agent",
        "duration_ms",
        "status",
    ])
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._time_fmt = "%Y-%m-%d %H:%M:%S"
        self._cache = {}
        
    def format(self, record):
        """Format log records with custom formatting."""
        asctime = self.formatTime(record, self._time_fmt)
        
        msg = f"{asctime}.{int(record.msecs):03d} | {record.levelname:<8} | {record.name}:{record.lineno} - {record.getMessage()}"

        # Use record.__dict__ directly for faster attribute access
        # and cache the extra fields that exist in the record
        if record.name not in self._cache:
            self._cache[record.name] = [field for field in self.EXTRA_FIELDS if hasattr(record, field)]
        
        extra_fields = self._cache[record.name]
        if not extra_fields:
            return msg
            
        # Pre-allocate the extra parts for better performance
        extra_parts = []
        for field in extra_fields:
            value = getattr(record, field, None)
            if value is not None:
                extra_parts.append(f"{field}={value}")
                
        if extra_parts:
            msg = f"{msg} | {', '.join(extra_parts)}"
                
        return msg


class JsonFormatter(logging.Formatter):
    # Pre-define the fields we want to extract to avoid checking the whole __dict__
    EXTRA_FIELDS = [
        "request_id",
        "method",
        "client_ip",
        "duration_ms",
        "status",
        "user_agent",
    ]
    
    def __init__(self):
        super().__init__()
        self._cache = {}
    
    def format(self, record):
        # Base structure that's always included
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.name,
            "line": record.lineno,
        }
        
        # Cache which fields exist for each record name to avoid repeatedly checking
        if record.name not in self._cache:
            self._cache[record.name] = [field for field in self.EXTRA_FIELDS if hasattr(record, field)]
            
        # Add only the fields that exist in this record type
        for field in self._cache[record.name]:
            value = getattr(record, field, None)
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
    log_format: str = "text",
    log_to_file: bool = False,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 7,
):
    log_queue = queue.Queue(-1)  # No limit on queue size

    # Convert string level to numeric level once
    level_value = getattr(logging, level, logging.INFO)
    logger = logging.getLogger("velithon")
    # Configure the main logger
    logger.setLevel(level_value)
    logger.handlers.clear()
    
    # Only propagate if we're not at the root level
    logger.propagate = logger.name != ""

    # Disable unnecessary loggers
    for name in ["", "_granian", "granian.access"]:
        velithon_logger = logging.getLogger(name)
        velithon_logger.handlers.clear()
        velithon_logger.propagate = False
        # Set to critical+1 to effectively disable
        velithon_logger.setLevel(logging.CRITICAL + 1)

    # Create formatters - lazily instantiate based on log_format
    formatter = TextFormatter() if log_format == "text" else JsonFormatter()

    # queue handler for async logging
    queue_handler = LocalQueueHandler(log_queue)
    queue_handler.setLevel(level_value)
    logger.addHandler(queue_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level_value)
    console_handler.addFilter(VelithonFilter())
    console_handler.setFormatter(formatter)

    listener = LocalQueueListener(log_queue, console_handler)

    # File handler - only create if needed
    if log_to_file:
        file_handler = ZipRotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setLevel(level_value)
        file_handler.addFilter(VelithonFilter())
        # Always use JSON for file logging
        file_handler.setFormatter(JsonFormatter())
        logger.addHandler(file_handler)
        listener = QueueListener(
            log_queue, console_handler, file_handler
        )
        
    listener.start()

    import atexit

    # Ensure the listener is stopped on exit
    atexit.register(listener.stop)
