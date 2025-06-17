#!/usr/bin/env python3
"""
Comprehensive test suite for Velithon proxy feature.

Tests all components: ProxyClient, ProxyLoadBalancer, and ProxyMiddleware.
"""

import asyncio
from unittest.mock import Mock

import pytest

from velithon._velithon import ProxyClient, ProxyLoadBalancer
from velithon.middleware.proxy import ProxyMiddleware


class TestProxyClient:
    """Test cases for ProxyClient."""

    @pytest.mark.asyncio
    async def test_proxy_client_creation(self):
        """Test ProxyClient instantiation with default parameters."""
        client = ProxyClient('https://example.com')
        assert client is not None

        # Test circuit breaker status
        status = await client.get_circuit_breaker_status()
        assert len(status) == 3
        assert status[0] == 'closed'  # Initial state should be closed
        assert status[1] == 0  # No failures initially

    @pytest.mark.asyncio
    async def test_proxy_client_custom_config(self):
        """Test ProxyClient with custom configuration."""
        client = ProxyClient(
            target_url='https://api.example.com',
            timeout_ms=15000,
            max_retries=5,
            max_failures=3,
            recovery_timeout_ms=30000,
        )
        assert client is not None

        # Circuit breaker should be in closed state initially
        status = await client.get_circuit_breaker_status()
        assert status[0] == 'closed'

    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self):
        """Test circuit breaker reset functionality."""
        client = ProxyClient('https://example.com')

        # Reset circuit breaker
        await client.reset_circuit_breaker()

        # Check status after reset
        status = await client.get_circuit_breaker_status()
        assert status[0] == 'closed'
        assert status[1] == 0


class TestProxyLoadBalancer:
    """Test cases for ProxyLoadBalancer."""

    @pytest.mark.asyncio
    async def test_load_balancer_creation(self):
        """Test ProxyLoadBalancer instantiation."""
        targets = ['server1', 'server2', 'server3']
        lb = ProxyLoadBalancer(targets)
        assert lb is not None

    @pytest.mark.asyncio
    async def test_round_robin_strategy(self):
        """Test round-robin load balancing strategy."""
        targets = ['server1', 'server2', 'server3']
        lb = ProxyLoadBalancer(targets, strategy='round_robin')

        # Get multiple targets and verify round-robin behavior
        selected = []
        for _ in range(6):  # Two full rounds
            target = await lb.get_next_target()
            selected.append(target)

        # Should cycle through all targets
        assert len(set(selected)) == 3  # All targets should be selected
        assert selected[0] != selected[1]  # Should be different targets

    @pytest.mark.asyncio
    async def test_random_strategy(self):
        """Test random load balancing strategy."""
        targets = ['server1', 'server2', 'server3']
        lb = ProxyLoadBalancer(targets, strategy='random')

        # Get multiple targets
        selected = []
        for _ in range(20):
            target = await lb.get_next_target()
            selected.append(target)

        # Should have some variety (not all the same)
        assert len(set(selected)) > 1

    @pytest.mark.asyncio
    async def test_weighted_strategy(self):
        """Test weighted load balancing strategy."""
        targets = ['server1', 'server2']
        weights = [80, 20]  # server1 should get ~80% of traffic

        lb = ProxyLoadBalancer(targets, strategy='weighted', weights=weights)

        # Get many targets to test distribution
        selected = []
        for _ in range(100):
            target = await lb.get_next_target()
            selected.append(target)

        # Should select both servers
        assert 'server1' in selected
        assert 'server2' in selected

    @pytest.mark.asyncio
    async def test_health_status(self):
        """Test health status tracking."""
        targets = ['server1', 'server2']
        lb = ProxyLoadBalancer(targets)

        # Get initial health status
        health = await lb.get_health_status()
        assert len(health) == 2
        assert all(isinstance(item, tuple) and len(item) == 2 for item in health)

    @pytest.mark.asyncio
    async def test_empty_targets_error(self):
        """Test error when no targets provided."""
        with pytest.raises(Exception):
            ProxyLoadBalancer([])

    @pytest.mark.asyncio
    async def test_invalid_strategy_error(self):
        """Test error for invalid load balancing strategy."""
        with pytest.raises(Exception):
            ProxyLoadBalancer(['server1'], strategy='invalid_strategy')

    @pytest.mark.asyncio
    async def test_weighted_without_weights_error(self):
        """Test error for weighted strategy without weights."""
        with pytest.raises(Exception):
            ProxyLoadBalancer(['server1', 'server2'], strategy='weighted')


