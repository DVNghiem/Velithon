import asyncio
import inspect
import logging
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .client import VSPClient
from .mesh import ServiceMesh
from .message import VSPError, VSPMessage
from .protocol import VSPProtocol
from .transport import TCPTransport

logger = logging.getLogger(__name__)


class WorkerType(IntEnum):
    ASYNCIO = 1
    MULTICORE = 2


class VSPManager:
    
    def __init__(
        self,
        name: str,
        service_mesh: Optional[ServiceMesh] = None,
        num_workers: int = 4,
        worker_type: WorkerType = WorkerType.ASYNCIO,
        max_queue_size: int = 2000, 
        max_transports: int = 10,
        batch_size: int = 10,   
    ):
        assert isinstance(worker_type, WorkerType), "worker_type must be an instance of WorkerType"
        
        self.name = name
        self.service_mesh = service_mesh or ServiceMesh(discovery_type="static")
        self.client = VSPClient(
            self.service_mesh,
            transport_factory=lambda manager: TCPTransport(manager),
            max_transports=max_transports,
        )
        self.endpoints: Dict[str, Callable[..., Dict[str, Any]]] = {}
        self.client.manager = self
        self.num_workers = max(1, num_workers)
        self.worker_type = worker_type
        self.batch_size = batch_size
        
        # queue with priority handling
        self.message_queue: asyncio.Queue[Tuple[VSPMessage, VSPProtocol]] = (
            asyncio.Queue(maxsize=max_queue_size)
        )
        self.priority_queue: deque = deque()  # For health checks and responses
        
        # Worker management
        self.workers: List[asyncio.Task] = []
        self.executor: Optional[ProcessPoolExecutor] = None
        if self.worker_type == WorkerType.MULTICORE:
            self.executor = ProcessPoolExecutor(max_workers=self.num_workers)
        
        # Performance tracking
        self.stats = {
            'messages_processed': 0,
            'messages_queued': 0,
            'queue_full_errors': 0,
            'processing_errors': 0,
            'batch_processed': 0,
            'average_queue_size': 0,
            'peak_queue_size': 0
        }
        self._last_stats_update = time.time()
        
        # Connection pool integration (create a simple one for now)
        self.connection_pool = None 
        
    def vsp_service(self, endpoint: str) -> Callable:
        """Register a service endpoint with caching optimization"""
        def decorator(func: Callable[..., Dict[str, Any]]) -> Callable:
            # Cache function signature for faster dispatch
            sig = inspect.signature(func)
            self.endpoints[endpoint] = func
            # Store signature for optimization
            func._vsp_signature = sig
            return func
        return decorator

    def vsp_call(self, service_name: str, endpoint: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            async def wrapper(**kwargs) -> Dict[str, Any]:
                logger.debug(f"Calling {service_name}.{endpoint} with {kwargs}")
                response = await self.client.call(service_name, endpoint, kwargs)
                return response
            # Cache the wrapper for reuse
            wrapper._vsp_service = service_name
            wrapper._vsp_endpoint = endpoint
            return wrapper
        return decorator

    async def start_server(
        self, host: str, port: int, loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        """Start server with better worker management"""
        if loop is None:
            loop = asyncio.get_event_loop()
        
        server = await loop.create_server(lambda: VSPProtocol(self), host, port)
        
        # Start workers
        self.workers = [
            asyncio.create_task(self.optimized_worker(i)) for i in range(self.num_workers)
        ]
        
        # Start background cleanup task
        # cleanup_task = asyncio.create_task(self._background_cleanup())
        
        async with server:
            logger.info(f"VSP server started on {host}:{port} with {self.num_workers} workers")
            __serving_forever_fut = loop.create_future()
            try:
                await __serving_forever_fut
            except asyncio.CancelledError:
                try:
                    server.close()
                    # cleanup_task.cancel()
                    self.close()
                finally:
                    raise

    async def enqueue_message(self, message: VSPMessage, protocol: VSPProtocol) -> None:
        """Message enqueuing with priority handling"""
        # Handle priority messages separately
        if (message.header["is_response"] or 
            message.header["endpoint"] == "health"):
            self.priority_queue.append((message, protocol))
            return
        
        try:
            # Update queue size stats
            current_size = self.message_queue.qsize()
            self.stats['peak_queue_size'] = max(self.stats['peak_queue_size'], current_size)
            
            await self.message_queue.put((message, protocol))
            self.stats['messages_queued'] += 1
            logger.debug(f"Enqueued message {message.header['request_id']}")
        except asyncio.QueueFull:
            self.stats['queue_full_errors'] += 1
            logger.error(f"Message queue full, dropping message {message.header['request_id']}")
            error_msg = VSPMessage(
                message.header["request_id"],
                message.header["service"],
                message.header["endpoint"],
                {"error": "Message queue full"},
                is_response=True,
            )
            protocol.send_message(error_msg)
            raise VSPError("Message queue full")

    async def optimized_worker(self, worker_id: int) -> None:
        """Worker with batch processing and priority handling"""
        logger.info(f"Worker {worker_id} ({self.worker_type.name.lower()}) started for {self.name}")
        
        batch = []
        last_batch_time = time.time()
        batch_timeout = 0.01  # 10ms batch timeout
        
        while True:
            try:
                # Process priority messages first
                while self.priority_queue:
                    message, protocol = self.priority_queue.popleft()
                    await self._process_priority_message(message, protocol)
                
                # Try to get a message with short timeout for batching
                try:
                    message, protocol = await asyncio.wait_for(
                        self.message_queue.get(), timeout=batch_timeout
                    )
                    batch.append((message, protocol))
                except asyncio.TimeoutError:
                    pass  # Continue to batch processing
                
                # Process batch if it's full or timeout reached
                current_time = time.time()
                if (len(batch) >= self.batch_size or 
                    (batch and current_time - last_batch_time > batch_timeout)):
                    
                    await self._process_batch(batch, worker_id)
                    batch.clear()
                    last_batch_time = current_time
                    self.stats['batch_processed'] += 1
                
                # Update stats periodically
                if current_time - self._last_stats_update > 10:
                    await self._update_stats()
                    
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} stopped")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                self.stats['processing_errors'] += 1
                await asyncio.sleep(0.1)  # Brief pause before continuing

    async def _process_priority_message(self, message: VSPMessage, protocol: VSPProtocol) -> None:
        """Process high-priority messages (responses and health checks) immediately"""
        if message.header["is_response"]:
            await self.handle_response(message)
        elif message.header["endpoint"] == "health":
            response_msg = VSPMessage(
                message.header["request_id"],
                message.header["service"],
                "health",
                {"status": "healthy", "timestamp": time.time()},
                is_response=True,
            )
            protocol.send_message(response_msg)

    async def _process_batch(self, batch: List[Tuple[VSPMessage, VSPProtocol]], worker_id: int):
        """Process a batch of messages efficiently"""
        if not batch:
            return
            
        # Group by endpoint for potential optimization
        endpoint_groups = {}
        for message, protocol in batch:
            endpoint = message.header["endpoint"]
            if endpoint not in endpoint_groups:
                endpoint_groups[endpoint] = []
            endpoint_groups[endpoint].append((message, protocol))
        
        # Process each endpoint group
        for endpoint, messages in endpoint_groups.items():
            handler = self.endpoints.get(endpoint)
            if not handler:
                # Send error for all messages in group
                for message, protocol in messages:
                    error_msg = VSPMessage(
                        message.header["request_id"],
                        message.header["service"],
                        message.header["endpoint"],
                        {"error": f"Endpoint {endpoint} not found"},
                        is_response=True,
                    )
                    protocol.send_message(error_msg)
                continue
            
            # Process messages for this endpoint
            if self.worker_type == WorkerType.ASYNCIO:
                await self._process_async_batch(messages, handler)
            else:  # MULTICORE
                await self._process_multicore_batch(messages, handler)
        
        self.stats['messages_processed'] += len(batch)
        
        # Mark all tasks as done
        for _ in batch:
            self.message_queue.task_done()

    async def _process_async_batch(self, messages: List[Tuple[VSPMessage, VSPProtocol]], handler: Callable):
        """Process batch of messages asynchronously"""
        tasks = []
        for message, protocol in messages:
            task = self._handle_single_message_async(message, protocol, handler)
            tasks.append(task)
        
        # Process all messages in parallel
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_single_message_async(self, message: VSPMessage, protocol: VSPProtocol, handler: Callable):
        """Handle a single message asynchronously"""
        try:
            response = handler(**message.body)
            if inspect.isawaitable(response):
                response = await response
            
            response_msg = VSPMessage(
                message.header["request_id"],
                message.header["service"],
                message.header["endpoint"],
                response,
                is_response=True,
            )
            protocol.send_message(response_msg)
        except Exception as e:
            logger.error(f"Error processing message {message.header['request_id']}: {e}")
            error_msg = VSPMessage(
                message.header["request_id"],
                message.header["service"],
                message.header["endpoint"],
                {"error": str(e)},
                is_response=True,
            )
            protocol.send_message(error_msg)

    async def _process_multicore_batch(self, messages: List[Tuple[VSPMessage, VSPProtocol]], handler: Callable):
        """Process batch using multicore processing"""
        loop = asyncio.get_event_loop()
        
        # Prepare batch for multicore processing
        message_data = [(msg.header, msg.body) for msg, _ in messages]
        
        try:
            # Process entire batch in executor
            results = await loop.run_in_executor(
                self.executor,
                self._process_batch_sync,
                message_data,
                handler
            )
            
            # Send responses
            for i, (message, protocol) in enumerate(messages):
                if i < len(results):
                    if isinstance(results[i], Exception):
                        error_msg = VSPMessage(
                            message.header["request_id"],
                            message.header["service"],
                            message.header["endpoint"],
                            {"error": str(results[i])},
                            is_response=True,
                        )
                        protocol.send_message(error_msg)
                    else:
                        response_msg = VSPMessage(
                            message.header["request_id"],
                            message.header["service"],
                            message.header["endpoint"],
                            results[i],
                            is_response=True,
                        )
                        protocol.send_message(response_msg)
        except Exception as e:
            logger.error(f"Batch multicore processing failed: {e}")
            # Send error to all messages
            for message, protocol in messages:
                error_msg = VSPMessage(
                    message.header["request_id"],
                    message.header["service"],
                    message.header["endpoint"],
                    {"error": f"Batch processing failed: {e}"},
                    is_response=True,
                )
                protocol.send_message(error_msg)

    @staticmethod
    def _process_batch_sync(message_data: List[Tuple[Dict, Dict]], handler: Callable) -> List[Any]:
        """Synchronously process a batch of messages"""
        results = []
        for header, body in message_data:
            try:
                result = handler(**body)
                results.append(result)
            except Exception as e:
                results.append(e)
        return results

    async def _background_cleanup(self):
        """Background task for periodic cleanup"""
        while True:
            try:
                await asyncio.sleep(30)  # Run every 30 seconds
                
                # Clean up expired connections (if connection pool exists)
                if self.connection_pool:
                    self.connection_pool.cleanup_expired_connections()
                
                # Log stats
                stats = self.get_performance_stats()
                logger.debug(f"VSP Manager {self.name} stats: {stats}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background cleanup error: {e}")

    async def _update_stats(self):
        """Update performance statistics"""
        current_size = self.message_queue.qsize()
        self.stats['average_queue_size'] = (
            self.stats['average_queue_size'] * 0.9 + current_size * 0.1
        )
        self._last_stats_update = time.time()

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        connection_stats = {}
        if self.connection_pool:
            connection_stats = self.connection_pool.get_stats()
        
        return {
            **self.stats,
            'current_queue_size': self.message_queue.qsize(),
            'worker_count': len(self.workers),
            'worker_type': self.worker_type.name,
            'connection_pool': connection_stats
        }

    async def handle_response(self, message: VSPMessage) -> None:
        """Handle response messages"""
        await self.client.handle_response(message)

    async def handle_vsp_endpoint(
        self, endpoint: str, body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle VSP endpoint"""
        handler = self.endpoints.get(endpoint)
        if not handler:
            logger.error(f"Endpoint {endpoint} not found")
            raise VSPError(f"Endpoint {endpoint} not found")
        try:
            response = handler(**body)
            if inspect.isawaitable(response):
                response = await response
            return response
        except Exception as e:
            logger.error(f"Error handling endpoint {endpoint}: {e}")
            raise VSPError(f"Endpoint execution failed: {e}")

    def close(self) -> None:
        """Close manager and clean up resources"""
        logger.info(f"Closing OptimizedVSPManager {self.name}")
        
        # Cancel workers
        for worker in self.workers:
            worker.cancel()
        self.workers.clear()
        
        # Shutdown executor
        if self.executor:
            self.executor.shutdown(wait=False)
        
        # Close client connections
        for connection_key, transports in list(self.client.transports.items()):
            for transport in transports:
                if not transport.is_closed():
                    transport.close()
            self.client.transports[connection_key].clear()
            self.client.connection_events[connection_key].clear()
        
        # Cancel health check tasks
        for task in self.client.health_check_tasks.values():
            task.cancel()
        self.client.health_check_tasks.clear()
        
        # Close service mesh
        self.service_mesh.close()
        
        # Close connection pool (if exists)
        if self.connection_pool:
            self.connection_pool.close_all()


