import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import asdict

from .mcp_test_runner import mcp_test_runner
from .database import update_repository_test_results, update_repository_fields

logger = logging.getLogger(__name__)

class MCPAutoTestService:
    """
    Service for automatically testing MCP repositories when they're added.
    Runs tests in the background and updates repository records with results.
    """
    
    def __init__(self):
        self.testing_enabled = True
        self.running_tests = set()  # Track repos currently being tested
    
    def set_testing_enabled(self, enabled: bool):
        """Enable or disable automatic testing."""
        self.testing_enabled = enabled
        logger.info(f"Automatic MCP testing {'enabled' if enabled else 'disabled'}")
    
    def is_testing_enabled(self) -> bool:
        """Check if automatic testing is enabled."""
        return self.testing_enabled
    
    def is_test_running(self, repo_name: str) -> bool:
        """Check if a test is currently running for a repository."""
        return repo_name in self.running_tests
    
    async def test_repository_async(self, repo_name: str, test_config: Optional[Dict[str, Any]] = None):
        """
        Run MCP test for a repository in the background.
        This is designed to be called as a FastAPI background task.
        """
        if not self.testing_enabled:
            logger.info(f"Automatic testing disabled, skipping test for '{repo_name}'")
            return
        
        if self.is_test_running(repo_name):
            logger.warning(f"Test already running for '{repo_name}', skipping")
            return
        
        logger.info(f"Starting automatic MCP test for repository: {repo_name}")
        
        # Mark test as running
        self.running_tests.add(repo_name)
        
        # Update repository status to indicate testing is in progress
        update_repository_fields(repo_name, {
            "test_status": "running"
        })
        
        try:
            # Run the test
            report = await mcp_test_runner.test_repository(
                repo_name=repo_name,
                test_config=test_config
            )
            
            # Convert dataclass to dict for storage
            report_dict = asdict(report)
            
            # Update repository with test results
            success = update_repository_test_results(repo_name, report_dict)
            
            if success:
                logger.info(f"Automatic test completed for '{repo_name}': "
                          f"{report.passed_tests}/{report.total_tests} tests passed "
                          f"({report.success_rate:.1f}% success rate)")
            else:
                logger.error(f"Failed to save test results for '{repo_name}'")
                
        except Exception as e:
            logger.error(f"Automatic test failed for '{repo_name}': {e}", exc_info=True)
            
            # Update repository with failure status
            update_repository_fields(repo_name, {
                "test_status": "failed",
                "test_results": {
                    "error_message": f"Test execution failed: {e}",
                    "total_tests": 0,
                    "passed_tests": 0,
                    "failed_tests": 0,
                    "success_rate": 0.0
                }
            })
            
        finally:
            # Remove from running tests
            self.running_tests.discard(repo_name)
    
    def should_auto_test_repository(self, repo_data: Dict[str, Any]) -> bool:
        """
        Determine if a repository should be automatically tested.
        
        Only test repositories that:
        - Are not external configurations
        - Have a local path (are cloned)
        - Are not already being tested
        """
        repo_name = repo_data.get("name", "")
        
        # Skip external configurations
        if repo_data.get("is_external_config", False):
            logger.debug(f"Skipping auto-test for external config: {repo_name}")
            return False
        
        # Skip if already testing
        if self.is_test_running(repo_name):
            logger.debug(f"Test already running for: {repo_name}")
            return False
        
        # Skip if testing is disabled
        if not self.testing_enabled:
            logger.debug(f"Auto-testing disabled, skipping: {repo_name}")
            return False
        
        logger.debug(f"Repository '{repo_name}' eligible for auto-testing")
        return True
    
    def trigger_auto_test(self, repo_name: str, background_tasks, test_config: Optional[Dict[str, Any]] = None):
        """
        Trigger an automatic test as a FastAPI background task.
        
        Args:
            repo_name: Name of the repository to test
            background_tasks: FastAPI BackgroundTasks instance
            test_config: Optional test configuration
        """
        if not self.testing_enabled:
            logger.debug(f"Auto-testing disabled for: {repo_name}")
            return
        
        logger.info(f"Triggering automatic MCP test for: {repo_name}")
        background_tasks.add_task(self.test_repository_async, repo_name, test_config)
    
    async def retest_repository(self, repo_name: str, test_config: Optional[Dict[str, Any]] = None):
        """
        Manually re-test a repository (not as background task).
        This can be called from API endpoints for manual re-testing.
        """
        logger.info(f"Manual re-test triggered for repository: {repo_name}")
        await self.test_repository_async(repo_name, test_config)
    
    def get_testing_status(self) -> Dict[str, Any]:
        """Get current status of the auto-testing service."""
        return {
            "testing_enabled": self.testing_enabled,
            "running_tests": list(self.running_tests),
            "running_test_count": len(self.running_tests)
        }

# Global instance
mcp_auto_test_service = MCPAutoTestService() 