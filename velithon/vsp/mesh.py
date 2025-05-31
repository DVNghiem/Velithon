import logging
from typing import Optional
from .load_balancer import LoadBalancer, RoundRobinBalancer
from .discovery import StaticDiscovery, MDNSDiscovery, ConsulDiscovery
from .service import ServiceInfo

logger = logging.getLogger(__name__)


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