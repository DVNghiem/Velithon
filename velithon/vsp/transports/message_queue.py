import asyncio
import logging
from typing import TYPE_CHECKING, Optional, Any, Dict

try:
    import aio_pika
    from aio_pika import Message, ExchangeType
    AIO_PIKA_AVAILABLE = True
except ImportError:
    AIO_PIKA_AVAILABLE = False

from ..abstract import Transport, TransportType, ConnectionConfig
from ..transport_factory import transport_registry

if TYPE_CHECKING:
    from ..manager import VSPManager

logger = logging.getLogger(__name__)


@transport_registry(TransportType.MESSAGE_QUEUE)
class MessageQueueTransport(Transport):
    """Message Queue (RabbitMQ) implementation of Transport."""

    def __init__(self, transport_type: TransportType = TransportType.MESSAGE_QUEUE):
        if not AIO_PIKA_AVAILABLE:
            raise ImportError("aio-pika package is required for Message Queue transport. Install with: pip install aio-pika")
        
        super().__init__(transport_type)
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.RobustChannel] = None
        self.exchange: Optional[aio_pika.RobustExchange] = None
        self.queue: Optional[aio_pika.RobustQueue] = None
        self.manager: Optional["VSPManager"] = None
        self._connected: bool = False
        self.queue_name: str = "vsp_messages"
        self.exchange_name: str = "vsp_exchange"

    async def connect(self, config: ConnectionConfig, manager: "VSPManager") -> None:
        self.manager = manager
        
        try:
            # Build connection URL
            if config.username and config.password:
                url = f"amqp://{config.username}:{config.password}@{config.host}:{config.port}/"
            else:
                url = f"amqp://{config.host}:{config.port}/"
            
            # Create robust connection
            self.connection = await aio_pika.connect_robust(
                url,
                timeout=config.timeout or 30
            )
            
            # Create channel
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            
            # Create exchange
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                ExchangeType.DIRECT,
                durable=True
            )
            
            # Create queue
            self.queue = await self.channel.declare_queue(
                self.queue_name,
                durable=True
            )
            
            # Bind queue to exchange
            await self.queue.bind(self.exchange, routing_key=self.queue_name)
            
            self._connected = True
            logger.debug(f"Message Queue connected to {config.host}:{config.port}")
            
        except Exception as e:
            logger.error(f"Message Queue connection failed to {config.host}:{config.port}: {e}")
            if self.connection:
                await self.connection.close()
                self.connection = None
            raise

    async def send(self, data: bytes) -> None:
        if not self._connected or self.exchange is None:
            raise RuntimeError("Message Queue transport not connected")
        
        try:
            # Create message
            message = Message(
                data,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            
            # Publish message
            await self.exchange.publish(
                message,
                routing_key=self.queue_name
            )
            
            logger.debug(f"Message Queue sent data of length {len(data)}")
            
        except Exception as e:
            logger.error(f"Message Queue send error: {e}")
            raise

    async def receive(self) -> Optional[bytes]:
        if not self._connected or self.queue is None:
            return None
        
        try:
            # Get message with timeout
            message = await asyncio.wait_for(
                self.queue.get(no_ack=False),
                timeout=1.0  # 1 second timeout
            )
            
            if message:
                data = message.body
                await message.ack()  # Acknowledge message
                logger.debug(f"Message Queue received data of length {len(data)}")
                return data
                
        except asyncio.TimeoutError:
            # No message available
            return None
        except Exception as e:
            logger.error(f"Message Queue receive error: {e}")
            return None

    def close(self) -> None:
        if self.connection and not self.connection.is_closed:
            asyncio.create_task(self.connection.close())
            logger.debug("Message Queue transport closed")
        self.connection = None
        self.channel = None
        self.exchange = None
        self.queue = None
        self._connected = False

    def is_closed(self) -> bool:
        return not self._connected or self.connection is None or self.connection.is_closed

    def supports_bidirectional(self) -> bool:
        return True  # Message queues support bidirectional communication

    def get_connection_info(self) -> Dict[str, Any]:
        return {
            'connected': self._connected,
            'queue_name': self.queue_name,
            'exchange_name': self.exchange_name,
            'transport_type': self.transport_type.value
        }
