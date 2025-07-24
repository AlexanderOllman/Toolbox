import json
from typing import List, Dict, Any, Optional
import os
import logging
import hashlib
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
import sys # Import sys for direct stderr access

from app.services.config_service import get_config_value
from app.models.repositories import EnvVarDetail # Import the new model

# Set up logging
logger = logging.getLogger(__name__)

# Collection name
def get_collection_name():
    """Get the collection name from config or use default"""
    return get_config_value("COLLECTION_NAME", "mcp_servers")

# Vector size for text-embedding-3-small
VECTOR_SIZE = 1536

def get_embedding(text: str) -> List[float]:
    """Generate an embedding for the given text."""
    api_key = get_config_value("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    # logger.info(f"[get_embedding] Text to embed: '{text}'") # Original logging, can be re-enabled if needed
    if not api_key:
        logger.warning("[get_embedding] OpenAI API key not found. Returning zero vector.")
        return [0.0] * VECTOR_SIZE  # Return a zero vector
    
    # logger.info(f"[get_embedding] OpenAI API key found (length: {len(api_key)}). Proceeding to create embedding.") # Original logging
    try:
        # Create client with the updated OpenAI SDK approach
        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            input=[text],
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise

def get_qdrant_client():
    """Get a Qdrant client using configuration from the database."""
    host = get_config_value("QDRANT_HOST", "localhost")
    port = int(get_config_value("QDRANT_PORT", "6333"))
    
    logger.info(f"Creating Qdrant client with host={host}, port={port}")
    return QdrantClient(host=host, port=port, timeout=5.0)

def generate_point_id(name: str) -> int:
    """Generate a deterministic point ID from server name."""
    return int(hashlib.md5(name.encode()).hexdigest(), 16) % (2**63)

def init_db():
    """Initialize the database with required collection."""
    try:
        client = get_qdrant_client()
        
        # Create collection if it doesn't exist
        if not client.collection_exists(get_collection_name()):
            client.create_collection(
                collection_name=get_collection_name(),
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info(f"Initialized {get_collection_name()} collection in Qdrant")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant collection: {str(e)}")

def init_server_roots_collection(collection_name: str):
    """Initialize a server_roots collection for a specific server."""
    try:
        client = get_qdrant_client()
        
        # Create collection if it doesn't exist
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info(f"Initialized {collection_name} collection in Qdrant for server roots")
            return True
    except Exception as e:
        logger.error(f"Failed to initialize server roots collection {collection_name}: {str(e)}")
        return False

def get_repositories() -> List[Dict[str, Any]]:
    """Get all repositories from the database."""
    try:
        client = get_qdrant_client()
        collection_name = get_collection_name()
        if not client.collection_exists(collection_name):
            logger.warning(f"Collection '{collection_name}' does not exist. Returning empty list.")
            return []
        scroll_result = client.scroll(
            collection_name=collection_name,
            limit=1000, with_payload=True, with_vectors=False
        )
        points = scroll_result[0]
        repositories = []
        for idx, point in enumerate(points):
            payload = point.payload
            repo_name_for_log = payload.get("name", "UnknownRepo")
            
            # Process env field to reconstruct EnvVarDetail objects or ensure correct dict structure
            env_data_from_db = payload.get("env", {})
            processed_env = {}
            if isinstance(env_data_from_db, dict):
                for key, details_dict in env_data_from_db.items():
                    if isinstance(details_dict, dict) and 'value' in details_dict and 'status' in details_dict:
                        processed_env[key] = EnvVarDetail(value=details_dict.get('value'), status=details_dict.get('status', 'Optional'))
                    elif isinstance(details_dict, str): # Legacy support: if it was a simple string value
                        processed_env[key] = EnvVarDetail(value=details_dict, status='Optional')
                    else: # Store as is if it doesn't match expected structure but is a dict (might be an error state)
                        processed_env[key] = details_dict 
            
            container_args_user_data = payload.get("container_args_user", {})
            if not isinstance(container_args_user_data, dict):
                container_args_user_data = {}
            
            container_args_template_data = payload.get("container_args_template", {})
            if not isinstance(container_args_template_data, dict):
                container_args_template_data = {}

            current_repo_url = payload.get("repo_url")
            final_repo_url = current_repo_url
            if not current_repo_url:
                # Fallback to 'url' if 'repo_url' is missing, and log this occurrence
                logger.warning(f"Repository '{repo_name_for_log}' is missing 'repo_url'. Falling back to 'url' field.")
                final_repo_url = payload.get("url") # Use 'url' as a fallback
                if not final_repo_url:
                    logger.error(f"Repository '{repo_name_for_log}' is also missing 'url'. Edit link will be broken.")

            repositories.append({
                "id": point.id,
                "name": payload.get("name", ""),
                "description": payload.get("description", ""),
                "command": payload.get("command"),
                "args": payload.get("args", []),
                "transport": payload.get("transport", "stdio"),
                "url": payload.get("url", ""),
                "read_timeout_seconds": payload.get("read_timeout_seconds"),
                "read_transport_sse_timeout_seconds": payload.get("read_transport_sse_timeout_seconds", 300),
                "headers": payload.get("headers", "{}"),
                "api_key": payload.get("api_key", ""),
                "env": {k: v.dict() if isinstance(v, EnvVarDetail) else v for k, v in processed_env.items()}, # Store as dicts
                "roots_table": payload.get("roots_table", ""),
                "repo_url": final_repo_url,
                "has_dockerfile": payload.get("has_dockerfile", False),
                "deploy_as_container": payload.get("deploy_as_container", False),
                "is_external_config": payload.get("is_external_config", False),
                "container_args_template": container_args_template_data,
                "container_args_user": container_args_user_data,
                "deployment_status": payload.get("deployment_status", "not_deployed"),
                # New MCP testing fields
                "test_status": payload.get("test_status", "pending"),
                "test_results": payload.get("test_results", {}),
                "last_tested_at": payload.get("last_tested_at", None),
                "tools_discovered": payload.get("tools_discovered", []),
                "test_success_rate": payload.get("test_success_rate", None),
                # Quality assessment fields
                "average_quality_score": payload.get("average_quality_score", None),
                "quality_breakdown": payload.get("quality_breakdown", {}),
                "tool_quality_assessments": payload.get("tool_quality_assessments", {}),
            })
        logger.info(f"Retrieved and formatted {len(repositories)} repositories.")
        return repositories
    except Exception as e:
        logger.error(f"Error getting repositories from Qdrant: {str(e)}")
        return []

def get_repository(name: str) -> Optional[Dict[str, Any]]:
    """Get a repository by name."""
    try:
        client = get_qdrant_client()
        search_result = client.search(
            collection_name=get_collection_name(),
            query_vector=[0.0] * VECTOR_SIZE,  # Dummy vector
            query_filter=Filter(must=[FieldCondition(key="name", match=MatchValue(value=name))]),
            limit=1, with_payload=True, with_vectors=False
        )
        if not search_result: return None
        payload = search_result[0].payload
        repo_name_for_log = payload.get("name", "UnknownRepo") # For logging
        
        # Process env field
        env_data_from_db = payload.get("env", {})
        processed_env = {}
        if isinstance(env_data_from_db, dict):
            for key, details_dict in env_data_from_db.items():
                if isinstance(details_dict, dict) and 'value' in details_dict and 'status' in details_dict:
                    processed_env[key] = EnvVarDetail(value=details_dict.get('value'), status=details_dict.get('status', 'Optional'))
                elif isinstance(details_dict, str):
                    processed_env[key] = EnvVarDetail(value=details_dict, status='Optional')
                else:
                    processed_env[key] = details_dict
        
        container_args_user_data = payload.get("container_args_user", {})
        if not isinstance(container_args_user_data, dict):
            container_args_user_data = {}

        container_args_template_data = payload.get("container_args_template", {})
        if not isinstance(container_args_template_data, dict):
            container_args_template_data = {}
            
        current_repo_url = payload.get("repo_url")
        final_repo_url = current_repo_url
        if not current_repo_url:
            logger.warning(f"Repository '{repo_name_for_log}' is missing 'repo_url' when fetched by name. Falling back to 'url' field.")
            final_repo_url = payload.get("url")
            if not final_repo_url:
                logger.error(f"Repository '{repo_name_for_log}' is also missing 'url' when fetched by name. Edit link will be broken.")

        return {
            "id": search_result[0].id,
            "name": payload.get("name", ""),
            "description": payload.get("description", ""),
            "command": payload.get("command", ""),
            "args": payload.get("args", []),
            "transport": payload.get("transport", "stdio"),
            "url": payload.get("url", ""),
            "read_timeout_seconds": payload.get("read_timeout_seconds", None),
            "read_transport_sse_timeout_seconds": payload.get("read_transport_sse_timeout_seconds", 300),
            "headers": payload.get("headers", "{}"),
            "api_key": payload.get("api_key", ""),
            "env": {k: v.dict() if isinstance(v, EnvVarDetail) else v for k, v in processed_env.items()}, # Store as dicts
            "roots_table": payload.get("roots_table", ""),
            "repo_url": final_repo_url,
            "has_dockerfile": payload.get("has_dockerfile", False),
            "deploy_as_container": payload.get("deploy_as_container", False),
            "is_external_config": payload.get("is_external_config", False),
            "container_args_template": container_args_template_data,
            "container_args_user": container_args_user_data,
            "deployment_status": payload.get("deployment_status", "not_deployed")
        }
    except Exception as e:
        logger.error(f"Error getting repository from Qdrant: {str(e)}")
        return None

def add_repository(repo_data: Dict[str, Any]):
    """Add a new repository to the database."""
    try:
        client = get_qdrant_client()
        
        # Payload construction should now expect repo_data["env"] to be Dict[str, Dict[str,str]]
        # (i.e., already serialized EnvVarDetail objects)
        payload = {
            "name": repo_data.get("name"),
            "description": repo_data.get("description"),
            "command": repo_data.get("command"),
            "args": repo_data.get("args", []),
            "transport": repo_data.get("transport", "stdio"),
            "url": repo_data.get("url"),
            "read_timeout_seconds": repo_data.get("read_timeout_seconds"),
            "read_transport_sse_timeout_seconds": repo_data.get("read_transport_sse_timeout_seconds", 300),
            "headers": repo_data.get("headers", "{}"),
            "api_key": repo_data.get("api_key", ""),
            "env": repo_data.get("env", {}), # This should now be the Dict[str, Dict[str,str]] structure
            "roots_table": repo_data.get("roots_table", ""),
            "repo_url": repo_data.get("repo_url"),
            "has_dockerfile": repo_data.get("has_dockerfile", False),
            "deploy_as_container": repo_data.get("deploy_as_container", False),
            "container_args_template": repo_data.get("container_args_template", {}),
            "container_args_user": repo_data.get("container_args_user", {}),
            "deployment_status": repo_data.get("deployment_status", "not_deployed"),
            "is_external_config": repo_data.get("is_external_config", False),
            # New fields for MCP testing
            "test_status": repo_data.get("test_status", "pending"),  # pending, running, completed, failed
            "test_results": repo_data.get("test_results", {}),  # Store the test report
            "last_tested_at": repo_data.get("last_tested_at", None),  # ISO timestamp
            "tools_discovered": repo_data.get("tools_discovered", []),  # List of discovered tools
            "test_success_rate": repo_data.get("test_success_rate", None),  # Percentage
            # Quality assessment fields
            "average_quality_score": repo_data.get("average_quality_score", None),  # Overall quality score
            "quality_breakdown": repo_data.get("quality_breakdown", {}),  # Quality scores by dimension
            "tool_quality_assessments": repo_data.get("tool_quality_assessments", {}),  # Per-tool quality data
        }
        
        logger.info(f"Payload for Qdrant upsert (repo: {payload.get('name')}): {json.dumps(payload, indent=2)}")
        
        # Generate embedding for the description
        description_text = repo_data.get("description") or ""
        vector = get_embedding(description_text)
        point_id = generate_point_id(repo_data.get("name"))
        point = PointStruct(id=point_id, vector=vector, payload=payload)
        client.upsert(collection_name=get_collection_name(), points=[point])
        if repo_data.get("roots_table"):
            init_server_roots_collection(repo_data.get("roots_table"))
        
        return_data = payload.copy()
        return_data['id'] = point_id
        return return_data

    except Exception as e:
        logger.error(f"Failed to add repository {repo_data.get('name', '')}: {e}")
        return False

def delete_repository(name: str) -> bool:
    """Delete a repository by name."""
    try:
        client = get_qdrant_client()
        
        # Get repository first to check if it has a roots_table
        repo = get_repository(name)
        if repo and repo.get("roots_table"):
            # Try to delete the roots collection if it exists
            try:
                client.delete_collection(collection_name=repo["roots_table"])
                logger.info(f"Deleted roots collection {repo['roots_table']} for repository {name}")
            except Exception as e:
                logger.warning(f"Failed to delete roots collection {repo['roots_table']}: {str(e)}")
        
        # Delete the repository point
        point_id = generate_point_id(name)
        client.delete(
            collection_name=get_collection_name(),
            points_selector=[point_id]
        )
        
        return True
    except Exception as e:
        logger.error(f"Error deleting repository from Qdrant: {str(e)}")
        return False

def add_server_root(server_name: str, uri: str, name: str = None, server_uri_alias: str = None) -> bool:
    """Add a root directory for a server to its roots collection."""
    try:
        repo = get_repository(server_name)
        if not repo:
            logger.error(f"Cannot add root: Server {server_name} not found")
            return False
            
        roots_table = repo.get("roots_table")
        if not roots_table:
            logger.error(f"Cannot add root: Server {server_name} has no roots_table defined")
            return False
            
        client = get_qdrant_client()
        
        # Ensure the collection exists
        if not client.collection_exists(roots_table):
            success = init_server_roots_collection(roots_table)
            if not success:
                return False
                
        # Create payload for the root
        payload = {
            "server_name": server_name,
            "uri": uri,
            "name": name,
            "server_uri_alias": server_uri_alias
        }
        
        # Generate embedding for the URI
        try:
            vector = get_embedding(uri)
        except Exception as e:
            logger.warning(f"Could not generate embedding for URI '{uri}': {str(e)}. Using zero vector.")
            vector = [0.0] * VECTOR_SIZE
            
        # Create a deterministic ID based on server_name and uri
        root_id = int(hashlib.md5(f"{server_name}:{uri}".encode()).hexdigest(), 16) % (2**63)
        point = PointStruct(id=root_id, vector=vector, payload=payload)
        
        # Upsert point to the roots collection
        client.upsert(
            collection_name=roots_table,
            points=[point]
        )
        
        return True
    except Exception as e:
        logger.error(f"Error adding server root to Qdrant: {str(e)}")
        return False

def get_server_roots(server_name: str) -> List[Dict[str, Any]]:
    """Get all root directories for a server."""
    try:
        repo = get_repository(server_name)
        if not repo:
            logger.error(f"Cannot get roots: Server {server_name} not found")
            return []
            
        roots_table = repo.get("roots_table")
        if not roots_table:
            # No roots table defined for this server
            return []
            
        client = get_qdrant_client()
        
        # Check if collection exists
        if not client.collection_exists(roots_table):
            logger.warning(f"Roots collection {roots_table} does not exist for server {server_name}")
            return []
            
        # Scroll through all points in the collection
        scroll_result = client.scroll(
            collection_name=roots_table,
            limit=100,  # Adjust as needed
            with_payload=True,
            with_vectors=False
        )
        points = scroll_result[0]  # First element contains the points
        
        roots = []
        for point in points:
            payload = point.payload
            if payload.get("server_name") == server_name:
                roots.append({
                    "uri": payload.get("uri", ""),
                    "name": payload.get("name"),
                    "server_uri_alias": payload.get("server_uri_alias")
                })
                
        return roots
    except Exception as e:
        logger.error(f"Error getting server roots from Qdrant: {str(e)}")
        return []

def update_repository_fields(name: str, fields_to_update: Dict[str, Any]) -> bool:
    """Update specific fields of an existing repository in Qdrant."""
    try:
        client = get_qdrant_client()
        point_id = generate_point_id(name)
        collection_name = get_collection_name()

        # Retrieve the existing point to get its vector and full payload
        # We need to use retrieve instead of search if we know the ID and want full details.
        # Qdrant's `retrieve` method is simpler for this than search with filter.
        retrieved_points = client.retrieve(
            collection_name=collection_name,
            ids=[point_id],
            with_payload=True,
            with_vectors=True # We need the vector to update the point
        )

        if not retrieved_points:
            logger.error(f"Repository '{name}' with point ID {point_id} not found for update.")
            return False
        
        existing_point = retrieved_points[0]
        existing_payload = existing_point.payload
        existing_vector = existing_point.vector

        if existing_payload is None:
            existing_payload = {} # Should not happen if point exists, but defensive

        # Merge the updates. fields_to_update takes precedence.
        updated_payload = {**existing_payload, **fields_to_update}
        
        # If the description is updated, we might need to re-generate the vector.
        # For now, we assume description (and thus the vector) is not part of this partial update.
        # If it could be, the logic would need to call get_embedding for the new description.
        if "description" in fields_to_update and fields_to_update["description"] != existing_payload.get("description"):
            logger.warning("Description updated, but vector was not re-calculated in this partial update.")
            # To re-calculate: 
            # new_description_text = updated_payload.get("description") or ""
            # existing_vector = get_embedding(new_description_text)
            # However, ensure get_embedding is async or run in thread if this function becomes async.

        # Upsert the point with the updated payload and original vector
        updated_point = PointStruct(id=point_id, vector=existing_vector, payload=updated_payload)
        client.upsert(collection_name=collection_name, points=[updated_point])
        
        logger.info(f"Successfully updated fields for repository '{name}'. Updated fields: {list(fields_to_update.keys())}")
        return True

    except Exception as e:
        logger.error(f"Error updating repository '{name}' in Qdrant: {str(e)}")
        return False

def update_repository_test_results(repo_name: str, test_report: Dict[str, Any]):
    """Update repository with MCP test results including quality assessments."""
    try:
        from datetime import datetime
        
        # Calculate success rate and extract key metrics
        success_rate = test_report.get("success_rate", 0.0)
        test_status = "completed" if test_report.get("error_message") is None else "failed"
        tools_discovered = test_report.get("tools_discovered", [])
        
        # Extract just the tool names and descriptions for easy searching
        tools_summary = [
            {
                "name": tool.get("name", ""),
                "description": tool.get("description", "")
            }
            for tool in tools_discovered
        ]
        
        # Extract quality metrics
        average_quality_score = test_report.get("average_quality_score")
        quality_breakdown = test_report.get("quality_breakdown", {})
        tool_quality_assessments = test_report.get("tool_quality_assessments", {})
        
        updates = {
            "test_status": test_status,
            "test_results": test_report,
            "last_tested_at": datetime.now().isoformat(),
            "tools_discovered": tools_summary,
            "test_success_rate": success_rate,
            # Quality assessment updates
            "average_quality_score": average_quality_score,
            "quality_breakdown": quality_breakdown,
            "tool_quality_assessments": tool_quality_assessments,
        }
        
        success = update_repository_fields(repo_name, updates)
        if success:
            quality_info = f", avg quality: {average_quality_score:.1f}" if average_quality_score else ""
            logger.info(f"Updated test results for '{repo_name}': {test_status}, {success_rate:.1f}% success rate, {len(tools_summary)} tools{quality_info}")
        return success
        
    except Exception as e:
        logger.error(f"Failed to update test results for '{repo_name}': {e}")
        return False

# Initialize database on module load
# init_db() 