class TestProxyMiddleware:
    """Test cases for ProxyMiddleware."""

    @pytest.mark.asyncio
    async def test_middleware_creation(self):
        """Test ProxyMiddleware instantiation."""
        mock_app = Mock()
        middleware = ProxyMiddleware(
            mock_app, targets=['https://api.example.com'], enable_health_checks=False
        )
        assert middleware is not None

    @pytest.mark.asyncio
    async def test_middleware_with_multiple_targets(self):
        """Test ProxyMiddleware with multiple targets."""
        mock_app = Mock()
        middleware = ProxyMiddleware(
            mock_app,
            targets=['https://api1.example.com', 'https://api2.example.com'],
            load_balancing_strategy='round_robin',
            enable_health_checks=False,
        )
        assert middleware is not None

    @pytest.mark.asyncio
    async def test_middleware_with_custom_config(self):
        """Test ProxyMiddleware with custom configuration."""
        mock_app = Mock()
        middleware = ProxyMiddleware(
            mock_app,
            targets=['https://api.example.com'],
            timeout_ms=15000,
            max_retries=2,
            health_check_interval=60,
            path_prefix='/api',
            upstream_path_prefix='/v1',
            enable_health_checks=False,
        )
        assert middleware is not None

    @pytest.mark.asyncio
    async def test_middleware_health_checks_enabled(self):
        """Test ProxyMiddleware with health checks enabled."""
        mock_app = Mock()
        middleware = ProxyMiddleware(
            mock_app,
            targets=['https://api.example.com'],
            enable_health_checks=True,
            health_check_interval=1,  # Short interval for testing
        )
        assert middleware is not None
        assert middleware.enable_health_checks is True

        # Clean up the health check task
        await middleware.cleanup()


class TestProxyIntegration:
    """Integration tests for proxy components."""

    @pytest.mark.asyncio
    async def test_client_and_load_balancer_integration(self):
        """Test ProxyClient and ProxyLoadBalancer working together."""
        # Create load balancer
        targets = ['https://api1.example.com', 'https://api2.example.com']
        lb = ProxyLoadBalancer(targets)

        # Get target from load balancer
        target = await lb.get_next_target()
        assert target in targets

        # Create proxy client for the selected target
        client = ProxyClient(target)
        assert client is not None

        # Check circuit breaker status
        status = await client.get_circuit_breaker_status()
        assert status[0] == 'closed'


class TestProxyPerformance:
    """Performance tests for proxy components."""

    @pytest.mark.asyncio
    async def test_load_balancer_performance(self):
        """Test load balancer performance with many targets."""
        # Create load balancer with many targets
        targets = [f'server{i}' for i in range(100)]
        lb = ProxyLoadBalancer(targets, strategy='round_robin')

        # Time target selection
        import time

        start_time = time.time()

        for _ in range(1000):
            await lb.get_next_target()

        elapsed = time.time() - start_time

        # Should complete quickly (less than 1 second for 1000 selections)
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_concurrent_load_balancer_access(self):
        """Test concurrent access to load balancer."""
        targets = ['server1', 'server2', 'server3']
        lb = ProxyLoadBalancer(targets)

        # Run concurrent target selections
        async def get_target():
            return await lb.get_next_target()

        tasks = []
        for _ in range(50):
            task = asyncio.create_task(get_target())
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert len(results) == 50
        assert all(result in targets for result in results)


if __name__ == '__main__':
    # Run tests with pytest
    print('Run with: pytest test_proxy_comprehensive.py -v')
    print('Or run individual test classes:')
    print('  pytest test_proxy_comprehensive.py::TestProxyClient -v')
    print('  pytest test_proxy_comprehensive.py::TestProxyLoadBalancer -v')
    print('  pytest test_proxy_comprehensive.py::TestProxyMiddleware -v')
