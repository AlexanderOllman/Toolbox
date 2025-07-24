from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List, Optional, Any
import logging
from pydantic import BaseModel
from dataclasses import asdict

from app.services.mcp_test_runner import mcp_test_runner, MCPServerTestReport, TestResult
from app.services.mcp_container_service import mcp_container_service
from app.services.mcp_auto_test import mcp_auto_test_service

logger = logging.getLogger(__name__)

router = APIRouter()

class MCPTestConfig(BaseModel):
    """Configuration for MCP server testing."""
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env_vars: Optional[Dict[str, str]] = None
    timeout_seconds: Optional[int] = 60

class MCPTestRequest(BaseModel):
    """Request to test an MCP server."""
    repo_name: str
    test_config: Optional[MCPTestConfig] = None

class MCPTestResponse(BaseModel):
    """Response from MCP testing."""
    success: bool
    report: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class MCPBatchTestRequest(BaseModel):
    """Request to test multiple MCP servers."""
    repo_names: List[str]
    test_config: Optional[MCPTestConfig] = None

class MCPBatchTestResponse(BaseModel):
    """Response from batch MCP testing."""
    total_repos: int
    completed_repos: int
    reports: Dict[str, Dict[str, Any]]
    errors: Dict[str, str]

@router.post("/test", response_model=MCPTestResponse)
async def test_mcp_server(request: MCPTestRequest) -> MCPTestResponse:
    """
    Test a single MCP server in an isolated container.
    
    This endpoint:
    1. Validates the repository exists locally
    2. Builds/runs it in an isolated Docker container  
    3. Connects via MCP protocol
    4. Discovers and tests all available tools
    5. Returns comprehensive test results
    """
    logger.info(f"Starting MCP test for repository: {request.repo_name}")
    
    try:
        # Convert test config to dict
        test_config_dict = None
        if request.test_config:
            test_config_dict = {
                "command": request.test_config.command,
                "args": request.test_config.args or [],
                "env_vars": request.test_config.env_vars or {},
                "timeout_seconds": request.test_config.timeout_seconds or 60
            }
        
        # Run the test
        report = await mcp_test_runner.test_repository(
            repo_name=request.repo_name,
            test_config=test_config_dict
        )
        
        # Convert dataclass to dict for JSON response
        report_dict = asdict(report)
        
        logger.info(f"MCP test completed for {request.repo_name}: {report.passed_tests}/{report.total_tests} passed")
        
        return MCPTestResponse(
            success=report.error_message is None,
            report=report_dict,
            error_message=report.error_message
        )
        
    except Exception as e:
        logger.error(f"MCP test failed for {request.repo_name}: {e}", exc_info=True)
        return MCPTestResponse(
            success=False,
            error_message=f"Test execution failed: {e}"
        )

@router.post("/test/batch", response_model=MCPBatchTestResponse)
async def batch_test_mcp_servers(request: MCPBatchTestRequest) -> MCPBatchTestResponse:
    """
    Test multiple MCP servers in parallel.
    
    This endpoint tests multiple repositories concurrently,
    providing aggregate results and individual reports.
    """
    logger.info(f"Starting batch MCP test for {len(request.repo_names)} repositories")
    
    reports = {}
    errors = {}
    completed = 0
    
    # Convert test config
    test_config_dict = None
    if request.test_config:
        test_config_dict = {
            "command": request.test_config.command,
            "args": request.test_config.args or [],
            "env_vars": request.test_config.env_vars or {},
            "timeout_seconds": request.test_config.timeout_seconds or 60
        }
    
    # Test each repository
    for repo_name in request.repo_names:
        try:
            logger.info(f"Testing repository {completed + 1}/{len(request.repo_names)}: {repo_name}")
            
            report = await mcp_test_runner.test_repository(
                repo_name=repo_name,
                test_config=test_config_dict
            )
            
            reports[repo_name] = asdict(report)
            completed += 1
            
            if report.error_message:
                errors[repo_name] = report.error_message
                
        except Exception as e:
            logger.error(f"Batch test failed for {repo_name}: {e}", exc_info=True)
            errors[repo_name] = f"Test execution failed: {e}"
            completed += 1
    
    logger.info(f"Batch MCP test completed: {completed}/{len(request.repo_names)} repositories tested")
    
    return MCPBatchTestResponse(
        total_repos=len(request.repo_names),
        completed_repos=completed,
        reports=reports,
        errors=errors
    )

