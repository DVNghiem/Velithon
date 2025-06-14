"""
Example demonstrating VSP multi-worker support with port sharing.

This example shows how to run multiple VSP services on the same port
using the SO_REUSEPORT socket option, which is essential for multi-worker
Velithon applications.
"""

import asyncio
import logging

from velithon.vsp import VSPManager

# Configure logging to see the server startup messages
logging.basicConfig(level=logging.INFO)


async def example_multi_worker_vsp():
    """Demonstrate multiple VSP managers sharing the same port."""
    # Create multiple VSP managers (simulating multiple workers)
    worker1_manager = VSPManager("worker-1", num_workers=2)
    worker2_manager = VSPManager("worker-2", num_workers=2)
    
    # Define services for each worker
    @worker1_manager.vsp_service("worker1_info")
    async def worker1_info() -> dict:
        return {
            "worker_id": 1,
            "status": "healthy",
            "services": ["worker1_info", "shared_health"]
        }
    
    @worker1_manager.vsp_service("shared_health")
    async def shared_health_worker1() -> dict:
        return {"worker": 1, "health": "ok", "timestamp": asyncio.get_event_loop().time()}
    
    @worker2_manager.vsp_service("worker2_info")
    async def worker2_info() -> dict:
        return {
            "worker_id": 2,
            "status": "healthy", 
            "services": ["worker2_info", "shared_health"]
        }
    
    @worker2_manager.vsp_service("shared_health")
    async def shared_health_worker2() -> dict:
        return {"worker": 2, "health": "ok", "timestamp": asyncio.get_event_loop().time()}
    
    print("Starting multiple VSP servers on the same port...")
    print("This demonstrates port sharing for multi-worker deployments.")
    
    # Start both servers on the same port - this works with reuse_port=True
    tasks = []
    
    try:
        # Worker 1 starts first
        task1 = asyncio.create_task(
            worker1_manager.start_server("127.0.0.1", 8010, reuse_port=True)
        )
        tasks.append(task1)
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Worker 2 starts on the same port
        task2 = asyncio.create_task(
            worker2_manager.start_server("127.0.0.1", 8010, reuse_port=True)
        )
        tasks.append(task2)
        
        print("\n✅ Both VSP servers started successfully!")
        print("📋 Key benefits of port sharing:")
        print("   • Multiple worker processes can bind to the same port")
        print("   • Load balancing is handled by the kernel (SO_REUSEPORT)")
        print("   • Eliminates 'port already in use' errors in multi-worker setups")
        print("   • Enables horizontal scaling of VSP services")
        
        print("\n🔗 Both services are now available on port 8010")
        print("   • worker1_info and shared_health (from worker 1)")
        print("   • worker2_info and shared_health (from worker 2)")
        
        # Let servers run for a few seconds
        await asyncio.sleep(3)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean shutdown
        print("\n🛑 Shutting down servers...")
        for task in tasks:
            task.cancel()
        
        # Wait for tasks to complete cancellation
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        print("✅ Servers shut down successfully")


async def example_without_port_sharing():
    """Show what happens without port sharing (for comparison)."""
    print("\n" + "="*60)
    print("COMPARISON: Without port sharing (reuse_port=False)")
    print("="*60)
    
    manager1 = VSPManager("no-sharing-1", num_workers=1)
    manager2 = VSPManager("no-sharing-2", num_workers=1)
    
    @manager1.vsp_service("test")
    async def test1() -> dict:
        return {"manager": 1}
    
    @manager2.vsp_service("test")
    async def test2() -> dict:
        return {"manager": 2}
    
    try:
        # First server binds successfully
        task1 = asyncio.create_task(
            manager1.start_server("127.0.0.1", 8011, reuse_port=False)
        )
        await asyncio.sleep(0.1)
        
        print("✅ First server started successfully")
        
        # Second server should fail
        print("⏳ Attempting to start second server on same port...")
        await manager2.start_server("127.0.0.1", 8011, reuse_port=False)
        
    except OSError as e:
        if "address already in use" in str(e).lower():
            print(f"❌ Expected error: {e}")
            print("💡 This is why port sharing (reuse_port=True) is important!")
        else:
            print(f"❌ Unexpected error: {e}")
    finally:
        task1.cancel()
        try:
            await task1
        except asyncio.CancelledError:
            pass


async def main():
    """Run the examples."""
    print("🚀 VSP Multi-Worker Port Sharing Example")
    print("="*50)
    
    # Show the working solution
    await example_multi_worker_vsp()
    
    # Show what happens without port sharing
    await example_without_port_sharing()
    
    print("\n📚 Summary:")
    print("   • Use reuse_port=True (default) for multi-worker deployments")
    print("   • This enables SO_REUSEPORT socket option")
    print("   • Multiple processes can bind to the same port")
    print("   • Kernel handles load balancing between processes")
    print("   • Essential for production multi-worker Velithon applications")


if __name__ == "__main__":
    asyncio.run(main())
