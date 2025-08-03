# Velithon Event System

## Overview

The Velithon event system provides a high-performance, Rust-powered mechanism for registering and handling events across your application. The core component is the `EventChannel` class, which enables you to define event listeners and emit events in a thread-safe and efficient manner.

## Features

- Register event listeners for custom events
- Support for both synchronous and asynchronous event handlers
- High-performance backend implemented in Rust for minimal overhead
- Configurable buffer size for event handling

## Usage

### 1. Creating an Event Channel

```python
from velithon.event import EventChannel

event_channel = EventChannel(buffer_size=1000)
```

### 2. Registering Event Listeners

You can register a listener for a specific event using the `on_event` decorator. Both synchronous and asynchronous functions are supported.

```python
@event_channel.on_event("user_registered")
def handle_user_registered(event_data):
    print("User registered:", event_data)

@event_channel.on_event("order_completed")
async def handle_order_completed(event_data):
    await process_order(event_data)
```

### 3. Emitting Events

To emit an event, use the `emit` method (provided by the Rust backend):

```python
await event_channel.emit("user_registered", {"user_id": 123})
```

### 4. Buffer Size

The `buffer_size` parameter controls the internal queue size for event delivery. Increase it for high-throughput scenarios.

## API Reference

### `EventChannel(buffer_size: int = 1000)`
Creates a new event channel with the specified buffer size.

### `on_event(event_name: str)`
Decorator to register a function as a listener for the given event name.
- `event_name`: The name of the event to listen for.

### `emit(event_name: str, data: dict)`
Emits an event with the given name and data to all registered listeners.

## Best Practices

- Use descriptive event names to avoid conflicts.
- Prefer async handlers for I/O-bound event processing.
- Monitor buffer usage in high-load scenarios to avoid dropped events.

---

This event system enables scalable, decoupled communication within your Velithon application, leveraging Rust for maximum performance.
