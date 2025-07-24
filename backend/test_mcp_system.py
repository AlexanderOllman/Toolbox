#!/usr/bin/env python3
"""
Simple test script to demonstrate the new MCP testing system.

This script shows how to:
1. Test an MCP server in an isolated container
2. Use the new clean API
3. Get comprehensive test results

Usage: python test_mcp_system.py [repo_name]
"""

import asyncio
import sys
import json
from pathlib import Path

# Add the app directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from app.services.mcp_test_runner import mcp_test_runner
from app.services.mcp_container_service import mcp_container_service

async def test_mcp_repository(repo_name: str):
    """Test a single MCP repository."""
    
    print(f"🚀 Starting MCP test for repository: {repo_name}")
    print("=" * 60)
    
    try:
        # Run the test
        report = await mcp_test_runner.test_repository(repo_name)
        
        # Display results
        print(f"📊 Test Results for {repo_name}")
        print(f"   Image: {report.image_name}")
        print(f"   Total Tests: {report.total_tests}")
        print(f"   Passed: {report.passed_tests}")
        print(f"   Failed: {report.failed_tests}")
        print(f"   Success Rate: {report.success_rate:.1f}%")
        print(f"   Execution Time: {report.execution_time_ms}ms")
        print()
        
        if report.error_message:
            print(f"❌ Error: {report.error_message}")
            if report.container_logs:
                print("📋 Container Logs:")
                print(report.container_logs)
            return False
        
        # Show discovered tools
        if report.tools_discovered:
            print(f"🔧 Discovered {len(report.tools_discovered)} tools:")
            for tool in report.tools_discovered:
                print(f"   - {tool['name']}: {tool['description']}")
            print()
        
        # Show test results
        if report.test_results:
            print("🧪 Individual Test Results:")
            for result in report.test_results:
                status = "✅" if result.success else "❌"
                print(f"   {status} {result.tool_name} ({result.test_type}): {result.execution_time_ms}ms")
                if not result.success and result.error_message:
                    print(f"      Error: {result.error_message}")
            print()
        
        # Show container logs if available
        if report.container_logs and len(report.container_logs.strip()) > 0:
            print("📋 Container Logs (last 1000 chars):")
            print(report.container_logs[-1000:])
            print()
        
        print(f"✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def demonstrate_system():
    """Demonstrate the MCP testing system with available repositories."""
    
    print("🧪 MCP Testing System Demonstration")
    print("=" * 60)
    
    # Check system status
    try:
        mcp_container_service._check_docker()
        print("✅ Docker connectivity: OK")
    except Exception as e:
        print(f"❌ Docker connectivity: FAILED - {e}")
        return
    
    # List available repositories for testing
    from app.services.database import get_repositories
    repos = get_repositories()
    
    if not repos:
        print("⚠️  No repositories found in database.")
        print("   Please add some repositories first using the web interface.")
        return
    
    print(f"📚 Found {len(repos)} repositories:")
    for i, repo in enumerate(repos[:5]):  # Show first 5
        print(f"   {i+1}. {repo['name']} - {repo.get('description', 'No description')[:60]}...")
    
    if len(repos) > 5:
        print(f"   ... and {len(repos) - 5} more")
    print()
    
    # Test the first repository as an example
    first_repo = repos[0]
    repo_name = first_repo['name']
    
    print(f"🎯 Testing first repository as demonstration: {repo_name}")
    print()
    
    success = await test_mcp_repository(repo_name)
    
    # Show cleanup
    print("🧹 Cleaning up test containers...")
    await mcp_container_service.cleanup_all()
    print("✅ Cleanup completed")
    
    return success

async def main():
    """Main entry point."""
    
    if len(sys.argv) > 1:
        # Test specific repository
        repo_name = sys.argv[1]
        try:
            success = await test_mcp_repository(repo_name)
            await mcp_container_service.cleanup_all()
            sys.exit(0 if success else 1)
        except KeyboardInterrupt:
            print("\n🛑 Test interrupted by user")
            await mcp_container_service.cleanup_all()
            sys.exit(1)
    else:
        # Demonstrate the system
        try:
            success = await demonstrate_system()
            sys.exit(0 if success else 1)
        except KeyboardInterrupt:
            print("\n🛑 Demonstration interrupted by user")
            await mcp_container_service.cleanup_all()
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 