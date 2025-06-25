# Background Tasks

Background tasks allow you to execute functions after returning a response to the client. This is useful for operations like sending emails, processing uploads, or logging.

**🚀 Performance Note**: Velithon uses a high-performance Rust implementation for background tasks, providing improved speed and memory efficiency over pure Python implementations.

## Basic Background Task

```python
from velithon import Velithon
from velithon.background import BackgroundTask

app = Velithon()

def send_email(email: str, message: str):
    # Simulate email sending
    print(f"Sending email to {email}: {message}")

@app.post("/send-notification")
async def send_notification(email: str, message: str):
    # Create and add background task
    task = BackgroundTask(send_email, email, message)
    
    # Return response immediately
    return {"message": "Notification queued"}
```

## Multiple Background Tasks

```python
from velithon.background import BackgroundTasks

def log_action(action: str, user_id: int):
    print(f"User {user_id} performed: {action}")

def update_analytics(action: str):
    print(f"Analytics updated for: {action}")

@app.post("/user-action")
async def user_action(action: str, user_id: int):
    # Create background tasks collection
    background_tasks = BackgroundTasks()
    
    # Add multiple tasks
    background_tasks.add_task(log_action, action, user_id)
    background_tasks.add_task(update_analytics, action)
    
    # Execute all tasks in background
    await background_tasks()
    
    return {"message": "Action completed"}
```

## Async Background Tasks

```python
import asyncio

async def async_process_data(data: dict):
    await asyncio.sleep(1)  # Simulate async work
    print(f"Processed data: {data}")

@app.post("/process")
async def process_data(data: dict):
    # Background tasks work with both sync and async functions
    task = BackgroundTask(async_process_data, data)
    
    return {"message": "Processing started"}
```

## Background Tasks with Response

You can include background tasks directly in responses:

```python
from velithon.responses import JSONResponse

@app.post("/order")
async def create_order(order_data: dict):
    # Create the order
    order_id = "12345"
    
    # Prepare background tasks
    background_tasks = BackgroundTasks()
    background_tasks.add_task(send_order_confirmation, order_data["email"], order_id)
    background_tasks.add_task(update_inventory, order_data["items"])
    
    # Return response with background tasks
    return JSONResponse(
        content={"order_id": order_id, "status": "created"},
        background=background_tasks
    )
```

## Concurrent Background Tasks

Control how many background tasks run concurrently:

```python
@app.post("/batch-process")
async def batch_process(items: list):
    # Limit concurrent tasks to avoid overwhelming resources
    background_tasks = BackgroundTasks(max_concurrent=5)
    
    for item in items:
        background_tasks.add_task(process_item, item)
    
    # Execute with concurrency control
    await background_tasks()
    
    return {"message": f"Processing {len(items)} items"}
```

## Error Handling in Background Tasks

```python
def risky_task(data: str):
    if not data:
        raise ValueError("Data cannot be empty")
    print(f"Processing: {data}")

@app.post("/risky-operation")
async def risky_operation(data: str):
    background_tasks = BackgroundTasks()
    background_tasks.add_task(risky_task, data)
    
    # Control error behavior
    try:
        await background_tasks(continue_on_error=False)  # Stop on first error
    except RuntimeError as e:
        return {"error": "Background task failed"}
    
    return {"message": "Operation completed"}
```

## Performance Benefits

Velithon's background task implementation is powered by Rust, providing:

- **Improved Speed**: Up to 10% faster execution compared to pure Python implementations
- **Memory Efficiency**: Lower memory overhead through Rust's zero-cost abstractions
- **Better Concurrency**: Efficient task scheduling using Tokio's async runtime
- **Type Safety**: Compile-time guarantees for task management operations

### Benchmarking Results

```python
# Example performance test showing Rust vs Python implementation
import time
from velithon.background import BackgroundTasks

async def performance_test():
    tasks = BackgroundTasks(max_concurrent=5)
    
    # Add 100 lightweight tasks
    for i in range(100):
        tasks.add_task(lambda x: time.sleep(0.001), i)
    
    start = time.time()
    await tasks.run_all()
    duration = time.time() - start
    
    print(f"Completed 100 tasks in {duration:.3f}s")
```

## Background Task Best Practices

1. **Keep tasks lightweight**: Background tasks should be quick operations
2. **Handle errors gracefully**: Always consider what happens if a task fails
3. **Use for non-critical operations**: Don't rely on background tasks for essential functionality
4. **Monitor resource usage**: Limit concurrent tasks to prevent system overload
5. **Consider task queues**: For complex workflows, use dedicated task queues like Celery
