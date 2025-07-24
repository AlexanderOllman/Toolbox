import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from .mcp_container_service import MCPContainerService, MCPContainerConfig, mcp_container_service
from .mcp_client import MCPTestSession, MCPTool, MCPResponse
from .repository_validation_service import RepositoryValidationService
from .database import get_repository
from .mcp_test_data_generator import mcp_test_data_generator, TestCase
from .mcp_quality_assessor import mcp_quality_assessor, QualityAssessment

logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Individual test case result."""
    tool_name: str
    test_type: str
    success: bool
    execution_time_ms: int
    arguments: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    raw_response: Optional[str] = None
    # Enhanced fields for LLM-powered testing
    test_description: Optional[str] = None
    expected_behavior: Optional[str] = None
    difficulty: Optional[str] = None
    quality_assessment: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None

@dataclass
class MCPServerTestReport:
    """Complete test report for an MCP server."""
    repo_name: str
    image_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    execution_time_ms: int
    tools_discovered: List[Dict[str, Any]]
    test_results: List[TestResult]
    container_logs: Optional[str] = None
    error_message: Optional[str] = None
    # Enhanced quality metrics
    average_quality_score: Optional[float] = None
    quality_breakdown: Optional[Dict[str, float]] = None
    tool_quality_assessments: Optional[Dict[str, Dict[str, Any]]] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

class MCPTestRunner:
    """
    High-level orchestrator for testing MCP servers in isolated containers.
    """
    
    def __init__(self, container_service: MCPContainerService = None):
        self.container_service = container_service or mcp_container_service
        self.validation_service = RepositoryValidationService()
    
    async def test_repository(self, repo_name: str, test_config: Optional[Dict[str, Any]] = None) -> MCPServerTestReport:
        """
        Test an MCP server repository end-to-end.
        
        Args:
            repo_name: Name of the repository to test
            test_config: Optional test configuration
            
        Returns:
            Complete test report
        """
        start_time = time.time()
        
        logger.info(f"Starting MCP server test for repository: {repo_name}")
        
        try:
            # Validate repository
            is_valid, error_msg, repo_info = self.validation_service.validate_repository_for_deployment(repo_name)
            if not is_valid:
                return MCPServerTestReport(
                    repo_name=repo_name,
                    image_name="",
                    total_tests=0,
                    passed_tests=0,
                    failed_tests=0,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    tools_discovered=[],
                    test_results=[],
                    error_message=f"Repository validation failed: {error_msg}"
                )
            
            # Get repository configuration
            repo_data = get_repository(repo_name)
            if not repo_data:
                # Try to work with local files only
                logger.warning(f"Repository {repo_name} not in database, using local analysis")
            
            # Create container configuration
            container_config = await self._create_container_config(repo_info, repo_data, test_config)
            
            # Run tests in container
            return await self._run_tests_in_container(repo_name, container_config, start_time)
            
        except Exception as e:
            logger.error(f"Test execution failed for {repo_name}: {e}")
            return MCPServerTestReport(
                repo_name=repo_name,
                image_name="",
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                execution_time_ms=int((time.time() - start_time) * 1000),
                tools_discovered=[],
                test_results=[],
                error_message=f"Test execution failed: {e}"
            )
    
    async def _create_container_config(self, repo_info: Dict[str, Any], repo_data: Optional[Dict[str, Any]], test_config: Optional[Dict[str, Any]]) -> MCPContainerConfig:
        """Create container configuration from repository information."""
        
        local_path = repo_info['local_path']
        
        # Determine command and args
        command = None
        args = []
        env_vars = {}
        
        if repo_data:
            command = repo_data.get('command')
            args = repo_data.get('args', [])
            
            # Convert env vars from database format
            env_data = repo_data.get('env', {})
            for key, value in env_data.items():
                if isinstance(value, dict) and 'value' in value:
                    env_vars[key] = value['value']
                elif isinstance(value, str):
                    env_vars[key] = value
        
        # Auto-detect command if not specified
        if not command:
            command = self._auto_detect_command(Path(local_path))
        
        # Apply test configuration overrides
        if test_config:
            command = test_config.get('command', command)
            args = test_config.get('args', args)
            env_vars.update(test_config.get('env_vars', {}))
        
        return MCPContainerConfig(
            repo_path=local_path,
            command=command,
            args=args,
            env_vars=env_vars,
            timeout_seconds=test_config.get('timeout_seconds', 60) if test_config else 60
        )
    
    def _auto_detect_command(self, repo_path: Path) -> Optional[str]:
        """Auto-detect the command to run the MCP server."""
        
        # Check for common entry points
        if (repo_path / "server.py").exists():
            return "python"
        elif (repo_path / "index.js").exists():
            return "node"
        elif (repo_path / "index.ts").exists():
            return "npx"
        elif (repo_path / "src" / "index.ts").exists():
            return "npm"
        elif (repo_path / "package.json").exists():
            # Try to read npm scripts
            try:
                import json
                with open(repo_path / "package.json") as f:
                    package_data = json.load(f)
                    scripts = package_data.get("scripts", {})
                    if "start" in scripts:
                        return "npm"
            except:
                pass
            return "node"
        elif (repo_path / "pyproject.toml").exists():
            return "python"
        elif (repo_path / "requirements.txt").exists():
            return "python"
        
        # Default fallback
        return "python"
    
    async def _run_tests_in_container(self, repo_name: str, config: MCPContainerConfig, start_time: float) -> MCPServerTestReport:
        """Run tests inside a container and return results."""
        
        container = None
        session = None
        
        try:
            # Start container
            logger.info(f"Starting container for {repo_name}")
            container = await self.container_service.run_mcp_server(config)
            
            # Create test session
            session = MCPTestSession(container)
            
            # Connect and discover tools
            logger.info(f"Connecting to MCP server in container")
            connected = await session.start()
            
            if not connected:
                container_logs = await self.container_service._get_container_logs(container.container_id)
                return MCPServerTestReport(
                    repo_name=repo_name,
                    image_name=container.image_name,
                    total_tests=0,
                    passed_tests=0,
                    failed_tests=0,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    tools_discovered=[],
                    test_results=[],
                    container_logs=container_logs,
                    error_message="Failed to connect to MCP server"
                )
            
            # Run tests
            logger.info(f"Running tests for {len(session.tools)} tools")
            test_results = await self._execute_test_suite(session)
            
            # Get container logs for debugging
            container_logs = await self.container_service._get_container_logs(container.container_id)
            
            # Calculate statistics
            passed_tests = sum(1 for result in test_results if result.success)
            failed_tests = len(test_results) - passed_tests
            
            # Calculate quality metrics
            quality_scores = [r.quality_score for r in test_results if r.quality_score is not None]
            average_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else None
            
            # Calculate quality breakdown by dimension
            quality_breakdown = None
            if test_results and any(r.quality_assessment for r in test_results):
                total_assessments = [r.quality_assessment for r in test_results if r.quality_assessment]
                if total_assessments:
                    quality_breakdown = {
                        "relevance": sum(a.get("relevance_score", 0) for a in total_assessments) / len(total_assessments),
                        "accuracy": sum(a.get("accuracy_score", 0) for a in total_assessments) / len(total_assessments),
                        "completeness": sum(a.get("completeness_score", 0) for a in total_assessments) / len(total_assessments),
                        "usability": sum(a.get("usability_score", 0) for a in total_assessments) / len(total_assessments),
                        "format": sum(a.get("format_score", 0) for a in total_assessments) / len(total_assessments)
                    }
            
            # Generate per-tool quality assessments
            tool_quality_assessments = {}
            for tool in session.tools:
                tool_results = [r for r in test_results if r.tool_name == tool.name]
                if tool_results:
                    tool_scores = [r.quality_score for r in tool_results if r.quality_score is not None]
                    tool_quality_assessments[tool.name] = {
                        "average_quality": sum(tool_scores) / len(tool_scores) if tool_scores else None,
                        "test_count": len(tool_results),
                        "success_count": sum(1 for r in tool_results if r.success),
                        "quality_assessments": [r.quality_assessment for r in tool_results if r.quality_assessment]
                    }
            
            return MCPServerTestReport(
                repo_name=repo_name,
                image_name=container.image_name,
                total_tests=len(test_results),
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                execution_time_ms=int((time.time() - start_time) * 1000),
                tools_discovered=[asdict(tool) for tool in session.tools],
                test_results=test_results,
                container_logs=container_logs,
                average_quality_score=average_quality_score,
                quality_breakdown=quality_breakdown,
                tool_quality_assessments=tool_quality_assessments
            )
            
        except Exception as e:
            logger.error(f"Container test execution failed: {e}")
            
            container_logs = None
            if container:
                try:
                    container_logs = await self.container_service._get_container_logs(container.container_id)
                except:
                    pass
            
            return MCPServerTestReport(
                repo_name=repo_name,
                image_name=container.image_name if container else "",
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                execution_time_ms=int((time.time() - start_time) * 1000),
                tools_discovered=[],
                test_results=[],
                container_logs=container_logs,
                error_message=f"Container execution failed: {e}"
            )
            
        finally:
            # Clean up
            if session:
                await session.stop()
            if container:
                await self.container_service.cleanup_container(container)
    
    async def _execute_test_suite(self, session: MCPTestSession) -> List[TestResult]:
        """Execute comprehensive test suite on the MCP server using LLM-powered test generation."""
        
        test_results = []
        
        for tool in session.tools:
            logger.info(f"Testing tool: {tool.name}")
            
            try:
                # Generate comprehensive test cases using LLM
                test_cases = await mcp_test_data_generator.generate_test_cases(
                    tool_name=tool.name,
                    tool_description=tool.description,
                    input_schema=tool.input_schema,
                    max_cases=8  # Generate up to 8 test cases per tool
                )
                
                if not test_cases:
                    # Fallback to basic test if LLM generation fails
                    logger.warning(f"No LLM test cases generated for {tool.name}, using basic test")
                    basic_result = await self._test_tool_basic(session, tool)
                    test_results.append(basic_result)
                    continue
                
                # Execute each generated test case
                for test_case in test_cases:
                    result = await self._execute_test_case(session, tool, test_case)
                    test_results.append(result)
                    
                    # Small delay between tests to avoid overwhelming the server
                    await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Failed to test tool {tool.name}: {e}")
                # Create error test result
                error_result = TestResult(
                    tool_name=tool.name,
                    test_type="error",
                    success=False,
                    execution_time_ms=0,
                    arguments={},
                    error_message=f"Test execution failed: {e}",
                    test_description="Test setup failed",
                    expected_behavior="Should execute without errors",
                    difficulty="unknown"
                )
                test_results.append(error_result)
        
        return test_results
    
    async def _execute_test_case(self, session: MCPTestSession, tool: MCPTool, test_case: TestCase) -> TestResult:
        """Execute a single test case with quality assessment."""
        
        start_time = time.time()
        
        try:
            # Execute the tool call
            response = await session.test_tool(tool.name, test_case.arguments)
            execution_time = int((time.time() - start_time) * 1000)
            
            # Assess response quality using LLM
            quality_assessment = None
            quality_score = None
            
            try:
                quality_assessment = await mcp_quality_assessor.assess_response_quality(
                    tool_name=tool.name,
                    tool_description=tool.description,
                    test_arguments=test_case.arguments,
                    response_data=response.result if response.success else response.error,
                    expected_behavior=test_case.expected_behavior,
                    test_description=test_case.description
                )
                quality_score = quality_assessment.overall_score
                
                # Convert quality assessment to dict for storage
                quality_dict = asdict(quality_assessment)
                
            except Exception as e:
                logger.warning(f"Quality assessment failed for {tool.name}: {e}")
                quality_dict = None
                quality_score = None
            
            return TestResult(
                tool_name=tool.name,
                test_type=test_case.test_type,
                success=response.success,
                execution_time_ms=execution_time,
                arguments=test_case.arguments,
                response=response.result if response.success else None,
                error_message=str(response.error) if response.error else None,
                raw_response=response.raw_response,
                test_description=test_case.description,
                expected_behavior=test_case.expected_behavior,
                difficulty=test_case.difficulty,
                quality_assessment=quality_dict,
                quality_score=quality_score
            )
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return TestResult(
                tool_name=tool.name,
                test_type=test_case.test_type,
                success=False,
                execution_time_ms=execution_time,
                arguments=test_case.arguments,
                error_message=f"Test execution failed: {e}",
                test_description=test_case.description,
                expected_behavior=test_case.expected_behavior,
                difficulty=test_case.difficulty
            )
    
    async def _test_tool_basic(self, session: MCPTestSession, tool: MCPTool) -> TestResult:
        """Test tool with basic, valid arguments."""
        
        start_time = time.time()
        
        try:
            # Generate basic test arguments
            test_args = session._generate_test_arguments(tool.input_schema)
            
            # Execute tool
            response = await session.test_tool(tool.name, test_args)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return TestResult(
                tool_name=tool.name,
                test_type="basic_functionality",
                success=response.success,
                execution_time_ms=execution_time,
                arguments=test_args,
                response=response.result if response.success else None,
                error_message=str(response.error) if response.error else None,
                raw_response=response.raw_response
            )
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return TestResult(
                tool_name=tool.name,
                test_type="basic_functionality",
                success=False,
                execution_time_ms=execution_time,
                arguments={},
                error_message=f"Test execution failed: {e}"
            )
    
    async def _test_tool_invalid_params(self, session: MCPTestSession, tool: MCPTool) -> Optional[TestResult]:
        """Test tool with invalid parameters to check error handling."""
        
        # Generate invalid arguments based on schema
        invalid_args = self._generate_invalid_arguments(tool.input_schema)
        if not invalid_args:
            return None  # Can't generate meaningful invalid args
        
        start_time = time.time()
        
        try:
            response = await session.test_tool(tool.name, invalid_args)
            execution_time = int((time.time() - start_time) * 1000)
            
            # For invalid params, we expect the tool to fail gracefully
            success = not response.success and response.error is not None
            
            return TestResult(
                tool_name=tool.name,
                test_type="invalid_parameters",
                success=success,
                execution_time_ms=execution_time,
                arguments=invalid_args,
                response=response.result if response.success else None,
                error_message=str(response.error) if response.error else "Tool should have failed with invalid params",
                raw_response=response.raw_response
            )
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return TestResult(
                tool_name=tool.name,
                test_type="invalid_parameters",
                success=False,
                execution_time_ms=execution_time,
                arguments=invalid_args,
                error_message=f"Test execution failed: {e}"
            )
    
    async def _test_tool_edge_cases(self, session: MCPTestSession, tool: MCPTool) -> Optional[TestResult]:
        """Test tool with edge case arguments."""
        
        edge_args = self._generate_edge_case_arguments(tool.input_schema)
        if not edge_args:
            return None
        
        start_time = time.time()
        
        try:
            response = await session.test_tool(tool.name, edge_args)
            execution_time = int((time.time() - start_time) * 1000)
            
            return TestResult(
                tool_name=tool.name,
                test_type="edge_cases",
                success=response.success,
                execution_time_ms=execution_time,
                arguments=edge_args,
                response=response.result if response.success else None,
                error_message=str(response.error) if response.error else None,
                raw_response=response.raw_response
            )
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return TestResult(
                tool_name=tool.name,
                test_type="edge_cases",
                success=False,
                execution_time_ms=execution_time,
                arguments=edge_args,
                error_message=f"Test execution failed: {e}"
            )
    
    def _generate_invalid_arguments(self, input_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate invalid arguments to test error handling."""
        
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        
        if not required:
            return {}  # Can't generate meaningful invalid args
        
        # Start with valid args, then make one invalid
        args = {}
        
        for prop_name, prop_schema in properties.items():
            if prop_name in required:
                prop_type = prop_schema.get("type", "string")
                
                # Generate wrong type
                if prop_type == "string":
                    args[prop_name] = 123  # Number instead of string
                    break
                elif prop_type == "number":
                    args[prop_name] = "not_a_number"  # String instead of number
                    break
                elif prop_type == "boolean":
                    args[prop_name] = "not_a_boolean"  # String instead of boolean
                    break
        
        return args
    
    def _generate_edge_case_arguments(self, input_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate edge case arguments."""
        
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        
        args = {}
        
        for prop_name, prop_schema in properties.items():
            if prop_name in required:
                prop_type = prop_schema.get("type", "string")
                
                if prop_type == "string":
                    # Test with empty string, very long string
                    args[prop_name] = ""
                elif prop_type == "number":
                    # Test with zero, negative numbers
                    args[prop_name] = 0
                elif prop_type == "array":
                    # Test with empty array
                    args[prop_name] = []
                elif prop_type == "object":
                    # Test with empty object
                    args[prop_name] = {}
        
        return args if args else {}

# Global instance
mcp_test_runner = MCPTestRunner() 