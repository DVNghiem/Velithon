import logging
import time
import pytest
from velithon.logging import TextFormatter, JsonFormatter, configure_logger


@pytest.mark.benchmark
def test_text_formatter_performance():
    """Test the performance of the TextFormatter."""
    formatter = TextFormatter()
    
    # Create a mock record
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.request_id = "1234"
    record.method = "GET"
    record.path = "/test"
    record.client_ip = "127.0.0.1"
    record.user_agent = "test-agent"
    record.duration_ms = 1.234
    record.status = 200
    
    # Measure performance
    iterations = 10000
    start = time.time()
    for _ in range(iterations):
        formatter.format(record)
    end = time.time()
    
    ms_per_format = (end - start) * 1000 / iterations
    print(f"TextFormatter: {ms_per_format:.6f} ms per format call")
    
    # Performance assertion
    assert ms_per_format < 0.1  # Allow up to 0.1ms per format call


@pytest.mark.benchmark
def test_json_formatter_performance():
    """Test the performance of the JsonFormatter."""
    formatter = JsonFormatter()
    
    # Create a mock record
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.request_id = "1234"
    record.method = "GET"
    record.path = "/test"
    record.client_ip = "127.0.0.1"
    record.user_agent = "test-agent"
    record.duration_ms = 1.234
    record.status = 200
    record.query_params = {"test": "value"}
    record.headers = {"User-Agent": "test-agent"}
    
    # Measure performance
    iterations = 10000
    start = time.time()
    for _ in range(iterations):
        formatter.format(record)
    end = time.time()
    
    ms_per_format = (end - start) * 1000 / iterations
    print(f"JsonFormatter: {ms_per_format:.6f} ms per format call")
    
    # Performance assertion
    assert ms_per_format < 0.2  # Allow up to 0.2ms per format call
