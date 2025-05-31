import time
import logging

logger = logging.getLogger(__name__)

class ServiceInfo:
    def __init__(self, name: str, host: str, port: int, weight: int = 1):
        self.name = name
        self.host = host
        self.port = port
        self.weight = weight
        self.is_healthy: bool = True
        self.last_health_check: float = time.time()

    def mark_unhealthy(self) -> None:
        self.is_healthy = False
        logger.warning(f"Service {self.name} at {self.host}:{self.port} marked unhealthy")
        self.last_health_check = time.time()

    def mark_healthy(self) -> None:
        self.is_healthy = True
        logger.info(f"Service {self.name} at {self.host}:{self.port} marked healthy")
        self.last_health_check = time.time()