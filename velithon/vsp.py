import asyncio
import inspect
import time
import uuid
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, Optional

import msgpack
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ServiceInfo:
    def __init__(self, name: str, host: str, port: int):
        self.name = name
        self.host = host
        self.port = port


class ServiceMesh:
    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}

    def register(self, service: ServiceInfo):
        self.services[service.name] = service

    async def query(self, service_name: str) -> Optional[ServiceInfo]:
        return self.services.get(service_name)


class VSPMessage:
    def __init__(
        self,
        request_id: str,
        service: str,
        endpoint: str,
        body: Any,
        is_response: bool = False,
    ):
        self.header = {
            "request_id": request_id,
            "service": service,
            "endpoint": endpoint,
            "is_response": is_response,
        }
        self.body = body

    def to_bytes(self) -> bytes:
        return msgpack.packb({"header": self.header, "body": self.body})

    @classmethod
    def from_bytes(cls, data: bytes) -> "VSPMessage":
        unpacked = msgpack.unpackb(data, raw=False)
        return cls(
            unpacked["header"]["request_id"],
            unpacked["header"]["service"],
            unpacked["header"]["endpoint"],
            unpacked["body"],
            unpacked["header"].get("is_response", False),
        )


class VSPProtocol(asyncio.Protocol):
    def __init__(self, vsp_mesh: "VSPMesh" = None):
        self.vsp_mesh = vsp_mesh
        self.transport = None
        self.buffer = b""
        self.last_heartbeat = time.time()
        self.heartbeat_task = None

    def connection_made(self, transport):
        self.transport = transport
        print(f"Connection made: {transport.get_extra_info('peername')}")
        self.heartbeat_task = asyncio.create_task(self.heartbeat())

    def connection_lost(self, exc):
        if self.heartbeat_task:
            self.heartbeat_task.cancel()

    def data_received(self, data):
        print(f"Data received: {data}")
        self.buffer += data
        while len(self.buffer) >= 4:
            if len(self.buffer) < 4:
                break
            length = int.from_bytes(self.buffer[:4], "big")
            if len(self.buffer) < 4 + length:
                break
            message_data = self.buffer[4 : 4 + length]
            self.buffer = self.buffer[4 + length :]
            message = VSPMessage.from_bytes(message_data)
            asyncio.create_task(self.handle_message(message))

    async def handle_message(self, message: VSPMessage):
        try:
            if message.header["endpoint"] == "ping":
                response_msg = VSPMessage(
                    message.header["request_id"],
                    message.header["service"],
                    "pong",
                    {"status": "alive"},
                    is_response=True,
                )
                self.send_message(response_msg)
                self.last_heartbeat = time.time()
            elif message.header["is_response"]:
                await self.vsp_mesh.handle_response(message)
                self.last_heartbeat = time.time()
            else:
                response = await self.vsp_mesh.handle_vsp_endpoint(
                    message.header["endpoint"], message.body
                )
                response_msg = VSPMessage(
                    message.header["request_id"],
                    message.header["service"],
                    message.header["endpoint"],
                    response,
                    is_response=True,
                )
                self.send_message(response_msg)
                self.last_heartbeat = time.time()
        except Exception as e:
            error_msg = VSPMessage(
                message.header["request_id"],
                message.header["service"],
                message.header["endpoint"],
                {"error": str(e)},
                is_response=True,
            )
            self.send_message(error_msg)

    def send_message(self, message: VSPMessage):
        if self.transport and not self.transport.is_closing():
            data = message.to_bytes()
            length = len(data).to_bytes(4, "big")
            self.transport.write(length + data)

    async def heartbeat(self):
        while not self.transport.is_closing():
            if time.time() - self.last_heartbeat > 30:
                self.transport.close()
                break
            await asyncio.sleep(10)


