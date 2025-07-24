import json
import logging
from typing import Dict, List, Any, Optional, Tuple
import asyncio
from dataclasses import dataclass

from .openai_service import client as openai_client

logger = logging.getLogger(__name__)

@dataclass
class QualityAssessment:
    """Represents a quality assessment of an MCP tool response."""
    overall_score: float  # 0.0 to 10.0
    relevance_score: float  # How relevant is the response to the request
    accuracy_score: float  # How accurate/correct does the response appear
    completeness_score: float  # How complete is the response
    usability_score: float  # How usable/actionable is the response
    format_score: float  # How well-formatted is the response
    
    explanation: str  # Detailed explanation of the assessment
    strengths: List[str]  # What the response does well
    weaknesses: List[str]  # What could be improved
    suggestions: List[str]  # Suggestions for improvement
    
    is_error_response: bool  # Whether this was an error response
    error_handling_quality: Optional[float] = None  # Quality of error handling (if applicable)

class MCPQualityAssessor:
    """
    Advanced quality assessor that uses LLMs to evaluate the quality, 
    usefulness, and correctness of MCP tool responses.
    """
    
    def __init__(self):
        self.openai_client = openai_client
        if not self.openai_client:
            logger.warning("OpenAI client not available. Quality assessment will use fallback methods.")
    
    async def assess_response_quality(self, tool_name: str, tool_description: str,
                                    test_arguments: Dict[str, Any], 
                                    response_data: Any,
                                    expected_behavior: str = "",
                                    test_description: str = "") -> QualityAssessment:
        """
        Assess the quality of an MCP tool response using LLM analysis.
        
        Args:
            tool_name: Name of the tool that was called
            tool_description: Description of what the tool does
            test_arguments: Arguments that were passed to the tool
            response_data: The actual response from the tool
            expected_behavior: Description of expected behavior
            test_description: Description of the test case
            
        Returns:
            Comprehensive quality assessment
        """
        logger.debug(f"Assessing response quality for tool: {tool_name}")
        
        # Check if OpenAI client is available
        if not self.openai_client:
            logger.warning(f"OpenAI client not available, using fallback quality assessment for {tool_name}")
            return QualityAssessment(
                overall_score=6.0,
                relevance_score=6.0,
                accuracy_score=6.0,
                completeness_score=6.0,
                usability_score=6.0,
                format_score=6.0,
                explanation="OpenAI client not available - basic functionality assessment only",
                strengths=["Tool executed successfully"] if response_data else [],
                weaknesses=["Detailed quality assessment not available"],
                suggestions=["Configure OpenAI API key for detailed quality analysis"],
                is_error_response=self._is_error_response(response_data)
            )
        
        try:
            # Determine if this is an error response
            is_error = self._is_error_response(response_data)
            
            if is_error:
                return await self._assess_error_response(
                    tool_name, tool_description, test_arguments, 
                    response_data, expected_behavior, test_description
                )
            else:
                return await self._assess_success_response(
                    tool_name, tool_description, test_arguments, 
                    response_data, expected_behavior, test_description
                )
                
        except Exception as e:
            logger.error(f"Failed to assess response quality for {tool_name}: {e}")
            # Return basic assessment on failure
            return QualityAssessment(
                overall_score=5.0,
                relevance_score=5.0,
                accuracy_score=5.0,
                completeness_score=5.0,
                usability_score=5.0,
                format_score=5.0,
                explanation="Quality assessment failed due to technical error",
                strengths=[],
                weaknesses=["Assessment could not be completed"],
                suggestions=[],
                is_error_response=False
            )
    
    async def _assess_success_response(self, tool_name: str, tool_description: str,
                                     test_arguments: Dict[str, Any], response_data: Any,
                                     expected_behavior: str, test_description: str) -> QualityAssessment:
        """Assess the quality of a successful response."""
        
        # Prepare response data for LLM (limit size to avoid token limits)
        response_str = self._prepare_response_for_analysis(response_data)
        
        prompt = f"""
Assess the quality of this MCP tool response on a scale of 0-10 for each dimension.

TOOL INFORMATION:
Tool Name: {tool_name}
Tool Description: {tool_description}
Test Description: {test_description}

INPUT:
Arguments Provided: {json.dumps(test_arguments, indent=2)}
Expected Behavior: {expected_behavior}

ACTUAL RESPONSE:
{response_str}

Please evaluate the response on these dimensions (0-10 scale):

1. RELEVANCE (0-10): How well does the response address the request?
2. ACCURACY (0-10): How accurate and correct does the information appear?
3. COMPLETENESS (0-10): How complete is the response? Does it include expected information?
4. USABILITY (0-10): How useful and actionable is the response for a user?
5. FORMAT (0-10): How well-structured and formatted is the response?

Also provide:
- 3-5 specific strengths of the response
- 3-5 areas for improvement (if any)
- 2-3 suggestions for making the response better
- Overall assessment explanation (2-3 sentences)

Respond ONLY with this JSON structure:
{{
  "relevance_score": 8.5,
  "accuracy_score": 9.0,
  "completeness_score": 7.5,
  "usability_score": 8.0,
  "format_score": 9.0,
  "explanation": "The response effectively addresses the user's request with relevant information...",
  "strengths": [
    "Provides specific and relevant information",
    "Well-structured output format",
    "Includes all requested data fields"
  ],
  "weaknesses": [
    "Could include more context about data sources",
    "Response format could be more user-friendly"
  ],
  "suggestions": [
    "Add metadata about data freshness",
    "Include confidence scores for results"
  ]
}}
"""
        
        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower temperature for more consistent assessments
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            assessment_data = json.loads(content)
            
            # Calculate overall score as weighted average
            overall_score = (
                assessment_data.get("relevance_score", 5) * 0.25 +
                assessment_data.get("accuracy_score", 5) * 0.25 +
                assessment_data.get("completeness_score", 5) * 0.2 +
                assessment_data.get("usability_score", 5) * 0.2 +
                assessment_data.get("format_score", 5) * 0.1
            )
            
            return QualityAssessment(
                overall_score=overall_score,
                relevance_score=assessment_data.get("relevance_score", 5.0),
                accuracy_score=assessment_data.get("accuracy_score", 5.0),
                completeness_score=assessment_data.get("completeness_score", 5.0),
                usability_score=assessment_data.get("usability_score", 5.0),
                format_score=assessment_data.get("format_score", 5.0),
                explanation=assessment_data.get("explanation", ""),
                strengths=assessment_data.get("strengths", []),
                weaknesses=assessment_data.get("weaknesses", []),
                suggestions=assessment_data.get("suggestions", []),
                is_error_response=False
            )
            
        except Exception as e:
            logger.error(f"Failed to parse LLM assessment: {e}")
            # Return neutral assessment
            return QualityAssessment(
                overall_score=6.0,
                relevance_score=6.0,
                accuracy_score=6.0,
                completeness_score=6.0,
                usability_score=6.0,
                format_score=6.0,
                explanation="Response appears functional but detailed assessment failed",
                strengths=["Tool executed successfully"],
                weaknesses=["Could not perform detailed quality analysis"],
                suggestions=[],
                is_error_response=False
            )
    
    async def _assess_error_response(self, tool_name: str, tool_description: str,
                                   test_arguments: Dict[str, Any], response_data: Any,
                                   expected_behavior: str, test_description: str) -> QualityAssessment:
        """Assess the quality of an error response."""
        
        response_str = self._prepare_response_for_analysis(response_data)
        
        prompt = f"""
Assess the quality of this MCP tool ERROR response.

TOOL INFORMATION:
Tool Name: {tool_name}
Tool Description: {tool_description}
Test Description: {test_description}

INPUT:
Arguments Provided: {json.dumps(test_arguments, indent=2)}
Expected Behavior: {expected_behavior}

ERROR RESPONSE:
{response_str}

Evaluate the ERROR HANDLING quality (0-10 scale):

1. ERROR_CLARITY (0-10): How clear and understandable is the error message?
2. HELPFULNESS (0-10): Does the error help users understand what went wrong?
3. ACTIONABILITY (0-10): Does the error suggest how to fix the problem?
4. APPROPRIATENESS (0-10): Is the error response appropriate for the input provided?

Also assess:
- Whether the error was expected or unexpected
- Quality of error message formatting
- Suggestions for improving error handling

Respond ONLY with this JSON structure:
{{
  "error_handling_score": 7.5,
  "explanation": "Error message is clear but could be more helpful...",
  "strengths": [
    "Clear error code provided",
    "Identifies the specific problem"
  ],
  "weaknesses": [
    "Could suggest how to fix the issue",
    "Error message could be more user-friendly"
  ],
  "suggestions": [
    "Include examples of valid input formats",
    "Add suggestions for correcting the error"
  ],
  "was_expected": true,
  "is_appropriate": true
}}
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
            assessment_data = json.loads(content)
            
            error_score = assessment_data.get("error_handling_score", 5.0)
            
            return QualityAssessment(
                overall_score=error_score,
                relevance_score=error_score,  # For errors, relevance = appropriateness
                accuracy_score=error_score,   # For errors, accuracy = correctness of error
                completeness_score=error_score,  # For errors, completeness = information provided
                usability_score=error_score,     # For errors, usability = helpfulness
                format_score=error_score,        # For errors, format = clarity
                explanation=assessment_data.get("explanation", ""),
                strengths=assessment_data.get("strengths", []),
                weaknesses=assessment_data.get("weaknesses", []),
                suggestions=assessment_data.get("suggestions", []),
                is_error_response=True,
                error_handling_quality=error_score
            )
            
        except Exception as e:
            logger.error(f"Failed to assess error response: {e}")
            return QualityAssessment(
                overall_score=4.0,
                relevance_score=4.0,
                accuracy_score=4.0,
                completeness_score=4.0,
                usability_score=4.0,
                format_score=4.0,
                explanation="Error occurred but could not assess error handling quality",
                strengths=[],
                weaknesses=["Error assessment failed"],
                suggestions=[],
                is_error_response=True,
                error_handling_quality=4.0
            )
    
    def _is_error_response(self, response_data: Any) -> bool:
        """Determine if a response represents an error condition."""
        
        if isinstance(response_data, dict):
            # Check for common error indicators
            if "error" in response_data:
                return True
            if "status" in response_data and response_data["status"] in ["error", "failed", "failure"]:
                return True
            if "success" in response_data and not response_data["success"]:
                return True
            # Check if response is empty or null
            if not response_data or all(v is None for v in response_data.values()):
                return True
        
        # Check for string error responses
        if isinstance(response_data, str) and any(
            keyword in response_data.lower() 
            for keyword in ["error", "failed", "exception", "invalid", "not found"]
        ):
            return True
        
        return False
    
    def _prepare_response_for_analysis(self, response_data: Any, max_length: int = 2000) -> str:
        """Prepare response data for LLM analysis, limiting size to avoid token limits."""
        
        if response_data is None:
            return "null"
        
        if isinstance(response_data, (dict, list)):
            response_str = json.dumps(response_data, indent=2, ensure_ascii=False)
        else:
            response_str = str(response_data)
        
        # Truncate if too long
        if len(response_str) > max_length:
            response_str = response_str[:max_length - 50] + "\n... [Response truncated for analysis]"
        
        return response_str
    
    async def assess_multiple_responses(self, tool_name: str, tool_description: str,
                                      test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Assess multiple test responses and provide aggregate quality metrics.
        
        Args:
            tool_name: Name of the tool
            tool_description: Description of the tool
            test_results: List of test results with responses
            
        Returns:
            Aggregate quality assessment with statistics
        """
        logger.info(f"Assessing multiple responses for tool: {tool_name}")
        
        assessments = []
        
        for test_result in test_results:
            try:
                assessment = await self.assess_response_quality(
                    tool_name=tool_name,
                    tool_description=tool_description,
                    test_arguments=test_result.get("arguments", {}),
                    response_data=test_result.get("response"),
                    expected_behavior=test_result.get("expected_behavior", ""),
                    test_description=test_result.get("description", "")
                )
                assessments.append(assessment)
            except Exception as e:
                logger.error(f"Failed to assess individual response: {e}")
                continue
        
        if not assessments:
            return {
                "overall_quality_score": 0.0,
                "assessment_count": 0,
                "quality_metrics": {},
                "common_strengths": [],
                "common_weaknesses": [],
                "improvement_suggestions": []
            }
        
        # Calculate aggregate metrics
        overall_scores = [a.overall_score for a in assessments]
        relevance_scores = [a.relevance_score for a in assessments]
        accuracy_scores = [a.accuracy_score for a in assessments]
        completeness_scores = [a.completeness_score for a in assessments]
        usability_scores = [a.usability_score for a in assessments]
        format_scores = [a.format_score for a in assessments]
        
        # Collect common themes
        all_strengths = []
        all_weaknesses = []
        all_suggestions = []
        
        for assessment in assessments:
            all_strengths.extend(assessment.strengths)
            all_weaknesses.extend(assessment.weaknesses)
            all_suggestions.extend(assessment.suggestions)
        
        # Find most common items (simple frequency count)
        common_strengths = list(set(all_strengths))[:5]  # Top 5 unique strengths
        common_weaknesses = list(set(all_weaknesses))[:5]  # Top 5 unique weaknesses
        improvement_suggestions = list(set(all_suggestions))[:5]  # Top 5 unique suggestions
        
        return {
            "overall_quality_score": sum(overall_scores) / len(overall_scores),
            "assessment_count": len(assessments),
            "quality_metrics": {
                "average_relevance": sum(relevance_scores) / len(relevance_scores),
                "average_accuracy": sum(accuracy_scores) / len(accuracy_scores),
                "average_completeness": sum(completeness_scores) / len(completeness_scores),
                "average_usability": sum(usability_scores) / len(usability_scores),
                "average_format": sum(format_scores) / len(format_scores),
                "min_score": min(overall_scores),
                "max_score": max(overall_scores),
                "score_variance": sum((s - sum(overall_scores)/len(overall_scores))**2 for s in overall_scores) / len(overall_scores)
            },
            "common_strengths": common_strengths,
            "common_weaknesses": common_weaknesses,
            "improvement_suggestions": improvement_suggestions,
            "error_responses": len([a for a in assessments if a.is_error_response]),
            "success_responses": len([a for a in assessments if not a.is_error_response])
        }

# Global instance
mcp_quality_assessor = MCPQualityAssessor() 