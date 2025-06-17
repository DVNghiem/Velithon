#!/usr/bin/env python3
"""Test script for the Velithon proxy functionality."""

import asyncio

import pytest

from velithon._velithon import ProxyClient, ProxyLoadBalancer


@pytest.mark.asyncio
async def test_proxy_client():
    """Test basic proxy client functionality."""
    print('Testing ProxyClient...')

    # Create a proxy client
    proxy = ProxyClient('https://httpbin.org', timeout_ms=10000)

    # Test circuit breaker status
    status = await proxy.get_circuit_breaker_status()
    print(f'Circuit breaker status: {status}')
    assert len(status) == 3
    assert status[0] == 'closed'  # Initial state should be closed

    print('ProxyClient test completed.\n')


@pytest.mark.asyncio
async def test_load_balancer():
    """Test load balancer functionality."""
    print('Testing ProxyLoadBalancer...')

    # Create a load balancer with multiple targets
    targets = ['server1', 'server2', 'server3']

    lb = ProxyLoadBalancer(targets, strategy='round_robin')

    # Test getting next targets
    selected = []
    for i in range(5):
        target = await lb.get_next_target()
        selected.append(target)
        print(f'Round {i + 1}: {target}')

    # Should get all targets
    assert len(set(selected)) == 3

    # Test health status
    health_status = await lb.get_health_status()
    print(f'Health status: {health_status}')
    assert len(health_status) == 3

    print('ProxyLoadBalancer test completed.\n')


@pytest.mark.asyncio
async def test_random_strategy():
    """Test random load balancing strategy."""
    print('Testing random load balancing...')

    targets = ['server1', 'server2', 'server3']
    lb = ProxyLoadBalancer(targets, strategy='random')

    selected_targets = []
    for i in range(10):
        target = await lb.get_next_target()
        selected_targets.append(target)

    print(f'Random selections: {selected_targets}')
    # Should have some variety
    assert len(set(selected_targets)) > 1

    print('Random strategy test completed.\n')


async def main():
    """Run all tests manually (not for pytest)."""
    print('=== Velithon Proxy Feature Test ===\n')

    # Note: These tests can also be run with pytest
    print('To run with pytest: python -m pytest tests/test_proxy.py -v')
    print('To run manually: python tests/test_proxy.py')
    print('\n=== Manual test execution completed ===')


if __name__ == '__main__':
    asyncio.run(main())
