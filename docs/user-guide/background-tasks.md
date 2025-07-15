# Background Tasks

Velithon provides powerful background task capabilities for running operations asynchronously without blocking the main request-response cycle.

> **Note:** In Velithon, background tasks are explicitly created and executed within route handlers, rather than being injected as route parameters. This design choice provides more control over task execution while maintaining high performance through Rust-powered implementation.

## Overview

Background tasks allow you to execute functions after returning a response to the client. This is useful for operations like sending emails, processing images, logging, cleanup tasks, or any time-consuming operations that don't need to complete before responding to the user.

## Basic Background Tasks

### Using BackgroundTasks

```python
from velithon import Velithon
from velithon.background import BackgroundTasks
from velithon.responses import JSONResponse
import logging

app = Velithon()

def send_email(to: str, subject: str, body: str):
    """Send an email - this will run in the background"""
    # Simulate email sending
    logging.info(f"Sending email to {to}: {subject}")
    # Your email sending logic here

def log_user_action(user_id: int, action: str):
    """Log user action to analytics"""
    logging.info(f"User {user_id} performed action: {action}")

@app.post("/users")
async def create_user(user_data: dict):
    # Create the user (main operation)
    user = create_new_user(user_data)
    
    # Create background tasks
    background_tasks = BackgroundTasks()
    
    # Add background tasks
    background_tasks.add_task(
        send_email,
        to=user_data["email"],
        subject="Welcome!",
        body=f"Welcome {user_data['name']}!"
    )
    
    background_tasks.add_task(
        log_user_action,
        user_id=user["id"],
        action="user_created"
    )
    
    # Execute tasks in background and return response immediately
    await background_tasks()
    return JSONResponse({
        "id": user["id"],
        "message": "User created successfully"
    })
```

### Multiple Background Tasks

```python
@app.post("/orders")
async def create_order(order_data: dict):
    # Process the order
    order = process_order(order_data)
    
    # Create and add multiple background tasks
    background_tasks = BackgroundTasks()
    background_tasks.add_task(send_order_confirmation, order["id"])
    background_tasks.add_task(update_inventory, order["items"])
    background_tasks.add_task(notify_warehouse, order)
    background_tasks.add_task(update_analytics, order["total"])
    
    # Execute background tasks
    await background_tasks()
    
    return JSONResponse({
        "order_id": order["id"],
        "status": "processing"
    })

def send_order_confirmation(order_id: int):
    """Send order confirmation email"""
    order = get_order(order_id)
    send_email(
        to=order["customer_email"],
        subject=f"Order #{order_id} Confirmed",
        body=f"Your order #{order_id} has been confirmed."
    )

def update_inventory(items: list):
    """Update product inventory"""
    for item in items:
        reduce_stock(item["product_id"], item["quantity"])

def notify_warehouse(order: dict):
    """Notify warehouse system"""
    warehouse_api.notify_new_order(order)

def update_analytics(total: float):
    """Update sales analytics"""
    analytics.record_sale(total)
```

## Task Scheduling

### Delayed Tasks

```python
from velithon.background import BackgroundScheduler
import asyncio
from datetime import datetime, timedelta

scheduler = BackgroundScheduler()

@app.post("/password-reset")
async def request_password_reset(email: str):
    # Generate reset token
    token = generate_reset_token(email)
    
    # Create background tasks for immediate email
    background_tasks = BackgroundTasks()
    background_tasks.add_task(
        send_password_reset_email,
        email=email,
        token=token
    )
    
    # Execute background tasks
    await background_tasks()
    
    # Schedule token cleanup after 1 hour
    scheduler.add_delayed_task(
        delete_reset_token,
        delay=timedelta(hours=1),
        token=token
    )
    
    return JSONResponse({
        "message": "Password reset email sent"
    })

def send_password_reset_email(email: str, token: str):
    """Send password reset email"""
    reset_url = f"https://example.com/reset?token={token}"
    send_email(
        to=email,
        subject="Password Reset Request",
        body=f"Reset your password: {reset_url}"
    )

def delete_reset_token(token: str):
    """Clean up expired reset token"""
    remove_token_from_database(token)
```

### Recurring Tasks

