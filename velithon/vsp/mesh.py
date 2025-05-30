import logging
import time
from typing import Dict, Optional, List
from .loadbalancer import LoadBalancer, RoundRobinBalancer

logger = logging.getLogger(__name__)

class ServiceInfo:
    def __init__(self, name: str, host: str, port: int, weight: int = 1):
        self.name = name
        self.host = host
        self.port = port
        self.weight = weight  # For weighted load balancing
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

class ServiceMesh:
    def __init__(self, load_balancer: Optional[LoadBalancer] = None):
        self.services: Dict[str, List[ServiceInfo]] = {}
        self.load_balancer = load_balancer or RoundRobinBalancer()

    def register(self, service: ServiceInfo) -> None:
        logger.debug(f"Registering service: {service.name} at {service.host}:{service.port}")
        if service.name not in self.services:
            self.services[service.name] = []
        if not any(s.host == service.host and s.port == service.port for s in self.services[service.name]):
            self.services[service.name].append(service)
            logger.info(f"Registered {service.name} at {service.host}:{service.port}")

    async def query(self, service_name: str) -> Optional[ServiceInfo]:
        instances = [s for s in self.services.get(service_name, []) if s.is_healthy]
        if not instances:
            logger.debug(f"No healthy instances for {service_name}")
            return None
        selected = self.load_balancer.select(instances)
        logger.debug(f"Queried {service_name}: selected {selected.host}:{selected.port}")
        return selected