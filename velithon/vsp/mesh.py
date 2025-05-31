import logging
import time
from typing import Dict, Optional, List
from .load_balancer import LoadBalancer, RoundRobinBalancer
from .discovery import Discovery, StaticDiscovery, MDNSDiscovery, ConsulDiscovery

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

class ServiceMesh:
    def __init__(self, discovery_type: str = "static", load_balancer: Optional[LoadBalancer] = None, **discovery_args):
        self.load_balancer = load_balancer or RoundRobinBalancer()
        if discovery_type == "mdns":
            self.discovery = MDNSDiscovery()
        elif discovery_type == "consul":
            self.discovery = ConsulDiscovery(**discovery_args)
        else:
            self.discovery = StaticDiscovery()
        logger.debug(f"Initialized ServiceMesh with {discovery_type} discovery")

    def register(self, service: ServiceInfo) -> None:
        self.discovery.register(service)
        logger.info(f"Registered {service.name} at {service.host}:{service.port}")

    async def query(self, service_name: str) -> Optional[ServiceInfo]:
        instances = await self.discovery.query(service_name)
        healthy_instances = [s for s in instances if s.is_healthy]
        if not healthy_instances:
            logger.debug(f"No healthy instances for {service_name}")
            return None
        selected = self.load_balancer.select(healthy_instances)
        logger.debug(f"Queried {service_name}: selected {selected.host}:{selected.port}")
        return selected

    def close(self) -> None:
        self.discovery.close()
        logger.debug("ServiceMesh closed")