```python
from velithon.background import BackgroundScheduler
from datetime import timedelta

scheduler = BackgroundScheduler()

@app.on_event("startup")
async def setup_recurring_tasks():
    # Daily cleanup task
    scheduler.add_recurring_task(
        cleanup_old_logs,
        interval=timedelta(days=1),
        start_time=datetime.now().replace(hour=2, minute=0, second=0)
    )
    
    # Hourly analytics update
    scheduler.add_recurring_task(
        update_hourly_analytics,
        interval=timedelta(hours=1)
    )
    
    # Weekly backup
    scheduler.add_recurring_task(
        create_backup,
        interval=timedelta(weeks=1),
        start_time=datetime.now().replace(hour=3, minute=0, second=0)
    )

def cleanup_old_logs():
    """Clean up logs older than 30 days"""
    cutoff_date = datetime.now() - timedelta(days=30)
    delete_logs_before(cutoff_date)

def update_hourly_analytics():
    """Update analytics dashboard"""
    generate_hourly_report()

def create_backup():
    """Create database backup"""
    backup_database()
```

## Worker Pools

### Task Queue with Workers

```python
from velithon.background import TaskQueue, Worker
import asyncio
import json

# Create task queue
task_queue = TaskQueue(max_size=1000)

# Define worker functions
async def process_image(image_path: str, user_id: int):
    """Process uploaded image"""
    # Resize image
    resized_path = resize_image(image_path, (800, 600))
    
    # Generate thumbnail
    thumbnail_path = create_thumbnail(image_path, (200, 200))
    
    # Update database
    update_user_image(user_id, resized_path, thumbnail_path)
    
    # Clean up original
    os.remove(image_path)

async def send_bulk_email(email_list: list, subject: str, body: str):
    """Send email to multiple recipients"""
    for email in email_list:
        try:
            await send_email_async(email, subject, body)
            await asyncio.sleep(0.1)  # Rate limiting
        except Exception as e:
            logging.error(f"Failed to send email to {email}: {e}")

# Start workers
@app.on_event("startup")
async def start_workers():
    # Start 3 image processing workers
    for i in range(3):
        worker = Worker(task_queue, f"image_worker_{i}")
        asyncio.create_task(worker.run())
    
    # Start 2 email workers
    for i in range(2):
        worker = Worker(task_queue, f"email_worker_{i}")
        asyncio.create_task(worker.run())

@app.post("/upload-image")
async def upload_image(file_path: str, user_id: int):
    # Add task to queue
    await task_queue.put({
        "type": "process_image",
        "function": process_image,
        "args": [file_path, user_id]
    })
    
    return JSONResponse({
        "message": "Image uploaded and queued for processing"
    })

@app.post("/send-newsletter")
async def send_newsletter(email_list: list, subject: str, body: str):
    # Add task to queue
    await task_queue.put({
        "type": "bulk_email",
        "function": send_bulk_email,
        "args": [email_list, subject, body]
    })
    
    return JSONResponse({
        "message": f"Newsletter queued for {len(email_list)} recipients"
    })
```

## Integration with External Task Queues

### Celery Integration

```python
from celery import Celery
from velithon import Velithon
from velithon.responses import JSONResponse

# Configure Celery
celery_app = Celery(
    "velithon_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

app = Velithon()

# Define Celery tasks
@celery_app.task
def process_payment(payment_data):
    """Process payment with external service"""
    # Call payment gateway
    result = payment_gateway.charge(
        amount=payment_data["amount"],
        card_token=payment_data["card_token"]
    )
    
    # Update database
    update_payment_status(payment_data["order_id"], result["status"])
    
    return result

@celery_app.task
def generate_report(report_type, user_id):
    """Generate and email report"""
    report_data = generate_analytics_report(report_type, user_id)
    pdf_path = create_pdf_report(report_data)
    
    user = get_user(user_id)
    send_email_with_attachment(
        to=user["email"],
        subject=f"Your {report_type} Report",
        body="Please find your report attached.",
        attachment=pdf_path
    )

# Velithon endpoints
@app.post("/process-payment")
async def handle_payment(payment_data: dict):
    # Queue payment processing
    task = process_payment.delay(payment_data)
    
    return JSONResponse({
        "task_id": task.id,
        "status": "queued"
    })

@app.post("/generate-report")
async def request_report(report_type: str, user_id: int):
    # Queue report generation
    task = generate_report.delay(report_type, user_id)
    
    return JSONResponse({
        "task_id": task.id,
        "message": "Report generation started"
    })

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    # Check Celery task status
    task = celery_app.AsyncResult(task_id)
    
    return JSONResponse({
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.successful() else None,
        "error": str(task.info) if task.failed() else None
    })
```

