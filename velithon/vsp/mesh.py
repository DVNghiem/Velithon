"""Service mesh implementation for VSP (Velithon Service Protocol).

This module provides service mesh functionality including service routing,
load balancing, and inter-service communication patterns.
"""

import logging

from velithon._velithon import LoadBalancer, RoundRobinBalancer, ServiceInfo

from .discovery import ConsulDiscovery, DiscoveryType, MDNSDiscovery, StaticDiscovery

logger = logging.getLogger(__name__)


class ServiceMesh:
    """Service mesh for VSP with discovery and load balancing."""

    def __init__(
        self,
        discovery_type: DiscoveryType = DiscoveryType.STATIC,
        load_balancer: LoadBalancer | None = None,
        **discovery_args,
    ):
        """Initialize the service mesh with discovery and load balancing."""
        self.load_balancer = load_balancer or RoundRobinBalancer()
        if discovery_type == DiscoveryType.MDNS:
            self.discovery = MDNSDiscovery()
        elif discovery_type == DiscoveryType.CONSUL:
            self.discovery = ConsulDiscovery(**discovery_args)
        else:
            self.discovery = StaticDiscovery()
        logger.debug(f'Initialized ServiceMesh with {discovery_type} discovery')

    def register(self, service: ServiceInfo) -> None:
        """Register a service with the mesh."""
        self.discovery.register(service)
        logger.info(f'Registered {service.name} at {service.host}:{service.port}')

    async def query(self, service_name: str) -> ServiceInfo | None:
        """Query for a service instance by name."""
        instances = await self.discovery.query(service_name)
        healthy_instances = [s for s in instances if s.is_healthy]
        if not healthy_instances:
            logger.debug(f'No healthy instances for {service_name}')
            return None
        selected = self.load_balancer.select(healthy_instances)
        logger.debug(
            f'Queried {service_name}: selected {selected.host}:{selected.port}'
        )
        return selected

    def close(self) -> None:
        """Close the service mesh and clean up resources."""
        self.discovery.close()
        logger.debug('ServiceMesh closed')
