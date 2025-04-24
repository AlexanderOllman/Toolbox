import os
import openai
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from typing import List, Dict, Any, Optional
import hashlib
import logging
import requests
from requests.exceptions import RequestException

from app.services.config_service import get_config_value

# Define collection name and vector size
COLLECTION_NAME = "repositories"
VECTOR_SIZE = 1536  # text-embedding-3-small output dimension

# Set up logging
logger = logging.getLogger(__name__)

def get_qdrant_client():
    """Get a Qdrant client using configuration from the database."""
    host = get_config_value("QDRANT_HOST", "localhost")
    port = int(get_config_value("QDRANT_PORT", "6333"))
    
    # Log the connection parameters
    logger.info(f"Creating Qdrant client with host={host}, port={port}")
    
    # Set a short timeout to avoid hanging
    return QdrantClient(host=host, port=port, timeout=5.0)

def check_qdrant_connection() -> Dict[str, Any]:
    """Check if connection to Qdrant server is available using a simple HTTP request."""
    # Always get the latest settings directly from the database
    host = get_config_value("QDRANT_HOST", "localhost")
    port = int(get_config_value("QDRANT_PORT", "6333"))
    
    logger.info(f"Checking connection to Qdrant server at {host}:{port}")
    
    try:
        # Use requests directly for more reliable connection testing
        url = f"http://{host}:{port}/collections"
        logger.info(f"Making HTTP request to {url}")
        
        response = requests.get(url, timeout=5.0)
        response.raise_for_status()  # Raise exception for non-2xx responses
        
        # If we get here, the connection was successful
        logger.info(f"Successfully connected to Qdrant server at {host}:{port}")
        return {"status": "connected", "message": f"Successfully connected to Qdrant server at {host}:{port}"}
    except RequestException as e:
        error_msg = f"Failed to connect to Qdrant server at {host}:{port}: {str(e)}"
        logger.warning(error_msg)
        return {"status": "disconnected", "message": error_msg}

def init_vector_db():
    """Initialize the vector database. Handles connection failures gracefully."""
    # First check if we can connect
    connection_status = check_qdrant_connection()
    if connection_status["status"] != "connected":
        logger.warning(f"Cannot initialize vector database: {connection_status['message']}")
        return False
        
    try:
        client = get_qdrant_client()
        
        # Create collection if it doesn't exist
        if not client.collection_exists(COLLECTION_NAME):
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
        logger.info("Vector database initialized successfully")
        return True
    except Exception as e:
        logger.warning(f"Vector database initialization failed: {str(e)}")
        return False

def get_embedding(text: str) -> List[float]:
    """Generate an embedding for the given text."""
    api_key = get_config_value("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    if not api_key:
        raise ValueError("OpenAI API key not found in configuration or environment variables")
    
    openai.api_key = api_key
    response = openai.Embedding.create(input=[text], model="text-embedding-3-small")
    return response["data"][0]["embedding"]

def generate_point_id(repo_name: str) -> int:
    """Generate a deterministic point ID from repository name."""
    return int(hashlib.md5(repo_name.encode()).hexdigest(), 16) % (2**63)

def add_repository_to_vector_db(repo_name: str, description: str, metadata: Dict[str, Any]):
    """Add a repository to the vector database."""
    connection_status = check_qdrant_connection()
    if connection_status["status"] != "connected":
        logger.warning(f"Skipping vector database update: {connection_status['message']}")
        return None
    
    try:
        client = get_qdrant_client()
        
        # Generate embedding for repository description
        embedding = get_embedding(description)
        
        # Create payload with metadata and text
        payload = {
            "name": repo_name,
            "description": description,
            **metadata
        }
        
        # Insert vector into Qdrant
        point_id = generate_point_id(repo_name)
        point = PointStruct(id=point_id, vector=embedding, payload=payload)
        client.upsert(collection_name=COLLECTION_NAME, points=[point])
        
        return point_id
    except Exception as e:
        logger.error(f"Error adding repository to vector database: {str(e)}")
        return None

def delete_repository_from_vector_db(repo_name: str) -> bool:
    """Delete a repository from the vector database."""
    connection_status = check_qdrant_connection()
    if connection_status["status"] != "connected":
        logger.warning(f"Skipping vector database deletion: {connection_status['message']}")
        return False
    
    try:
        client = get_qdrant_client()
        point_id = generate_point_id(repo_name)
        
        client.delete(collection_name=COLLECTION_NAME, points_selector=[point_id])
        return True
    except Exception as e:
        logger.error(f"Error deleting repository from vector database: {str(e)}")
        return False

def search_repositories(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search for repositories by query text."""
    connection_status = check_qdrant_connection()
    if connection_status["status"] != "connected":
        logger.warning(f"Skipping vector search: {connection_status['message']}")
        return []
    
    try:
        client = get_qdrant_client()
        
        # Generate embedding for query
        query_embedding = get_embedding(query)
        
        # Search for similar vectors
        search_results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=limit,
        )
        
        # Format results
        results = []
        for result in search_results:
            results.append({
                "name": result.payload.get("name"),
                "description": result.payload.get("description"),
                "score": result.score,
                **{k: v for k, v in result.payload.items() if k not in ["name", "description"]}
            })
        
        return results
    except Exception as e:
        logger.error(f"Error searching repositories: {str(e)}")
        return []

# Try to initialize vector database on module load, but don't fail if it can't connect
try:
    init_vector_db()
except Exception as e:
    logger.warning(f"Vector database initialization skipped: {str(e)}") 