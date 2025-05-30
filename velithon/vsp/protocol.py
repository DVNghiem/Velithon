import asyncio
import logging
import time
from typing import Optional
from .message import VSPMessage, VSPError
from .manager import VSPManager
from .transport import Transport

logger = logging.getLogger(__name__)

class VSPProtocol(asyncio.Protocol):
    def __init__(self, manager: 'VSPManager', transport: Optional[Transport] = None):
        self.manager = manager
        self.transport = transport
        self._transport: Optional[asyncio.Transport] = None
        self.buffer = bytearray()
        self.last_heartbeat = time.time()
        self.heartbeat_task: Optional[asyncio.Task] = None

    def connection_made(self, transport: asyncio.Transport) -> None:
        self._transport = transport
        logger.debug(f"Connection made: {transport.get_extra_info('peername')}")
        self.heartbeat_task = asyncio.create_task(self.heartbeat())

    def connection_lost(self, exc: Optional[Exception]) -> None:
        logger.debug(f"Connection lost: {exc}")
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        self._transport = None
        if self.transport:
            self.transport.close()

    def data_received(self, data: bytes) -> None:
        self.buffer.extend(data)
        while len(self.buffer) >= 4:
            length = int.from_bytes(self.buffer[:4], "big")
            if len(self.buffer) < 4 + length:
                break
            message_data = self.buffer[4:4 + length]
            self.buffer = self.buffer[4 + length:]
            try:
                message = VSPMessage.from_bytes(message_data)
                asyncio.create_task(self.manager.enqueue_message(message, self))
            except VSPError as e:
                logger.error(f"Failed to process message: {e}")

    async def handle_message(self, message: VSPMessage) -> None:
        try:
            logger.debug(f"Processing message: {message.header}")
            if message.header["endpoint"] == "ping":
                response_msg = VSPMessage(
                    message.header["request_id"],
                    message.header["service"],
                    "pong",
                    {"status": "alive"},
                    is_response=True
                )
                self.send_message(response_msg)
                self.last_heartbeat = time.time()
            elif message.header["endpoint"] == "health":
                response_msg = VSPMessage(
                    message.header["request_id"],
                    message.header["service"],
                    "health",
                    {"status": "healthy"},
                    is_response=True
                )
                self.send_message(response_msg)
                self.last_heartbeat = time.time()
            elif message.header["is_response"]:
                await self.manager.handle_response(message)
                self.last_heartbeat = time.time()
            else:
                response = await self.manager.handle_vsp_endpoint(message.header["endpoint"], message.body)
                response_msg = VSPMessage(
                    message.header["request_id"],
                    message.header["service"],
                    message.header["endpoint"],
                    response,
                    is_response=True
                )
                self.send_message(response_msg)
                self.last_heartbeat = time.time()
        except VSPError as e:
            logger.error(f"Error handling message: {e}")
            error_msg = VSPMessage(
                message.header["request_id"],
                message.header["service"],
                message.header["endpoint"],
                {"error": str(e)},
                is_response=True
            )
            self.send_message(error_msg)

    def send_message(self, message: VSPMessage) -> None:
        if self._transport and not self._transport.is_closing():
            data = message.to_bytes()
            length = len(data).to_bytes(4, "big")
            self._transport.write(length + data)
            logger.debug(f"Sent message: {message.header}")

    async def heartbeat(self) -> None:
        while self._transport and not self._transport.is_closing():
            if time.time() - self.last_heartbeat > 30:
                logger.warning("Heartbeat timeout, closing connection")
                if self._transport:
                    self._transport.close()
                break
            await asyncio.sleep(10)