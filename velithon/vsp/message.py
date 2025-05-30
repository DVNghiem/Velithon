import logging
from typing import Any, Dict

import msgpack

logger = logging.getLogger(__name__)


class VSPError(Exception):
    pass


class VSPMessage:
    def __init__(
        self,
        request_id: str,
        service: str,
        endpoint: str,
        body: Dict[str, Any],
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
        try:
            return msgpack.packb(
                {"header": self.header, "body": self.body}, use_bin_type=True
            )
        except Exception as e:
            logger.error(f"Failed to serialize message: {e}")
            raise VSPError(f"Message serialization failed: {e}")

    @classmethod
    def from_bytes(cls, data: bytes) -> "VSPMessage":
        try:
            unpacked = msgpack.unpackb(data, raw=False)
            return cls(
                unpacked["header"]["request_id"],
                unpacked["header"]["service"],
                unpacked["header"]["endpoint"],
                unpacked["body"],
                unpacked["header"].get("is_response", False),
            )
        except Exception as e:
            logger.error(f"Failed to deserialize message: {e}")
            raise VSPError(f"Message deserialization failed: {e}")
