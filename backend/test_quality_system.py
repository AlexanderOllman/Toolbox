#!/usr/bin/env python3
"""
Demo script to test the LLM-powered MCP quality assessment system.

This script:
1. Tests the test data generator with sample tool schemas
2. Tests the quality assessor with sample responses
3. Demonstrates the enhanced testing workflow
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.mcp_test_data_generator import mcp_test_data_generator
from app.services.mcp_quality_assessor import mcp_quality_assessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_data_generator():
    """Test the LLM-powered test data generator."""
    print("\n" + "="*60)
    print("TESTING LLM-POWERED TEST DATA GENERATOR")
    print("="*60)
    
    # Sample tool schemas for testing
    sample_tools = [
        {
            "name": "search_arxiv",
            "description": "Search for academic papers on arXiv by query terms, categories, and date ranges",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for papers"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 10
                    },
                    "category": {
                        "type": "string",
                        "description": "arXiv category to search in",
                        "enum": ["cs.AI", "cs.LG", "cs.CL", "physics", "math"]
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "file_manager",
            "description": "Manage files and directories: create, read, update, delete operations",
            "input_schema": {
                "type": "object", 
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "read", "update", "delete", "list"],
                        "description": "File operation to perform"
                    },
                    "path": {
                        "type": "string",
                        "description": "File or directory path"
                    },
                    "content": {
                        "type": "string",
                        "description": "File content (for create/update operations)"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to operate recursively on directories",
                        "default": False
                    }
                },
                "required": ["action", "path"]
            }
        }
    ]
    
    for tool in sample_tools:
        print(f"\n--- Generating Test Cases for {tool['name']} ---")
        
        try:
            test_cases = await mcp_test_data_generator.generate_test_cases(
                tool_name=tool["name"],
                tool_description=tool["description"],
                input_schema=tool["input_schema"],
                max_cases=6
            )
            
            print(f"Generated {len(test_cases)} test cases:")
            for i, case in enumerate(test_cases, 1):
                print(f"\n  Test Case {i} ({case.test_type} - {case.difficulty}):")
                print(f"    Description: {case.description}")
                print(f"    Arguments: {json.dumps(case.arguments, indent=6)}")
                print(f"    Expected: {case.expected_behavior}")
                
        except Exception as e:
            print(f"  ERROR: Failed to generate test cases: {e}")

async def test_quality_assessor():
    """Test the LLM-powered quality assessor."""
    print("\n" + "="*60)
    print("TESTING LLM-POWERED QUALITY ASSESSOR")
    print("="*60)
    
    # Sample test scenarios with responses
    test_scenarios = [
        {
            "tool_name": "search_arxiv",
            "tool_description": "Search for academic papers on arXiv",
            "arguments": {"query": "machine learning", "max_results": 5},
            "response": {
                "papers": [
                    {
                        "title": "Attention Is All You Need",
                        "authors": ["Vaswani, A.", "Shazeer, N."],
                        "abstract": "The dominant sequence transduction models...",
                        "arxiv_id": "1706.03762",
                        "category": "cs.LG",
                        "published": "2017-06-12"
                    },
                    {
                        "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                        "authors": ["Devlin, J.", "Chang, M-W."],
                        "abstract": "We introduce a new language representation model...",
                        "arxiv_id": "1810.04805",
                        "category": "cs.CL",
                        "published": "2018-10-11"
                    }
                ],
                "total_found": 12847,
                "query_time_ms": 234
            },
            "expected": "Should return relevant machine learning papers with metadata",
            "description": "Search for popular ML papers"
        },
        {
            "tool_name": "file_manager",
            "tool_description": "Manage files and directories",
            "arguments": {"action": "read", "path": "/nonexistent/file.txt"},
            "response": {
                "error": "FileNotFoundError",
                "message": "File not found: /nonexistent/file.txt",
                "code": "FILE_NOT_FOUND",
                "suggestions": [
                    "Check if the file path is correct",
                    "Ensure the file exists before reading",
                    "Use 'list' action to see available files"
                ]
            },
            "expected": "Should return clear error message for missing file",
            "description": "Attempt to read non-existent file"
        },
        {
            "tool_name": "weather_api",
            "tool_description": "Get current weather information",
            "arguments": {"location": "San Francisco", "units": "metric"},
            "response": {
                "temperature": 18.5,
                "humidity": 72,
                "description": "Partly cloudy",
                "wind_speed": 12.3,
                "location": "San Francisco, CA"
            },
            "expected": "Should return current weather data",
            "description": "Get weather for major city"
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n--- Assessing Quality for {scenario['tool_name']} ---")
        print(f"Test: {scenario['description']}")
        
        try:
            assessment = await mcp_quality_assessor.assess_response_quality(
                tool_name=scenario["tool_name"],
                tool_description=scenario["tool_description"],
                test_arguments=scenario["arguments"],
                response_data=scenario["response"],
                expected_behavior=scenario["expected"],
                test_description=scenario["description"]
            )
            
            print(f"\n  QUALITY ASSESSMENT:")
            print(f"    Overall Score: {assessment.overall_score:.1f}/10")
            print(f"    Relevance: {assessment.relevance_score:.1f}/10")
            print(f"    Accuracy: {assessment.accuracy_score:.1f}/10")
            print(f"    Completeness: {assessment.completeness_score:.1f}/10")
            print(f"    Usability: {assessment.usability_score:.1f}/10")
            print(f"    Format: {assessment.format_score:.1f}/10")
            print(f"    Is Error Response: {assessment.is_error_response}")
            
            print(f"\n  EXPLANATION:")
            print(f"    {assessment.explanation}")
            
            if assessment.strengths:
                print(f"\n  STRENGTHS:")
                for strength in assessment.strengths:
                    print(f"    + {strength}")
            
            if assessment.weaknesses:
                print(f"\n  WEAKNESSES:")
                for weakness in assessment.weaknesses:
                    print(f"    - {weakness}")
            
            if assessment.suggestions:
                print(f"\n  SUGGESTIONS:")
                for suggestion in assessment.suggestions:
                    print(f"    → {suggestion}")
                    
        except Exception as e:
            print(f"  ERROR: Quality assessment failed: {e}")

async def test_integrated_workflow():
    """Test the integrated workflow: generate test cases + assess quality."""
    print("\n" + "="*60)
    print("TESTING INTEGRATED WORKFLOW")
    print("="*60)
    
    # Sample tool
    tool = {
        "name": "code_analyzer",
        "description": "Analyze code files for complexity, style, and potential issues",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the code file to analyze"
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "java", "cpp"],
                    "description": "Programming language of the file"
                },
                "checks": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["complexity", "style", "security", "performance"]
                    },
                    "description": "Types of checks to perform"
                }
            },
            "required": ["file_path", "language"]
        }
    }
    
    print(f"Testing integrated workflow for: {tool['name']}")
    
    try:
        # Step 1: Generate test cases
        print("\n1. Generating test cases...")
        test_cases = await mcp_test_data_generator.generate_test_cases(
            tool_name=tool["name"],
            tool_description=tool["description"], 
            input_schema=tool["input_schema"],
            max_cases=4
        )
        
        print(f"   Generated {len(test_cases)} test cases")
        
        # Step 2: Simulate responses and assess quality
        print("\n2. Simulating responses and assessing quality...")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   Test Case {i}: {test_case.description}")
            print(f"   Arguments: {json.dumps(test_case.arguments, indent=14)}")
            
            # Simulate a response based on the test case
            simulated_response = generate_simulated_response(test_case)
            
            # Assess quality
            assessment = await mcp_quality_assessor.assess_response_quality(
                tool_name=tool["name"],
                tool_description=tool["description"],
                test_arguments=test_case.arguments,
                response_data=simulated_response,
                expected_behavior=test_case.expected_behavior,
                test_description=test_case.description
            )
            
            print(f"   Quality Score: {assessment.overall_score:.1f}/10")
            print(f"   Assessment: {assessment.explanation}")
            
    except Exception as e:
        print(f"ERROR: Integrated workflow failed: {e}")

def generate_simulated_response(test_case):
    """Generate a simulated response based on the test case type and arguments."""
    
    if test_case.test_type == "invalid":
        return {
            "error": "ValidationError", 
            "message": "Invalid input parameters provided",
            "details": "Check the required parameters and their types"
        }
    elif "empty" in test_case.description.lower() or "missing" in test_case.description.lower():
        return {
            "error": "FileNotFoundError",
            "message": "Code file not found or is empty", 
            "suggestions": ["Verify file path exists", "Check file permissions"]
        }
    else:
        # Simulate successful response
        return {
            "analysis_results": {
                "complexity_score": 7.2,
                "style_issues": 3,
                "security_warnings": 0,
                "performance_suggestions": 2,
                "lines_of_code": 248,
                "functions_analyzed": 12
            },
            "summary": "Code analysis completed successfully with moderate complexity",
            "execution_time_ms": 1543
        }

async def main():
    """Run all quality system tests."""
    print("LLM-POWERED MCP QUALITY ASSESSMENT SYSTEM DEMO")
    print("=" * 80)
    
    try:
        await test_data_generator()
        await test_quality_assessor()
        await test_integrated_workflow()
        
        print("\n" + "="*60)
        print("DEMO COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nThe LLM-powered quality system includes:")
        print("✓ Advanced test case generation with realistic scenarios")
        print("✓ Intelligent quality assessment with detailed scoring")
        print("✓ Error handling evaluation")
        print("✓ Comprehensive feedback and improvement suggestions")
        print("✓ Integration with the existing MCP testing framework")
        
    except Exception as e:
        print(f"\nDEMO FAILED: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 