@router.get("/test/{repo_name}/quick")
async def quick_test_mcp_server(repo_name: str) -> MCPTestResponse:
    """
    Quick test of an MCP server with default configuration.
    
    This is a simplified version that uses auto-detected settings
    and runs basic functionality tests only.
    """
    logger.info(f"Starting quick MCP test for repository: {repo_name}")
    
    try:
        # Run test with default configuration
        report = await mcp_test_runner.test_repository(repo_name=repo_name)
        
        # Convert to dict for response
        report_dict = asdict(report)
        
        return MCPTestResponse(
            success=report.error_message is None,
            report=report_dict,
            error_message=report.error_message
        )
        
    except Exception as e:
        logger.error(f"Quick MCP test failed for {repo_name}: {e}", exc_info=True)
        return MCPTestResponse(
            success=False,
            error_message=f"Quick test failed: {e}"
        )

@router.get("/status")
async def get_testing_status():
    """
    Get the current status of the MCP testing system.
    
    Returns information about:
    - Docker connectivity
    - Running test containers
    - System resources
    """
    try:
        # Check Docker connectivity
        docker_available = True
        docker_error = None
        try:
            mcp_container_service._check_docker()
        except Exception as e:
            docker_available = False
            docker_error = str(e)
        
        # Get running containers
        running_containers = len(mcp_container_service.running_containers)
        
        return {
            "system_status": "operational" if docker_available else "docker_unavailable",
            "docker_available": docker_available,
            "docker_error": docker_error,
            "running_containers": running_containers,
            "container_details": [
                {
                    "container_id": container.container_id[:12],
                    "image_name": container.image_name
                }
                for container in mcp_container_service.running_containers.values()
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get testing status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")

@router.post("/cleanup")
async def cleanup_test_containers():
    """
    Clean up all running test containers.
    
    This endpoint stops and removes all containers created
    by the MCP testing system.
    """
    try:
        logger.info("Starting cleanup of all MCP test containers")
        
        before_count = len(mcp_container_service.running_containers)
        
        await mcp_container_service.cleanup_all()
        
        after_count = len(mcp_container_service.running_containers)
        
        logger.info(f"Cleanup completed: removed {before_count - after_count} containers")
        
        return {
            "success": True,
            "containers_removed": before_count - after_count,
            "remaining_containers": after_count
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {e}")

@router.get("/health")
async def health_check():
    """Simple health check for the MCP testing API."""
    return {"status": "healthy", "service": "mcp-testing"}

@router.get("/auto-test/status")
async def get_auto_test_status():
    """Get the status of the automatic testing service."""
    testing_status = mcp_auto_test_service.get_testing_status()
    container_status = {
        "system_status": "operational",
        "running_containers": len(mcp_container_service.running_containers)
    }
    
    try:
        mcp_container_service._check_docker()
        container_status["docker_available"] = True
    except Exception as e:
        container_status["docker_available"] = False
        container_status["docker_error"] = str(e)
    
    return {
        **testing_status,
        **container_status
    }

@router.post("/auto-test/enable")
async def enable_auto_testing():
    """Enable automatic testing for newly added repositories."""
    mcp_auto_test_service.set_testing_enabled(True)
    return {
        "success": True,
        "message": "Automatic MCP testing enabled",
        "testing_enabled": mcp_auto_test_service.is_testing_enabled()
    }

@router.post("/auto-test/disable")
async def disable_auto_testing():
    """Disable automatic testing for newly added repositories."""
    mcp_auto_test_service.set_testing_enabled(False)
    return {
        "success": True,
        "message": "Automatic MCP testing disabled",
        "testing_enabled": mcp_auto_test_service.is_testing_enabled()
    }

@router.post("/retest/{repo_name}")
async def retest_repository(repo_name: str, background_tasks: BackgroundTasks):
    """Manually trigger a re-test of an existing repository."""
    try:
        logger.info(f"Manual re-test requested for repository: {repo_name}")
        
        # Check if repository exists
        from app.services.database import get_repository
        repo = get_repository(repo_name)
        if not repo:
            raise HTTPException(status_code=404, detail=f"Repository '{repo_name}' not found")
        
        # Check if already testing
        if mcp_auto_test_service.is_test_running(repo_name):
            return {
                "success": False,
                "message": f"Test already running for repository '{repo_name}'"
            }
        
        # Trigger the test
        mcp_auto_test_service.trigger_auto_test(repo_name, background_tasks)
        
        return {
            "success": True,
            "message": f"Re-test triggered for repository '{repo_name}'"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger re-test for {repo_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger re-test: {e}")

@router.get("/results/{repo_name}")
async def get_repository_test_results(repo_name: str):
    """Get the latest test results for a specific repository."""
    try:
        from app.services.database import get_repository
        repo = get_repository(repo_name)
        
        if not repo:
            raise HTTPException(status_code=404, detail=f"Repository '{repo_name}' not found")
        
        return {
            "repo_name": repo_name,
            "test_status": repo.get("test_status", "pending"),
            "test_results": repo.get("test_results", {}),
            "last_tested_at": repo.get("last_tested_at"),
            "tools_discovered": repo.get("tools_discovered", []),
            "test_success_rate": repo.get("test_success_rate"),
            "is_testing_running": mcp_auto_test_service.is_test_running(repo_name)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get test results for {repo_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get test results: {e}")

@router.get("/results")
async def get_all_test_results():
    """Get test results summary for all repositories."""
    try:
        from app.services.database import get_repositories
        repos = get_repositories()
        
        results = []
        for repo in repos:
            results.append({
                "repo_name": repo.get("name"),
                "test_status": repo.get("test_status", "pending"),
                "last_tested_at": repo.get("last_tested_at"),
                "test_success_rate": repo.get("test_success_rate"),
                "tools_count": len(repo.get("tools_discovered", [])),
                "is_external_config": repo.get("is_external_config", False),
                "is_testing_running": mcp_auto_test_service.is_test_running(repo.get("name", ""))
            })
        
        # Calculate summary statistics
        total_repos = len(results)
        tested_repos = len([r for r in results if r["test_status"] in ["completed", "failed"]])
        successful_repos = len([r for r in results if r["test_status"] == "completed"])
        running_tests = len([r for r in results if r["is_testing_running"]])
        
        return {
            "summary": {
                "total_repositories": total_repos,
                "tested_repositories": tested_repos,
                "successful_tests": successful_repos,
                "running_tests": running_tests,
                "auto_testing_enabled": mcp_auto_test_service.is_testing_enabled()
            },
            "repositories": results
        }
        
    except Exception as e:
        logger.error(f"Failed to get test results summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get test results: {e}")

@router.get("/quality/{repo_name}")
async def get_repository_quality_report(repo_name: str):
    """Get detailed quality assessment report for a specific repository."""
    try:
        from app.services.database import get_repository
        repo = get_repository(repo_name)
        
        if not repo:
            raise HTTPException(status_code=404, detail=f"Repository '{repo_name}' not found")
        
        # Extract quality information
        test_results = repo.get("test_results", {})
        quality_breakdown = repo.get("quality_breakdown", {})
        tool_quality_assessments = repo.get("tool_quality_assessments", {})
        average_quality_score = repo.get("average_quality_score")
        
        # Analyze test results for detailed quality insights
        detailed_test_results = test_results.get("test_results", [])
        quality_insights = {
            "by_test_type": {},
            "by_difficulty": {},
            "common_strengths": [],
            "common_weaknesses": [],
            "improvement_suggestions": []
        }
        
        if detailed_test_results:
            # Group by test type
            for result in detailed_test_results:
                test_type = result.get("test_type", "unknown")
                if test_type not in quality_insights["by_test_type"]:
                    quality_insights["by_test_type"][test_type] = {
                        "count": 0,
                        "avg_quality": 0,
                        "scores": []
                    }
                
                quality_score = result.get("quality_score")
                if quality_score is not None:
                    quality_insights["by_test_type"][test_type]["count"] += 1
                    quality_insights["by_test_type"][test_type]["scores"].append(quality_score)
            
            # Calculate averages
            for test_type_data in quality_insights["by_test_type"].values():
                if test_type_data["scores"]:
                    test_type_data["avg_quality"] = sum(test_type_data["scores"]) / len(test_type_data["scores"])
                    del test_type_data["scores"]  # Remove raw scores from response
            
            # Collect common themes from quality assessments
            all_strengths = []
            all_weaknesses = []
            all_suggestions = []
            
            for result in detailed_test_results:
                assessment = result.get("quality_assessment", {})
                if assessment:
                    all_strengths.extend(assessment.get("strengths", []))
                    all_weaknesses.extend(assessment.get("weaknesses", []))
                    all_suggestions.extend(assessment.get("suggestions", []))
            
            # Get most common items (simple approach)
            quality_insights["common_strengths"] = list(set(all_strengths))[:5]
            quality_insights["common_weaknesses"] = list(set(all_weaknesses))[:5]
            quality_insights["improvement_suggestions"] = list(set(all_suggestions))[:5]
        
        return {
            "repo_name": repo_name,
            "overall_quality_score": average_quality_score,
            "quality_breakdown": quality_breakdown,
            "tool_quality_assessments": tool_quality_assessments,
            "quality_insights": quality_insights,
            "test_summary": {
                "total_tests": test_results.get("total_tests", 0),
                "passed_tests": test_results.get("passed_tests", 0),
                "failed_tests": test_results.get("failed_tests", 0),
                "execution_time_ms": test_results.get("execution_time_ms", 0)
            },
            "last_tested_at": repo.get("last_tested_at"),
            "test_status": repo.get("test_status", "pending")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quality report for {repo_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get quality report: {e}")

@router.get("/quality/leaderboard")
async def get_quality_leaderboard(limit: int = 20):
    """Get a leaderboard of repositories ranked by quality scores."""
    try:
        from app.services.database import get_repositories
        repos = get_repositories()
        
        # Filter repositories with quality scores and sort by quality
        quality_repos = []
        for repo in repos:
            quality_score = repo.get("average_quality_score")
            if quality_score is not None:
                quality_repos.append({
                    "repo_name": repo.get("name"),
                    "quality_score": quality_score,
                    "test_success_rate": repo.get("test_success_rate", 0),
                    "tools_count": len(repo.get("tools_discovered", [])),
                    "last_tested_at": repo.get("last_tested_at"),
                    "quality_breakdown": repo.get("quality_breakdown", {}),
                    "is_external_config": repo.get("is_external_config", False)
                })
        
        # Sort by quality score (descending)
        quality_repos.sort(key=lambda x: x["quality_score"], reverse=True)
        
        # Calculate statistics
        if quality_repos:
            avg_quality = sum(r["quality_score"] for r in quality_repos) / len(quality_repos)
            max_quality = max(r["quality_score"] for r in quality_repos)
            min_quality = min(r["quality_score"] for r in quality_repos)
        else:
            avg_quality = max_quality = min_quality = 0
        
        return {
            "leaderboard": quality_repos[:limit],
            "statistics": {
                "total_repositories_with_quality": len(quality_repos),
                "average_quality_score": avg_quality,
                "highest_quality_score": max_quality,
                "lowest_quality_score": min_quality,
                "quality_distribution": {
                    "excellent": len([r for r in quality_repos if r["quality_score"] >= 8.0]),
                    "good": len([r for r in quality_repos if 6.0 <= r["quality_score"] < 8.0]),
                    "fair": len([r for r in quality_repos if 4.0 <= r["quality_score"] < 6.0]),
                    "poor": len([r for r in quality_repos if r["quality_score"] < 4.0])
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get quality leaderboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get quality leaderboard: {e}")

@router.get("/quality/analytics")
async def get_quality_analytics():
    """Get overall quality analytics across all repositories."""
    try:
        from app.services.database import get_repositories
        repos = get_repositories()
        
        # Collect all quality data
        all_quality_scores = []
        quality_by_dimension = {
            "relevance": [],
            "accuracy": [],
            "completeness": [],
            "usability": [],
            "format": []
        }
        tool_quality_data = {}
        
        for repo in repos:
            # Overall quality scores
            quality_score = repo.get("average_quality_score")
            if quality_score is not None:
                all_quality_scores.append(quality_score)
            
            # Quality breakdown by dimension
            breakdown = repo.get("quality_breakdown", {})
            for dimension, score in breakdown.items():
                if dimension in quality_by_dimension and score is not None:
                    quality_by_dimension[dimension].append(score)
            
            # Tool-specific quality data
            tool_assessments = repo.get("tool_quality_assessments", {})
            for tool_name, tool_data in tool_assessments.items():
                tool_quality = tool_data.get("average_quality")
                if tool_quality is not None:
                    if tool_name not in tool_quality_data:
                        tool_quality_data[tool_name] = []
                    tool_quality_data[tool_name].append(tool_quality)
        
        # Calculate analytics
        def calculate_stats(scores):
            if not scores:
                return {"average": 0, "min": 0, "max": 0, "count": 0}
            return {
                "average": sum(scores) / len(scores),
                "min": min(scores),
                "max": max(scores),
                "count": len(scores)
            }
        
        # Overall quality analytics
        overall_analytics = calculate_stats(all_quality_scores)
        
        # Dimension analytics
        dimension_analytics = {}
        for dimension, scores in quality_by_dimension.items():
            dimension_analytics[dimension] = calculate_stats(scores)
        
        # Top performing tools
        tool_rankings = []
        for tool_name, scores in tool_quality_data.items():
            if scores:
                tool_rankings.append({
                    "tool_name": tool_name,
                    "average_quality": sum(scores) / len(scores),
                    "repository_count": len(scores),
                    "min_quality": min(scores),
                    "max_quality": max(scores)
                })
        
        tool_rankings.sort(key=lambda x: x["average_quality"], reverse=True)
        
        return {
            "overall_quality": overall_analytics,
            "quality_by_dimension": dimension_analytics,
            "top_performing_tools": tool_rankings[:15],
            "quality_trends": {
                "repositories_with_quality_data": len(all_quality_scores),
                "total_repositories": len(repos),
                "coverage_percentage": (len(all_quality_scores) / len(repos) * 100) if repos else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get quality analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get quality analytics: {e}") 