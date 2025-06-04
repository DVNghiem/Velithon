from abc import ABC, abstractmethod
from typing import List

from velithon._velithon import ServiceInfo


class Transport(ABC):
    """Abstract Transport interface for VSP communication."""

    @abstractmethod
    async def connect(self, host: str, port: str) -> None:
        """Connect to the specified host and port."""
        pass

    @abstractmethod
    def send(self, message: bytes) -> None:
        """Send a VSP message."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the transport."""
        pass

    @abstractmethod
    def is_closed(self) -> bool:
        """Check if the transport is closed."""
        pass


class Discovery(ABC):
    """Abstract Service Discovery interface."""

    @abstractmethod
    def register(self, service: ServiceInfo) -> None:
        """Register a service."""
        pass

    @abstractmethod
    async def query(self, service_name: str) -> List[ServiceInfo]:
        """Query service instances."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close discovery resources."""
        pass

