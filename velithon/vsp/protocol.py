import asyncio
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .manager import VSPManager
from .message import VSPError, VSPMessage

logger = logging.getLogger(__name__)


class VSPProtocol(asyncio.Protocol):
    def __init__(self, manager: "VSPManager"):
        self.manager = manager
        self.transport: Optional[asyncio.Transport] = None
        self.buffer = bytearray()

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        logger.debug(f"Connection made: {transport.get_extra_info('peername')}")

    def connection_lost(self, exc: Optional[Exception]) -> None:
        logger.debug(f"Connection lost: {exc}")
        if self.transport:
            self.transport.close()

    def data_received(self, data: bytes) -> None:
        self.buffer.extend(data)
        while len(self.buffer) >= 4:
            length = int.from_bytes(self.buffer[:4], "big")
            # Check if we have enough data for the complete message
            if len(self.buffer) < 4 + length:
                break  # Wait for more data
            
            message_data = self.buffer[4 : 4 + length]
            self.buffer = self.buffer[4 + length :]
            try:
                message = VSPMessage.from_bytes(message_data)
                # Create task but don't await to avoid blocking the protocol
                asyncio.create_task(self.manager.enqueue_message(message, self))
            except VSPError as e:
                logger.error(f"Failed to process message: {e}")
                # Continue processing other messages even if one fails

    async def handle_message(self, message: VSPMessage) -> None:
        try:
            response = await self.manager.handle_vsp_endpoint(
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
        except VSPError as e:
            logger.error(f"Error handling message: {e}")
            error_msg = VSPMessage(
                message.header["request_id"],
                message.header["service"],
                message.header["endpoint"],
                {"error": str(e)},
                is_response=True,
            )
            self.send_message(error_msg)

    def send_message(self, message: VSPMessage) -> None:
        if self.transport and not self.transport.is_closing():
            data = message.to_bytes()
            length = len(data).to_bytes(4, "big")
            self.transport.write(length + data)
            logger.debug(f"Sent message: {message.header}")
