import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ConnectionPool:
    """High-performance connection pool with intelligent resource management"""
    
    def __init__(self, max_connections_per_service: int = 10, connection_timeout: float = 30.0):
        self.max_connections_per_service = max_connections_per_service
        self.connection_timeout = connection_timeout
        
        # Connection pools per service
        self.pools: Dict[str, deque] = defaultdict(deque)
        self.active_connections: Dict[str, int] = defaultdict(int)
        self.connection_creation_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        
        # Health tracking
        self.unhealthy_services: set = set()
        self.last_health_check: Dict[str, float] = {}
        
        # Performance metrics
        self.stats = {
            'connections_created': 0,
            'connections_reused': 0,
            'connections_expired': 0,
            'pool_hits': 0,
            'pool_misses': 0
        }

    async def get_connection(self, service_key: str, connection_factory) -> Any:
        """Get a connection from the pool or create a new one"""
        # Check if service is marked as unhealthy
        if service_key in self.unhealthy_services:
            # Retry unhealthy services every 30 seconds
            if time.time() - self.last_health_check.get(service_key, 0) < 30:
                raise ConnectionError(f"Service {service_key} is marked unhealthy")
            else:
                self.unhealthy_services.discard(service_key)
        
        # Try to get from pool first
        pool = self.pools[service_key]
        while pool:
            connection, created_at = pool.popleft()
            
            # Check if connection is still valid
            if time.time() - created_at < self.connection_timeout and not connection.is_closed():
                self.stats['connections_reused'] += 1
                self.stats['pool_hits'] += 1
                return connection
            else:
                # Connection expired or closed
                if not connection.is_closed():
                    connection.close()
                self.stats['connections_expired'] += 1
        
        self.stats['pool_misses'] += 1
        
        # Need to create new connection
        async with self.connection_creation_locks[service_key]:
            # Double-check pool after acquiring lock
            if pool:
                connection, created_at = pool.popleft()
                if time.time() - created_at < self.connection_timeout and not connection.is_closed():
                    self.stats['connections_reused'] += 1
                    return connection
                elif not connection.is_closed():
                    connection.close()
            
            # Create new connection if under limit
            if self.active_connections[service_key] < self.max_connections_per_service:
                try:
                    connection = await connection_factory()
                    self.active_connections[service_key] += 1
                    self.stats['connections_created'] += 1
                    return connection
                except Exception as e:
                    self.unhealthy_services.add(service_key)
                    self.last_health_check[service_key] = time.time()
                    logger.error(f"Failed to create connection to {service_key}: {e}")
                    raise
            else:
                raise ConnectionError(f"Maximum connections reached for {service_key}")

    def return_connection(self, service_key: str, connection: Any) -> None:
        """Return a connection to the pool"""
        if not connection.is_closed() and len(self.pools[service_key]) < self.max_connections_per_service:
            self.pools[service_key].append((connection, time.time()))
        else:
            # Pool is full or connection is closed
            if not connection.is_closed():
                connection.close()
            self.active_connections[service_key] = max(0, self.active_connections[service_key] - 1)

    def remove_connection(self, service_key: str, connection: Any) -> None:
        """Remove a connection permanently (e.g., due to error)"""
        if not connection.is_closed():
            connection.close()
        self.active_connections[service_key] = max(0, self.active_connections[service_key] - 1)

    def cleanup_expired_connections(self) -> None:
        """Clean up expired connections from all pools"""
        current_time = time.time()
        expired_count = 0
        
        for service_key, pool in self.pools.items():
            # Create new deque with only valid connections
            valid_connections = deque()
            
            while pool:
                connection, created_at = pool.popleft()
                if current_time - created_at < self.connection_timeout and not connection.is_closed():
                    valid_connections.append((connection, created_at))
                else:
                    if not connection.is_closed():
                        connection.close()
                    expired_count += 1
                    self.active_connections[service_key] = max(0, self.active_connections[service_key] - 1)
            
            self.pools[service_key] = valid_connections
        
        if expired_count > 0:
            logger.debug(f"Cleaned up {expired_count} expired connections")
            self.stats['connections_expired'] += expired_count

    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        total_pooled = sum(len(pool) for pool in self.pools.values())
        total_active = sum(self.active_connections.values())
        
        return {
            **self.stats,
            'total_pooled_connections': total_pooled,
            'total_active_connections': total_active,
            'services_count': len(self.pools),
            'unhealthy_services': len(self.unhealthy_services),
            'pool_hit_rate': self.stats['pool_hits'] / max(1, self.stats['pool_hits'] + self.stats['pool_misses'])
        }

    def close_all(self) -> None:
        """Close all connections and clean up"""
        for pool in self.pools.values():
            while pool:
                connection, _ = pool.popleft()
                if not connection.is_closed():
                    connection.close()
        
        self.pools.clear()
        self.active_connections.clear()
        self.connection_creation_locks.clear()
        self.unhealthy_services.clear()
        logger.info("All connections closed")


# Global connection pool instance
_connection_pool = ConnectionPool()


def get_connection_pool() -> ConnectionPool:
    """Get the global connection pool instance"""
    return _connection_pool
