import json
import logging
from typing import Any, Dict, Optional

from velithon.cache import create_lru_cache

# Try to import faster serialization libraries
try:
    import orjson

    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

try:
    import msgpack

    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False

logger = logging.getLogger(__name__)


class VSPError(Exception):
    pass


class VSPMessage:
    """VSP Message with faster serialization"""

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
        # Cache serialized form for repeated sends
        self._serialized_cache: Optional[bytes] = None

    @create_lru_cache(cache_type="message")
    def _fast_serialize_header(
        self, request_id: str, service: str, endpoint: str, is_response: bool
    ) -> dict:
        """Cache frequently used header combinations"""
        return {
            "request_id": request_id,
            "service": service,
            "endpoint": endpoint,
            "is_response": is_response,
        }

    def to_bytes(self) -> bytes:
        """Serialization with caching and fast backends"""
        if self._serialized_cache is not None:
            return self._serialized_cache

        data = {"header": self.header, "body": self.body}

        try:
            if HAS_ORJSON:
                # orjson is fastest for JSON
                result = orjson.dumps(data)
            elif HAS_MSGPACK:
                # msgpack is more compact
                result = msgpack.packb(data, use_bin_type=True)
            else:
                # Fallback to standard JSON
                result = json.dumps(data, separators=(",", ":")).encode("utf-8")

            # Cache small messages only to avoid memory bloat
            if len(result) < 1024:  # Only cache messages under 1KB
                self._serialized_cache = result

            return result
        except Exception as e:
            logger.error(f"Failed to serialize message: {e}")
            raise VSPError(f"Message serialization failed: {e}")

    @classmethod
    def from_bytes(cls, data: bytes) -> "VSPMessage":
        """Deserialization"""
        try:
            if HAS_ORJSON:
                unpacked = orjson.loads(data)
            elif HAS_MSGPACK:
                unpacked = msgpack.unpackb(data, raw=False)
            else:
                unpacked = json.loads(data.decode("utf-8"))

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

    def clear_cache(self) -> None:
        """Clear serialization cache"""
        self._serialized_cache = None

    def __repr__(self) -> str:
        return (
            f"VSPMessage(request_id={self.header['request_id']}, "
            f"service={self.header['service']}, "
            f"endpoint={self.header['endpoint']}, "
            f"is_response={self.header['is_response']})"
        )