class VSPClient:
    def __init__(self, service_mesh: ServiceMesh):
        self.vsp_mesh = None
        self.service_mesh = service_mesh
        self.connections: Dict[str, tuple[asyncio.Transport, VSPProtocol]] = {}
        self.response_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self.connection_events: Dict[str, asyncio.Event] = {}

    async def get_service(self, service_name: str) -> Optional[Dict[str, Any]]:
        service = await self.service_mesh.query(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")
        return {"host": service.host, "port": service.port}

    async def ensure_connection(self, service_name: str):
        service = await self.get_service(service_name)
        connection_key = f"{service['host']}:{service['port']}"
        if connection_key not in self.connection_events:
            self.connection_events[connection_key] = asyncio.Event()

        if (
            connection_key not in self.connections
            or self.connections[connection_key][0].is_closing()
        ):
            retry_delay = 1
            while True:
                try:
                    (
                        transport,
                        protocol,
                    ) = await asyncio.get_event_loop().create_connection(
                        lambda: VSPProtocol(self.vsp_mesh),
                        service["host"],
                        service["port"],
                    )
                    self.connections[connection_key] = (transport, protocol)
                    self.connection_events[connection_key].set()
                    asyncio.create_task(self.send_heartbeat(connection_key))
                    break
                except (ConnectionRefusedError, OSError):
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 8)  # Exponential backoff

    async def send_heartbeat(self, connection_key: str):
        while (
            connection_key in self.connections
            and not self.connections[connection_key][0].is_closing()
        ):
            try:
                await self.call(
                    "ping_service", "ping", None, connection_key=connection_key
                )
                await asyncio.sleep(10)
            except Exception:
                self.connections[connection_key][0].close()
                del self.connections[connection_key]
                self.connection_events[connection_key].clear()
                break

    async def call(
        self,
        service_name: str,
        endpoint: str,
        data: Dict[str, Any] | None = None,
        connection_key: Optional[str] = None,
    ) -> Any:
        if not connection_key:
            await self.ensure_connection(service_name)
            service = await self.get_service(service_name)
            connection_key = f"{service['host']}:{service['port']}"

        await self.connection_events[connection_key].wait()
        if (
            connection_key not in self.connections
            or self.connections[connection_key][0].is_closing()
        ):
            await self.ensure_connection(service_name)

        transport = self.connections[connection_key][0]
        request_id = str(uuid.uuid4())
        message = VSPMessage(
            request_id=request_id,
            service=service_name,
            endpoint=endpoint,
            body=data if data else {},
        )
        transport.write(len(message.to_bytes()).to_bytes(4, "big") + message.to_bytes())

        try:
            response = await asyncio.wait_for(
                self.response_queues[request_id].get(), timeout=10
            )
            del self.response_queues[request_id]
            if "error" in response:
                raise ValueError(response["error"])
            return response
        except asyncio.TimeoutError:
            del self.response_queues[request_id]
            transport.close()
            del self.connections[connection_key]
            self.connection_events[connection_key].clear()
            raise ValueError("Request timed out")

    async def handle_response(self, message: VSPMessage):
        await self.response_queues[message.header["request_id"]].put(message.body)


class VSPMesh:
    def __init__(self):
        self.service_mesh = ServiceMesh()
        self.client = VSPClient(self.service_mesh)
        self.endpoints: Dict[str, Callable] = {}
        self.client.vsp_mesh = self

    # ============= this block handles service registration and querying ==============
    def register_service(
        self, name: str, host: str, port: int
    ):
        service = ServiceInfo(name, host, port)
        self.service_mesh.register(service)

    # ============ this block handles client connections and requests ==============
    async def close(self):
        for _, (transport, _) in self.client.connections.values():
            if not transport.is_closing():
                transport.close()
        self.client.connections.clear()
        self.client.response_queues.clear()
        self.client.connection_events.clear()

    async def start_server(self, host: str, port: int, loop: Optional[asyncio.AbstractEventLoop] = None):
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

    # ============== this block handles the VSP endpoints ==============
    async def handle_vsp_endpoint(self, endpoint: str, body: Any):
        handler = self.endpoints.get(endpoint)
        print(f"Handling VSP endpoint: {endpoint} with body: {body}")
        if not handler:
            raise ValueError(f"Endpoint {endpoint} not found")

        sig = inspect.signature(handler)
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param.annotation != inspect.Parameter.empty and issubclass(
                param.annotation, BaseModel
            ):
                kwargs[param_name] = param.annotation.model_validate(body)
        response = handler(**kwargs)
        if inspect.isawaitable(response):
            response = await response
        return response.model_dump() if isinstance(response, BaseModel) else response

    def vsp_service(self, endpoint: str):
        def decorator(func: Callable):
            self.endpoints[endpoint] = func
            return func
        return decorator
    
    def handle_response(self, message: VSPMessage):
        return self.client.handle_response(message)
    
vsp_mesh = VSPMesh()
