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

from app.services.config_service import get_config_value

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
    if not api_key:
        raise ValueError("OpenAI API key not found in configuration or environment variables")
    
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
        
        # Scroll through all points in the collection
        scroll_result = client.scroll(
            collection_name=get_collection_name(),
            limit=100,  # Adjust as needed
            with_payload=True,
            with_vectors=False
        )
        points = scroll_result[0]  # First element contains the points
        
        repositories = []
        for idx, point in enumerate(points):
            payload = point.payload
            repositories.append({
                "id": idx + 1,
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
                "env": payload.get("env", "{}"),
                "roots_table": payload.get("roots_table", "")
            })
        return repositories
    except Exception as e:
        logger.error(f"Error getting repositories from Qdrant: {str(e)}")
        return []

def get_repository(name: str) -> Optional[Dict[str, Any]]:
    """Get a repository by name."""
    try:
        client = get_qdrant_client()
        
        # Search for the repository by name
        search_result = client.search(
            collection_name=get_collection_name(),
            query_vector=[0.0] * VECTOR_SIZE,  # Dummy vector
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="name",
                        match=MatchValue(value=name)
                    )
                ]
            ),
            limit=1,
            with_payload=True,
            with_vectors=False
        )
        
        if not search_result:
            return None
        
        payload = search_result[0].payload
        return {
            "id": 1,  # This would be replaced with a real ID in a proper DB
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
            "env": payload.get("env", "{}"),
            "roots_table": payload.get("roots_table", "")
        }
    except Exception as e:
        logger.error(f"Error getting repository from Qdrant: {str(e)}")
        return None

def add_repository(name: str, description: str, command: str, args: List[str], transport: str = "stdio", 
                  url: str = "", read_timeout_seconds: Optional[int] = None, 
                  read_transport_sse_timeout_seconds: int = 300, headers: str = "{}", 
                  api_key: str = "", env: str = "{}", roots_table: str = "") -> Dict[str, Any]:
    """Add a repository to the database."""
    try:
        client = get_qdrant_client()
        
        # Create payload with all fields from the new schema
        payload = {
            "name": name,
            "description": description,
            "command": command,
            "args": args,
            "transport": transport,
            "url": url,
            "read_timeout_seconds": read_timeout_seconds,
            "read_transport_sse_timeout_seconds": read_transport_sse_timeout_seconds,
            "headers": headers,
            "api_key": api_key,
            "env": env,
            "roots_table": roots_table
        }
        
        # Generate embedding for the description
        try:
            vector = get_embedding(description)
        except Exception as e:
            logger.warning(f"Could not generate embedding for '{name}': {str(e)}. Using zero vector.")
            vector = [0.0] * VECTOR_SIZE
        
        # Create point with embedding vector
        point_id = generate_point_id(name)
        point = PointStruct(id=point_id, vector=vector, payload=payload)
        
        # Upsert point
        client.upsert(
            collection_name=get_collection_name(),
            points=[point]
        )

        # If roots_table is specified, create a collection for it
        if roots_table:
            init_server_roots_collection(roots_table)
        
        return {
            "id": 1,  # This would be replaced with a real ID in a proper DB
            "name": name,
            "description": description,
            "command": command,
            "args": args,
            "transport": transport,
            "url": url,
            "read_timeout_seconds": read_timeout_seconds,
            "read_transport_sse_timeout_seconds": read_transport_sse_timeout_seconds,
            "headers": headers,
            "api_key": api_key,
            "env": env,
            "roots_table": roots_table
        }
    except Exception as e:
        logger.error(f"Error adding repository to Qdrant: {str(e)}")
        # Re-raise to ensure API calls fail properly
        raise e

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

# Initialize database on module load
init_db() 
