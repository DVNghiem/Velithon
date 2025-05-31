import asyncio
import logging
import inspect
from enum import IntEnum
from typing import Dict, Any, Optional, Callable, Tuple, List
from concurrent.futures import ProcessPoolExecutor
from .message import VSPMessage, VSPError
from .client import VSPClient
from .mesh import ServiceMesh
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
        max_queue_size: int = 1000,
        max_transports: int = 5
    ):
        self.name = name
        self.service_mesh = service_mesh or ServiceMesh(discovery_type="static")
        self.client = VSPClient(
            self.service_mesh,
            transport_factory=lambda: TCPTransport(self),
            max_transports=max_transports
        )
        self.endpoints: Dict[str, Callable[..., Dict[str, Any]]] = {}
        self.client.manager = self
        self.num_workers = max(1, num_workers)
        self.worker_type = worker_type
        self.message_queue: asyncio.Queue[Tuple[VSPMessage, VSPProtocol]] = asyncio.Queue(maxsize=max_queue_size)
        self.workers: List[asyncio.Task] = []
        self.executor: Optional[ProcessPoolExecutor] = None
        if self.worker_type == WorkerType.MULTICORE:
            self.executor = ProcessPoolExecutor(max_workers=self.num_workers)
        logger.info(f"Initialized VSPManager for {name} with {self.num_workers} {self.worker_type.name.lower()} workers, queue size {max_queue_size}")

    def vsp_service(self, endpoint: str) -> Callable:
        def decorator(func: Callable[..., Dict[str, Any]]) -> Callable:
            self.endpoints[endpoint] = func
            logger.debug(f"Registered endpoint {endpoint} for {self.name}")
            return func
        return decorator

    def vsp_call(self, service_name: str, endpoint: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            async def wrapper(**kwargs) -> Dict[str, Any]:
                logger.debug(f"Calling {service_name}.{endpoint} with {kwargs}")
                response = await self.client.call(service_name, endpoint, kwargs)
                return response
            return wrapper
        return decorator

    async def register_service(self, host: str, port: int) -> None:
        from .mesh import ServiceInfo
        service_info = ServiceInfo(self.name, host, port)
        self.service_mesh.register(service_info)
        logger.info(f"Registered {self.name} at {host}:{port}")
        self.workers = [asyncio.create_task(self.worker(i)) for i in range(self.num_workers)]
        await self.start_server(host, port)

    async def start_server(self, host: str, port: int, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        if loop is None:
            loop = asyncio.get_event_loop()
        server = await loop.create_server(
            lambda: VSPProtocol(self), host, port
        )
        async with server:
            logger.info(f"VSP server started on {host}:{port}")
            __serving_forever_fut = loop.create_future()
            try:
                await __serving_forever_fut
            except asyncio.CancelledError:
                try:
                    server.close()
                    self.close()
                finally:
                    raise

    async def enqueue_message(self, message: VSPMessage, protocol: VSPProtocol) -> None:
        try:
            await self.message_queue.put((message, protocol))
            logger.debug(f"Enqueued message {message.header['request_id']}")
        except asyncio.QueueFull:
            logger.error(f"Message queue full, dropping message {message.header['request_id']}")
            error_msg = VSPMessage(
                message.header["request_id"],
                message.header["service"],
                message.header["endpoint"],
                {"error": "Message queue full"},
                is_response=True
            )
            protocol.send_message(error_msg)
            raise VSPError("Message queue full")

    async def worker(self, worker_id: int) -> None:
        logger.info(f"Worker {worker_id} ({self.worker_type.name.lower()}) started for {self.name}")
        while True:
            try:
                message, protocol = await self.message_queue.get()
                try:
                    if self.worker_type == WorkerType.ASYNCIO:
                        await self.process_message(message, protocol)
                    else:  # MULTICORE
                        loop = asyncio.get_event_loop()
                        response = await loop.run_in_executor(
                            self.executor,
                            self._process_message_sync,
                            message.header["endpoint"],
                            message.body,
                            self.endpoints
                        )
                        response_msg = VSPMessage(
                            message.header["request_id"],
                            message.header["service"],
                            message.header["endpoint"],
                            response,
                            is_response=True
                        )
                        protocol.send_message(response_msg)
                except Exception as e:
                    logger.error(f"Worker {worker_id} failed to process message: {e}")
                    error_msg = VSPMessage(
                        message.header["request_id"],
                        message.header["service"],
                        message.header["endpoint"],
                        {"error": str(e)},
                        is_response=True
                    )
                    protocol.send_message(error_msg)
                finally:
                    self.message_queue.task_done()
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} stopped")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)

    @staticmethod
    def _process_message_sync(endpoint: str, body: Dict[str, Any], endpoints: Dict[str, Callable]) -> Dict[str, Any]:
        handler = endpoints.get(endpoint)
        if not handler:
            raise VSPError(f"Endpoint {endpoint} not found")
        try:
            return handler(**body)
        except Exception as e:
            raise VSPError(f"Endpoint execution failed: {e}")

    async def process_message(self, message: VSPMessage, protocol: VSPProtocol) -> None:
        await protocol.handle_message(message)

    def close(self) -> None:
        logger.info(f"Closing VSPManager {self.name} connections and workers")
        for worker in self.workers:
            worker.cancel()
        self.workers.clear()
        if self.executor:
            self.executor.shutdown(wait=True)
        for connection_key, transports in list(self.client.transports.items()):
            for transport in transports:
                if not transport.is_closed():
                    transport.close()
            logger.debug(f"Closed transports for {connection_key}")
            self.client.transports[connection_key].clear()
            self.client.connection_events[connection_key].clear()
        for task in self.client.health_check_tasks.values():
            task.cancel()
        self.client.health_check_tasks.clear()
        self.service_mesh.close()

    async def handle_response(self, message: VSPMessage) -> None:
        await self.client.handle_response(message)

    async def handle_vsp_endpoint(self, endpoint: str, body: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"Handling VSP endpoint: {endpoint} with body: {body}")
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