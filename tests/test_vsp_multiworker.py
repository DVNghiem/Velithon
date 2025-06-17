"""Test VSP multi-worker functionality."""

import asyncio

import pytest

from velithon.vsp import VSPManager


class TestVSPMultiWorker:
    """Test VSP multi-worker functionality."""

    @pytest.mark.asyncio
    async def test_port_sharing_enabled(self):
        """Test that multiple VSP managers can share the same port with reuse_port=True."""
        manager1 = VSPManager('service1', num_workers=2)
        manager2 = VSPManager('service2', num_workers=2)

        @manager1.vsp_service('test1')
        async def test_endpoint1() -> dict:
            return {'message': 'from service1'}

        @manager2.vsp_service('test2')
        async def test_endpoint2() -> dict:
            return {'message': 'from service2'}

        # Both should be able to bind to the same port with reuse_port=True
        task1 = asyncio.create_task(
            manager1.start_server('127.0.0.1', 8003, reuse_port=True)
        )
        await asyncio.sleep(0.1)  # Give first server time to bind

        task2 = asyncio.create_task(
            manager2.start_server('127.0.0.1', 8003, reuse_port=True)
        )

        # Wait to ensure both servers start
        await asyncio.sleep(0.5)

        # Cleanup
        task1.cancel()
        task2.cancel()

        # Ensure tasks are properly cancelled
        with pytest.raises(asyncio.CancelledError):
            await task1
        with pytest.raises(asyncio.CancelledError):
            await task2

    @pytest.mark.asyncio
    async def test_port_sharing_disabled_fails(self):
        """Test that multiple VSP managers cannot share the same port with reuse_port=False."""
        manager1 = VSPManager('service1', num_workers=2)
        manager2 = VSPManager('service2', num_workers=2)

        @manager1.vsp_service('test1')
        async def test_endpoint1() -> dict:
            return {'message': 'from service1'}

        @manager2.vsp_service('test2')
        async def test_endpoint2() -> dict:
            return {'message': 'from service2'}

        # First server should bind successfully
        task1 = asyncio.create_task(
            manager1.start_server('127.0.0.1', 8004, reuse_port=False)
        )
        await asyncio.sleep(0.1)  # Give first server time to bind

        # Second server should fail with "address already in use"
        with pytest.raises(OSError) as exc_info:
            await manager2.start_server('127.0.0.1', 8004, reuse_port=False)

        assert 'address already in use' in str(exc_info.value).lower()

        # Cleanup
        task1.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task1

    @pytest.mark.asyncio
    async def test_default_reuse_port_behavior(self):
        """Test that reuse_port=True is the default behavior."""
        manager = VSPManager('service', num_workers=2)

        @manager.vsp_service('test')
        async def test_endpoint() -> dict:
            return {'message': 'test'}

        # Should work with default parameters (reuse_port=True by default)
        task = asyncio.create_task(manager.start_server('127.0.0.1', 8005))
        await asyncio.sleep(0.1)

        # Cleanup
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
