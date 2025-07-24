#!/usr/bin/env python3
"""
Demonstration of the automatic MCP testing system.

This script shows how repositories are automatically tested when added.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.mcp_auto_test import mcp_auto_test_service
from app.services.database import get_repositories, get_repository

async def demonstrate_auto_testing():
    """Demonstrate the automatic testing system."""
    
    print("🧪 MCP Automatic Testing System Demonstration")
    print("=" * 60)
    
    # Check if auto-testing is enabled
    if mcp_auto_test_service.is_testing_enabled():
        print("✅ Automatic testing is ENABLED")
    else:
        print("❌ Automatic testing is DISABLED")
        print("   Enabling for demonstration...")
        mcp_auto_test_service.set_testing_enabled(True)
    
    print()
    
    # Show current status
    status = mcp_auto_test_service.get_testing_status()
    print(f"📊 Testing Status:")
    print(f"   Testing Enabled: {status['testing_enabled']}")
    print(f"   Running Tests: {status['running_test_count']}")
    if status['running_tests']:
        print(f"   Currently Testing: {', '.join(status['running_tests'])}")
    print()
    
    # Show repositories and their test status
    repos = get_repositories()
    if not repos:
        print("⚠️  No repositories found in database.")
        print("   Add some repositories to see automatic testing in action!")
        return
    
    print(f"📚 Found {len(repos)} repositories:")
    print()
    
    for repo in repos[:10]:  # Show first 10
        name = repo.get('name', 'Unknown')
        test_status = repo.get('test_status', 'pending')
        test_rate = repo.get('test_success_rate')
        tools_count = len(repo.get('tools_discovered', []))
        last_tested = repo.get('last_tested_at')
        is_external = repo.get('is_external_config', False)
        
        # Status emoji
        if test_status == 'completed':
            status_emoji = "✅"
        elif test_status == 'failed':
            status_emoji = "❌"
        elif test_status == 'running':
            status_emoji = "🔄"
        else:
            status_emoji = "⏳"
        
        print(f"   {status_emoji} {name}")
        print(f"      Status: {test_status}")
        if test_rate is not None:
            print(f"      Success Rate: {test_rate:.1f}%")
        if tools_count > 0:
            print(f"      Tools Discovered: {tools_count}")
        if last_tested:
            print(f"      Last Tested: {last_tested[:19].replace('T', ' ')}")
        if is_external:
            print(f"      Type: External Config (not auto-tested)")
        print()
    
    if len(repos) > 10:
        print(f"   ... and {len(repos) - 10} more repositories")
        print()
    
    # Show what happens when a repository is added
    print("💡 How Automatic Testing Works:")
    print("   1. When you add a repository via API or web interface")
    print("   2. System checks if it's eligible for testing (not external config)")
    print("   3. Test is triggered as a background task")
    print("   4. Repository is containerized and MCP tools are discovered")
    print("   5. All tools are tested automatically")
    print("   6. Results are saved to the repository record")
    print()
    
    # Show example API calls
    print("🚀 Try These API Calls:")
    print("   # Get auto-test status")
    print("   curl http://localhost:8020/api/mcp/auto-test/status")
    print()
    print("   # View all test results")
    print("   curl http://localhost:8020/api/mcp/results")
    print()
    print("   # Manually re-test a repository")
    print("   curl -X POST http://localhost:8020/api/mcp/retest/REPO_NAME")
    print()
    print("   # Disable automatic testing")
    print("   curl -X POST http://localhost:8020/api/mcp/auto-test/disable")
    print()
    
    # Show repository with detailed test results
    completed_repos = [r for r in repos if r.get('test_status') == 'completed']
    if completed_repos:
        repo = completed_repos[0]
        print(f"📋 Detailed Test Results for '{repo['name']}':")
        
        test_results = repo.get('test_results', {})
        tools = repo.get('tools_discovered', [])
        
        if test_results:
            print(f"   Total Tests: {test_results.get('total_tests', 0)}")
            print(f"   Passed: {test_results.get('passed_tests', 0)}")
            print(f"   Failed: {test_results.get('failed_tests', 0)}")
            print(f"   Execution Time: {test_results.get('execution_time_ms', 0)}ms")
            
            if tools:
                print(f"   Discovered Tools:")
                for tool in tools[:5]:  # Show first 5 tools
                    print(f"     - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')[:60]}...")
                if len(tools) > 5:
                    print(f"     ... and {len(tools) - 5} more tools")
        print()
    
    print("✨ That's how automatic MCP testing keeps your server pool healthy!")

if __name__ == "__main__":
    asyncio.run(demonstrate_auto_testing()) 