### RQ (Redis Queue) Integration

```python
import redis
from rq import Queue, Job
from velithon import Velithon
from velithon.responses import JSONResponse

# Setup Redis connection
redis_conn = redis.Redis(host='localhost', port=6379, db=0)

# Create queues
high_priority_queue = Queue('high', connection=redis_conn)
normal_queue = Queue('normal', connection=redis_conn)
low_priority_queue = Queue('low', connection=redis_conn)

app = Velithon()

# Worker functions
def urgent_notification(user_id: int, message: str):
    """Send urgent notification"""
    user = get_user(user_id)
    send_push_notification(user["device_token"], message)
    send_sms(user["phone"], message)

def batch_data_processing(data_batch: list):
    """Process batch of data"""
    results = []
    for item in data_batch:
        processed = process_data_item(item)
        results.append(processed)
    
    save_processed_data(results)
    return len(results)

def cleanup_temp_files():
    """Clean up temporary files"""
    import os
    import glob
    
    temp_files = glob.glob("/tmp/velithon_*")
    for file_path in temp_files:
        try:
            os.remove(file_path)
        except OSError:
            pass

# Endpoints
@app.post("/urgent-alert")
async def send_urgent_alert(user_id: int, message: str):
    # High priority queue for urgent tasks
    job = high_priority_queue.enqueue(
        urgent_notification,
        user_id,
        message,
        job_timeout='30s'
    )
    
    return JSONResponse({
        "job_id": job.id,
        "queue": "high_priority"
    })

@app.post("/process-batch")
async def process_data_batch(data_batch: list):
    # Normal priority queue for regular processing
    job = normal_queue.enqueue(
        batch_data_processing,
        data_batch,
        job_timeout='5m'
    )
    
    return JSONResponse({
        "job_id": job.id,
        "queue": "normal",
        "estimated_time": "5 minutes"
    })

@app.post("/schedule-cleanup")
async def schedule_cleanup():
    # Low priority queue for maintenance tasks
    job = low_priority_queue.enqueue(
        cleanup_temp_files,
        job_timeout='1h'
    )
    
    return JSONResponse({
        "job_id": job.id,
        "queue": "low_priority"
    })

@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        
        return JSONResponse({
            "job_id": job_id,
            "status": job.get_status(),
            "result": job.result,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None
        })
    except Exception as e:
        return JSONResponse({
            "error": "Job not found"
        }, status_code=404)
```

## Error Handling and Retries

### Retry Logic

```python
from velithon.background import BackgroundTasks, RetryPolicy
import logging

def unreliable_task(data: dict):
    """Task that might fail"""
    if random.random() < 0.3:  # 30% failure rate
        raise Exception("Random failure")
    
    # Process data
    return process_data(data)

@app.post("/submit-data")
async def submit_data(data: dict):
    # Create background tasks
    background_tasks = BackgroundTasks()
    
    # Add task with retry policy
    background_tasks.add_task(
        unreliable_task,
        data,
        retry_policy=RetryPolicy(
            max_retries=3,
            initial_delay=1.0,
            max_delay=60.0,
            exponential_backoff=True
        )
    )
    
    # Execute background tasks
    await background_tasks()
    
    return JSONResponse({
        "message": "Data submitted for processing"
    })

# Custom retry decorator
def retry_on_failure(max_retries=3, delay=1.0, backoff=2.0):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        logging.warning(
                            f"Task {func.__name__} failed on attempt {attempt + 1}, "
                            f"retrying in {wait_time}s: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logging.error(
                            f"Task {func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator

@retry_on_failure(max_retries=3, delay=2.0)
async def fetch_external_data(url: str):
    """Fetch data from external API with retries"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        return response.json()
```

## Monitoring and Metrics

### Task Monitoring

