import time
import logging
from velithon.logging import TextFormatter, JsonFormatter

def run_benchmark(iterations=100000):
    """Run manual benchmark for logging formatters"""
    print(f"Running benchmark with {iterations} iterations")
    
    # Create test records
    text_record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    text_record.request_id = "1234"
    text_record.method = "GET"
    text_record.path = "/test"
    text_record.client_ip = "127.0.0.1"
    text_record.user_agent = "test-agent"
    text_record.duration_ms = 1.234
    text_record.status = 200
    
    json_record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    json_record.request_id = "1234" 
    json_record.method = "GET"
    json_record.path = "/test"
    json_record.client_ip = "127.0.0.1"
    json_record.user_agent = "test-agent"
    json_record.duration_ms = 1.234
    json_record.status = 200
    json_record.query_params = {"test": "value"}
    json_record.headers = {"User-Agent": "test-agent"}
    
    # Benchmark TextFormatter
    text_formatter = TextFormatter()
    start = time.time()
    for _ in range(iterations):
        text_formatter.format(text_record)
    end = time.time()
    text_time = (end - start) * 1000
    text_per_op = text_time / iterations
    
    # Benchmark JsonFormatter
    json_formatter = JsonFormatter()
    start = time.time()
    for _ in range(iterations):
        json_formatter.format(json_record)
    end = time.time()
    json_time = (end - start) * 1000
    json_per_op = json_time / iterations
    
    # Print results
    print(f"\n----- Benchmark Results ({iterations} iterations) -----")
    print(f"TextFormatter: {text_time:.2f}ms total, {text_per_op:.6f}ms per operation")
    print(f"JsonFormatter: {json_time:.2f}ms total, {json_per_op:.6f}ms per operation")
    print("------------------------------------------------\n")

if __name__ == "__main__":
    # Run with different iteration counts to see performance at scale
    run_benchmark(10000)
    run_benchmark(50000)