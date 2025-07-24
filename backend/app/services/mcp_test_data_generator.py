import json
import logging
from typing import Dict, List, Any, Optional, Tuple
import asyncio
from dataclasses import dataclass

from .openai_service import client as openai_client

logger = logging.getLogger(__name__)

@dataclass
class TestCase:
    """Represents a generated test case for an MCP tool."""
    test_type: str  # "realistic", "edge_case", "stress_test", "invalid"
    arguments: Dict[str, Any]
    expected_behavior: str  # Description of what should happen
    description: str  # Human-readable description of the test case
    difficulty: str  # "easy", "medium", "hard"

class MCPTestDataGenerator:
    """
    Advanced test data generator using LLMs to create realistic and comprehensive
    test cases for MCP tools based on their schemas and descriptions.
    """
    
    def __init__(self):
        self.openai_client = openai_client
        if not self.openai_client:
            logger.warning("OpenAI client not available. Test data generation will use fallback methods.")
    
    async def generate_test_cases(self, tool_name: str, tool_description: str, 
                                input_schema: Dict[str, Any], 
                                max_cases: int = 10) -> List[TestCase]:
        """
        Generate comprehensive test cases for an MCP tool using LLM analysis.
        
        Args:
            tool_name: Name of the tool
            tool_description: Description of what the tool does
            input_schema: JSON schema for the tool's input parameters
            max_cases: Maximum number of test cases to generate
            
        Returns:
            List of generated test cases
        """
        logger.info(f"Generating test cases for tool: {tool_name}")
        
        # Check if OpenAI client is available
        if not self.openai_client:
            logger.warning(f"OpenAI client not available, falling back to basic test case generation for {tool_name}")
            return self._generate_basic_fallback_cases(tool_name, input_schema)
        
        try:
            # Generate different types of test cases
            test_cases = []
            
            # Generate realistic test cases (most important)
            realistic_cases = await self._generate_realistic_cases(
                tool_name, tool_description, input_schema, count=max(3, max_cases // 2)
            )
            test_cases.extend(realistic_cases)
            
            # Generate edge cases
            edge_cases = await self._generate_edge_cases(
                tool_name, tool_description, input_schema, count=min(3, max_cases // 4)
            )
            test_cases.extend(edge_cases)
            
            # Generate invalid cases for error handling testing
            invalid_cases = await self._generate_invalid_cases(
                tool_name, tool_description, input_schema, count=min(2, max_cases // 4)
            )
            test_cases.extend(invalid_cases)
            
            # Generate stress test cases if applicable
            if max_cases > 8:
                stress_cases = await self._generate_stress_cases(
                    tool_name, tool_description, input_schema, count=1
                )
                test_cases.extend(stress_cases)
            
            logger.info(f"Generated {len(test_cases)} test cases for {tool_name}")
            return test_cases[:max_cases]
            
        except Exception as e:
            logger.error(f"Failed to generate test cases for {tool_name}: {e}")
            # Fallback to basic test case generation
            return self._generate_basic_fallback_cases(tool_name, input_schema)
    
    async def _generate_realistic_cases(self, tool_name: str, tool_description: str, 
                                      input_schema: Dict[str, Any], count: int) -> List[TestCase]:
        """Generate realistic, practical test cases that users would actually run."""
        
        prompt = f"""
Generate {count} realistic test cases for an MCP tool.

Tool Name: {tool_name}
Description: {tool_description}
Input Schema: {json.dumps(input_schema, indent=2)}

Create test cases that represent real-world usage scenarios. For each test case, provide:
1. Realistic parameter values that a user would actually provide
2. A description of the test scenario
3. Expected behavior description
4. Difficulty level (easy/medium/hard)

Consider the tool's purpose and generate diverse, practical examples.
Focus on common use cases, typical parameter combinations, and realistic data.

Return ONLY a JSON array of test cases with this structure:
[
  {{
    "arguments": {{"param1": "value1", "param2": "value2"}},
    "description": "Test searching for recent papers on AI",
    "expected_behavior": "Should return a list of relevant papers with titles and abstracts",
    "difficulty": "easy"
  }}
]
"""
        
        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            logger.debug(f"Raw LLM response for realistic cases: {content}")
            
            # Parse JSON response
            test_data = json.loads(content)
            logger.debug(f"Parsed test data: {test_data}")
            
            # Handle different response formats - LLM might return object with test_cases key
            if isinstance(test_data, dict):
                if "test_cases" in test_data:
                    test_data = test_data["test_cases"]
                elif len(test_data) == 1:
                    # If it's a dict with a single key, try using that value
                    test_data = list(test_data.values())[0]
                else:
                    logger.warning(f"Unexpected dict format: {test_data}")
                    return []
            
            if not isinstance(test_data, list):
                logger.warning(f"Expected list but got {type(test_data)}: {test_data}")
                return []
            
            test_cases = []
            for case_data in test_data:
                test_cases.append(TestCase(
                    test_type="realistic",
                    arguments=case_data.get("arguments", {}),
                    expected_behavior=case_data.get("expected_behavior", ""),
                    description=case_data.get("description", ""),
                    difficulty=case_data.get("difficulty", "medium")
                ))
            
            return test_cases
            
        except Exception as e:
            logger.error(f"Failed to generate realistic test cases: {e}")
            return []
    
    async def _generate_edge_cases(self, tool_name: str, tool_description: str, 
                                 input_schema: Dict[str, Any], count: int) -> List[TestCase]:
        """Generate edge cases to test boundary conditions and limits."""
        
        prompt = f"""
Generate {count} edge case test scenarios for an MCP tool.

Tool Name: {tool_name}
Description: {tool_description}
Input Schema: {json.dumps(input_schema, indent=2)}

Create edge cases that test boundary conditions, limits, and unusual but valid inputs:
- Empty strings where strings are expected
- Minimum/maximum values for numbers
- Very long strings
- Empty arrays
- Special characters and unicode
- Boundary date/time values
- Zero values where applicable

Each test case should still be VALID according to the schema, but test edge conditions.

Return ONLY a JSON array with this structure:
[
  {{
    "arguments": {{"param1": "", "param2": 0}},
    "description": "Test with empty search query",
    "expected_behavior": "Should handle empty query gracefully, possibly return error or empty results",
    "difficulty": "medium"
  }}
]
"""
        
        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            test_data = json.loads(content)
            
            # Handle different response formats
            if isinstance(test_data, dict):
                if "test_cases" in test_data:
                    test_data = test_data["test_cases"]
                elif len(test_data) == 1:
                    test_data = list(test_data.values())[0]
                else:
                    logger.warning(f"Unexpected dict format for edge cases: {test_data}")
                    return []
            
            if not isinstance(test_data, list):
                logger.warning(f"Expected list but got {type(test_data)} for edge cases")
                return []
            
            test_cases = []
            for case_data in test_data:
                test_cases.append(TestCase(
                    test_type="edge_case",
                    arguments=case_data.get("arguments", {}),
                    expected_behavior=case_data.get("expected_behavior", ""),
                    description=case_data.get("description", ""),
                    difficulty=case_data.get("difficulty", "medium")
                ))
            
            return test_cases
            
        except Exception as e:
            logger.error(f"Failed to generate edge cases: {e}")
            return []
    
    async def _generate_invalid_cases(self, tool_name: str, tool_description: str, 
                                    input_schema: Dict[str, Any], count: int) -> List[TestCase]:
        """Generate invalid test cases to test error handling."""
        
        prompt = f"""
Generate {count} invalid test cases for an MCP tool to test error handling.

Tool Name: {tool_name}
Description: {tool_description}
Input Schema: {json.dumps(input_schema, indent=2)}

Create test cases with INVALID inputs that should cause the tool to fail gracefully:
- Wrong data types (string where number expected, etc.)
- Missing required parameters
- Invalid enum values
- Out-of-range numbers
- Malformed data formats

These should test that the tool properly validates input and returns meaningful error messages.

Return ONLY a JSON array with this structure:
[
  {{
    "arguments": {{"param1": 999999, "param2": "invalid_enum_value"}},
    "description": "Test with invalid parameter values",
    "expected_behavior": "Should return validation error with clear message",
    "difficulty": "easy"
  }}
]
"""
        
        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            test_data = json.loads(content)
            
            # Handle different response formats
            if isinstance(test_data, dict):
                if "test_cases" in test_data:
                    test_data = test_data["test_cases"]
                elif len(test_data) == 1:
                    test_data = list(test_data.values())[0]
                else:
                    logger.warning(f"Unexpected dict format for invalid cases: {test_data}")
                    return []
            
            if not isinstance(test_data, list):
                logger.warning(f"Expected list but got {type(test_data)} for invalid cases")
                return []
            
            test_cases = []
            for case_data in test_data:
                test_cases.append(TestCase(
                    test_type="invalid",
                    arguments=case_data.get("arguments", {}),
                    expected_behavior=case_data.get("expected_behavior", ""),
                    description=case_data.get("description", ""),
                    difficulty=case_data.get("difficulty", "easy")
                ))
            
            return test_cases
            
        except Exception as e:
            logger.error(f"Failed to generate invalid cases: {e}")
            return []
    
    async def _generate_stress_cases(self, tool_name: str, tool_description: str, 
                                   input_schema: Dict[str, Any], count: int) -> List[TestCase]:
        """Generate stress test cases with large/complex inputs."""
        
        prompt = f"""
Generate {count} stress test case for an MCP tool.

Tool Name: {tool_name}
Description: {tool_description}
Input Schema: {json.dumps(input_schema, indent=2)}

Create a stress test with large, complex, or resource-intensive inputs:
- Very long strings (1000+ characters)
- Large arrays
- Complex nested objects
- Multiple parameters with maximum values
- High-volume data requests

The input should still be valid but designed to test performance and resource handling.

Return ONLY a JSON array with this structure:
[
  {{
    "arguments": {{"query": "very long query string...", "limit": 100}},
    "description": "Stress test with large query and high limit",
    "expected_behavior": "Should handle large request efficiently or return appropriate limits",
    "difficulty": "hard"
  }}
]
"""
        
        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            test_data = json.loads(content)
            
            # Handle different response formats
            if isinstance(test_data, dict):
                if "test_cases" in test_data:
                    test_data = test_data["test_cases"]
                elif len(test_data) == 1:
                    test_data = list(test_data.values())[0]
                else:
                    logger.warning(f"Unexpected dict format for stress cases: {test_data}")
                    return []
            
            if not isinstance(test_data, list):
                logger.warning(f"Expected list but got {type(test_data)} for stress cases")
                return []
            
            test_cases = []
            for case_data in test_data:
                test_cases.append(TestCase(
                    test_type="stress_test",
                    arguments=case_data.get("arguments", {}),
                    expected_behavior=case_data.get("expected_behavior", ""),
                    description=case_data.get("description", ""),
                    difficulty=case_data.get("difficulty", "hard")
                ))
            
            return test_cases
            
        except Exception as e:
            logger.error(f"Failed to generate stress cases: {e}")
            return []
    
    def _generate_basic_fallback_cases(self, tool_name: str, input_schema: Dict[str, Any]) -> List[TestCase]:
        """Generate basic test cases when LLM generation fails."""
        
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        
        if not required:
            return []
        
        # Generate one basic test case with minimal valid arguments
        basic_args = {}
        for prop_name in required:
            prop_schema = properties.get(prop_name, {})
            prop_type = prop_schema.get("type", "string")
            
            if prop_type == "string":
                basic_args[prop_name] = "test"
            elif prop_type in ["number", "integer"]:
                basic_args[prop_name] = 1
            elif prop_type == "boolean":
                basic_args[prop_name] = True
            elif prop_type == "array":
                basic_args[prop_name] = []
            elif prop_type == "object":
                basic_args[prop_name] = {}
        
        return [TestCase(
            test_type="realistic",
            arguments=basic_args,
            expected_behavior="Should execute successfully with basic valid input",
            description=f"Basic functionality test for {tool_name}",
            difficulty="easy"
        )]

# Global instance
mcp_test_data_generator = MCPTestDataGenerator() 