import asyncio
import logging
import random
import uuid
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from .mesh import ServiceMesh
from .message import VSPError, VSPMessage

if TYPE_CHECKING:
    from .manager import VSPManager
from .abstract import Transport

logger = logging.getLogger(__name__)


class VSPClient:
    def __init__(
        self,
        service_mesh: ServiceMesh,
        transport_factory: Callable[..., Transport],
        max_transports: int = 5,
    ):
        self.service_mesh = service_mesh
        self.transport_factory = transport_factory
        self.max_transports = max_transports
        self.transports: Dict[str, List[Transport]] = defaultdict(list)
        self.response_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self.manager: Optional[VSPManager] = None
        self.connection_events: Dict[str, asyncio.Event] = {}
        self.health_check_tasks: Dict[str, asyncio.Task] = {}

    async def get_service(self, service_name: str) -> Dict[str, Any]:
        service = await self.service_mesh.query(service_name)
        if not service:
            logger.error(f"Service {service_name} not found or unhealthy")
            raise VSPError(f"Service {service_name} not found or unhealthy")
        return {"host": service.host, "port": service.port}

    async def ensure_transport(self, service_name: str) -> str:
        service = await self.get_service(service_name)
        connection_key = f"{service['host']}:{service['port']}"
        if connection_key not in self.connection_events:
            self.connection_events[connection_key] = asyncio.Event()

        active_transports = [
            t for t in self.transports[connection_key] if not t.is_closed()
        ]
        while len(active_transports) < self.max_transports:
            try:
                transport = self.transport_factory(self.manager)
                await transport.connect(service["host"], service["port"])
                self.transports[connection_key].append(transport)
                active_transports.append(transport)
                logger.debug(
                    f"Added transport to {connection_key}, total: {len(active_transports)}"
                )
            except (ConnectionRefusedError, OSError) as e:
                logger.warning(f"Transport connection failed to {service_name}: {e}")
                for s in await self.service_mesh.discovery.query(service_name):
                    if s.host == service["host"] and s.port == service["port"]:
                        s.mark_unhealthy()
                raise VSPError(f"Failed to connect to {service_name}: {e}")
        self.connection_events[connection_key].set()
        if connection_key not in self.health_check_tasks:
            self.health_check_tasks[connection_key] = asyncio.create_task(
                self.health_check(service_name)
            )
        return connection_key

    async def get_transport(self, service_name: str) -> Tuple[Transport, str]:
        connection_key = await self.ensure_transport(service_name)
        active_transports = [
            t for t in self.transports[connection_key] if not t.is_closed()
        ]
        if not active_transports:
            self.connection_events[connection_key].clear()
            self.transports[connection_key].clear()
            connection_key = await self.ensure_transport(service_name)
            active_transports = [t for t in self.transports[connection_key]]
        transport = random.choice(active_transports)
        return transport, connection_key

    async def health_check(self, service_name: str) -> None:
        while True:
            try:
                await self.call(service_name, "health", {})
                for s in await self.service_mesh.discovery.query(service_name):
                    s.mark_healthy()
            except VSPError as e:
                logger.warning(f"Health check failed for {service_name}: {e}")
                for s in await self.service_mesh.discovery.query(service_name):
                    s.mark_unhealthy()
            await asyncio.sleep(10)  # Reduced health check frequency

    async def call(
        self,
        service_name: str,
        endpoint: str,
        data: Dict[str, Any],
        connection_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not connection_key:
            transport, connection_key = await self.get_transport(service_name)
        else:
            transport = next(
                (t for t in self.transports[connection_key] if not t.is_closed()), None
            )
            if not transport:
                transport, connection_key = await self.get_transport(service_name)

        request_id = str(uuid.uuid4())
        message = VSPMessage(
            request_id=request_id, service=service_name, endpoint=endpoint, body=data
        )
        data_bytes = len(message.to_bytes()).to_bytes(4, "big") + message.to_bytes()
        transport.send(data_bytes)
        logger.debug(f"Sent request {request_id} to {service_name}.{endpoint}")

        try:
            response = await asyncio.wait_for(
                self.response_queues[request_id].get(), timeout=30  # Increased timeout
            )
            del self.response_queues[request_id]
            if "error" in response:
                raise VSPError(response["error"])
            return response
        except asyncio.TimeoutError:
            # Clean up on timeout
            if request_id in self.response_queues:
                del self.response_queues[request_id]
            # Don't immediately close all transports - they might be used by other requests
            logger.error(f"Request {request_id} timed out after 30 seconds")
            raise VSPError("Request timed out")

    async def handle_response(self, message: VSPMessage) -> None:
        request_id = message.header["request_id"]
        await self.response_queues[request_id].put(message.body)
        logger.debug(f"Received response for request {request_id}")