```python
from velithon.background import TaskMonitor
import time

monitor = TaskMonitor()

def monitored_task(task_name: str):
    """Task with monitoring"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            monitor.task_started(task_name)
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                monitor.task_completed(task_name, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                monitor.task_failed(task_name, duration, str(e))
                raise
        
        return wrapper
    return decorator

@monitored_task("email_sending")
async def send_email_monitored(to: str, subject: str, body: str):
    """Send email with monitoring"""
    await send_email_async(to, subject, body)

@app.get("/task-metrics")
async def get_task_metrics():
    """Get task execution metrics"""
    return JSONResponse({
        "total_tasks": monitor.total_tasks,
        "completed_tasks": monitor.completed_tasks,
        "failed_tasks": monitor.failed_tasks,
        "average_duration": monitor.average_duration,
        "task_stats": monitor.get_task_stats()
    })

# Health check for background tasks
@app.get("/health/background-tasks")
async def background_task_health():
    """Check background task system health"""
    stats = monitor.get_recent_stats(minutes=5)
    
    health_status = "healthy"
    if stats["failure_rate"] > 0.1:  # More than 10% failures
        health_status = "degraded"
    if stats["failure_rate"] > 0.5:  # More than 50% failures
        health_status = "unhealthy"
    
    return JSONResponse({
        "status": health_status,
        "recent_tasks": stats["total_tasks"],
        "failure_rate": stats["failure_rate"],
        "average_duration": stats["average_duration"]
    })
```

## Best Practices

### 1. Keep Tasks Simple

```python
# Good: Simple, focused task
def send_welcome_email(user_email: str, user_name: str):
    email_content = f"Welcome {user_name}!"
    send_email(user_email, "Welcome!", email_content)

# Avoid: Complex task with multiple responsibilities
def process_new_user(user_data: dict):
    # Too many things in one task
    send_welcome_email(user_data["email"], user_data["name"])
    update_analytics(user_data)
    sync_to_crm(user_data)
    generate_user_report(user_data["id"])
    # ... more operations
```

### 2. Handle Errors Gracefully

```python
def robust_background_task(data: dict):
    """Background task with proper error handling"""
    try:
        # Main task logic
        result = process_data(data)
        
        # Log success
        logging.info(f"Task completed successfully: {result}")
        
    except ValidationError as e:
        # Handle validation errors
        logging.error(f"Validation error in background task: {e}")
        # Don't retry validation errors
        
    except ConnectionError as e:
        # Handle connection errors
        logging.error(f"Connection error in background task: {e}")
        # This should be retried
        raise
        
    except Exception as e:
        # Handle unexpected errors
        logging.error(f"Unexpected error in background task: {e}")
        # Send alert to monitoring system
        send_alert(f"Background task failed: {e}")
        raise
```

### 3. Use Appropriate Task Queues

```python
# Use different queues for different priorities
@app.post("/critical-operation")
async def critical_operation(data: dict):
    # Use immediate background task for critical operations
    background_tasks = BackgroundTasks()
    background_tasks.add_task(process_critical_data, data)
    return response

@app.post("/bulk-operation")
async def bulk_operation(data_list: list):
    # Use external queue for bulk operations
    job = celery_app.send_task('process_bulk_data', args=[data_list])
    return {"job_id": job.id}
```

## Testing Background Tasks

### Unit Testing

```python
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_background_task_execution():
    """Test that background tasks are executed"""
    with patch('send_email') as mock_send_email:
        background_tasks = BackgroundTasks()
        background_tasks.add_task(send_email, "test@example.com", "Test", "Body")
        
        # Execute background tasks
        await background_tasks.execute_all()
        
        # Verify task was called
        mock_send_email.assert_called_once_with("test@example.com", "Test", "Body")

@pytest.mark.asyncio
async def test_background_task_with_failure():
    """Test background task error handling"""
    def failing_task():
        raise Exception("Task failed")
    
    background_tasks = BackgroundTasks()
    background_tasks.add_task(failing_task)
    
    # Should not raise exception
    await background_tasks.execute_all()
    
    # Check that failure was logged
    # Add your logging assertion here
```

### Integration Testing

```python
from velithon.testing import TestClient

def test_endpoint_with_background_task():
    """Test endpoint that uses background tasks"""
    client = TestClient(app)
    
    with patch('send_email') as mock_send_email:
        response = client.post("/users", json={
            "name": "Test User",
            "email": "test@example.com"
        })
        
        assert response.status_code == 200
        
        # Verify background task was queued
        mock_send_email.assert_called_once()
```

## Next Steps

- [WebSocket Support →](websocket.md)
- [Middleware →](middleware.md)
- [Error Handling →](error-handling.md)
