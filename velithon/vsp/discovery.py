import enum
import logging
from typing import List

from velithon._velithon import ServiceInfo

from .abstract import Discovery

try:
    from zeroconf import ServiceInfo as ZeroconfServiceInfo
    from zeroconf import Zeroconf
except ImportError:
    Zeroconf = None
try:
    import consul
except ImportError:
    consul = None

logger = logging.getLogger(__name__)

class DiscoveryType(str, enum.Enum):
    """Enumeration of discovery types."""

    STATIC = "static"
    MDNS = "mdns"
    CONSUL = "consul"

class StaticDiscovery(Discovery):
    """Static discovery using pre-configured services."""

    def __init__(self):
        self.services: dict[str, List[ServiceInfo]] = {}

    def register(self, service: ServiceInfo) -> None:
        if service.name not in self.services:
            self.services[service.name] = []
        if not any(s.host == service.host and s.port == service.port for s in self.services[service.name]):
            self.services[service.name].append(service)
            logger.debug(f"Static registered {service.name} at {service.host}:{service.port}")

    async def query(self, service_name: str) -> List[ServiceInfo]:
        instances = self.services.get(service_name, [])
        logger.debug(f"Static queried {service_name}: found {len(instances)} instances")
        return instances

    def close(self) -> None:
        logger.debug("Static discovery closed")

class MDNSDiscovery(Discovery):
    """mDNS discovery using zeroconf."""

    def __init__(self):
        if Zeroconf is None:
            raise ImportError("zeroconf package is required for mDNS discovery")
        self.zeroconf = Zeroconf()
        self.services: dict[str, List[ServiceInfo]] = {}
        self.service_type = "_vsp._tcp.local."

    def register(self, service: ServiceInfo) -> None:
        service_name = f"{service.name}.{self.service_type}"
        info = ZeroconfServiceInfo(
            type_=self.service_type,
            name=service_name,
            addresses=[bytearray([int(x) for x in service.host.split(".")])],
            port=service.port,
            properties={"weight": str(service.weight)},
        )
        self.zeroconf.register_service(info)
        if service.name not in self.services:
            self.services[service.name] = []
        self.services[service.name].append(service)
        logger.info(f"mDNS registered {service.name} at {service.host}:{service.port}")

    async def query(self, service_name: str) -> List[ServiceInfo]:
        instances = []
        service_name_full = f"{service_name}.{self.service_type}"
        try:
            services = self.zeroconf.get_service_info(self.service_type, service_name_full)
            if services:
                host = ".".join(str(x) for x in services.addresses[0])
                port = services.port
                weight = int(services.properties.get(b"weight", b"1").decode())
                instances.append(ServiceInfo(service_name, host, port, weight))
        except Exception as e:
            logger.warning(f"mDNS query failed for {service_name}: {e}")
        logger.debug(f"mDNS queried {service_name}: found {len(instances)} instances")
        return instances

    def close(self) -> None:
        self.zeroconf.close()
        logger.debug("mDNS discovery closed")

class ConsulDiscovery(Discovery):
    """Consul discovery using consul client."""

    def __init__(self, host: str = "localhost", port: int = 8500):
        if consul is None:
            raise ImportError("consul package is required for Consul discovery")
        self.consul = consul.Consul(host=host, port=port)
        self.services: dict[str, List[ServiceInfo]] = {}

    def register(self, service: ServiceInfo) -> None:
        service_id = f"{service.name}-{service.host}:{service.port}"
        self.consul.agent.service.register(
            name=service.name,
            service_id=service_id,
            address=service.host,
            port=service.port,
            tags=[f"weight={service.weight}"],
            check=consul.Check.tcp(service.host, service.port, "10s")
        )
        if service.name not in self.services:
            self.services[service.name] = []
        self.services[service.name].append(service)
        logger.info(f"Consul registered {service.name} at {service.host}:{service.port}")

    async def query(self, service_name: str) -> List[ServiceInfo]:
        try:
            _, services = self.consul.catalog.service(service_name)
            instances = []
            for s in services:
                host = s["Address"]
                port = s["ServicePort"]
                weight = 1
                for tag in s.get("ServiceTags", []):
                    if tag.startswith("weight="):
                        weight = int(tag.split("=")[1])
                instances.append(ServiceInfo(service_name, host, port, weight))
            logger.debug(f"Consul queried {service_name}: found {len(instances)} instances")
            return instances
        except Exception as e:
            logger.warning(f"Consul query failed for {service_name}: {e}")
            return []

    def close(self) -> None:
        logger.debug("Consul discovery closed")