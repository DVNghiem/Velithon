import logging
import random
from abc import ABC, abstractmethod
from typing import List
from .mesh import ServiceInfo

logger = logging.getLogger(__name__)

class LoadBalancer(ABC):
    """Abstract Load Balancer interface."""
    @abstractmethod
    def select(self, instances: List[ServiceInfo]) -> ServiceInfo:
        """Select a service instance."""
        pass

class RoundRobinBalancer(LoadBalancer):
    """Round-Robin Load Balancer."""
    def __init__(self):
        self.index = 0

    def select(self, instances: List[ServiceInfo]) -> ServiceInfo:
        if not instances:
            raise ValueError("No instances available")
        self.index = (self.index + 1) % len(instances)
        selected = instances[self.index]
        logger.debug(f"Round-Robin selected {selected.name} at {selected.host}:{selected.port}")
        return selected

class WeightedBalancer(LoadBalancer):
    """Weighted Load Balancer based on instance weight."""
    def select(self, instances: List[ServiceInfo]) -> ServiceInfo:
        if not instances:
            raise ValueError("No instances available")
        weights = [s.weight for s in instances]
        selected = random.choices(instances, weights=weights, k=1)[0]
        logger.debug(f"Weighted selected {selected.name} at {selected.host}:{selected.port}")
        return selected