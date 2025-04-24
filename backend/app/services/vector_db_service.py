import os
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
from typing import List, Dict, Any, Optional
import hashlib
import logging
import requests
from requests.exceptions import RequestException

from app.services.config_service import get_config_value

# Vector size for text-embedding-3-small
VECTOR_SIZE = 1536  # text-embedding-3-small output dimension

# Set up logging
logger = logging.getLogger(__name__)

def get_collection_name():
    """Get the collection name from config"""
    return get_config_value("COLLECTION_NAME", "mcp_servers")

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
    
    # Log the connection parameters
    logger.info(f"Creating Qdrant client with host={host}, port={port}")
    
    # Set a short timeout to avoid hanging
    return QdrantClient(host=host, port=port, timeout=5.0)

def check_qdrant_connection() -> Dict[str, Any]:
    """Check if connection to Qdrant server is available using a simple HTTP request."""
    # Always get the latest settings directly from the database
    host = get_config_value("QDRANT_HOST", "localhost")
    port = int(get_config_value("QDRANT_PORT", "6333"))
    collection = get_collection_name()
    
    logger.info(f"Checking connection to Qdrant server at {host}:{port}, collection: {collection}")
    
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
        collection_name = get_collection_name()
        
        # Create collection if it doesn't exist
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
        logger.info(f"Vector database initialized successfully with collection {collection_name}")
        return True
    except Exception as e:
        logger.warning(f"Vector database initialization failed: {str(e)}")
        return False

def search_repositories(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search for repositories by query text."""
    connection_status = check_qdrant_connection()
    if connection_status["status"] != "connected":
        logger.warning(f"Skipping vector search: {connection_status['message']}")
        return []
    
    try:
        client = get_qdrant_client()
        collection_name = get_collection_name()
        
        # Generate embedding for query
        query_embedding = get_embedding(query)
        
        # Search for similar vectors
        search_results = client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=limit,
        )
        
        # Format results
        results = []
        for result in search_results:
            payload = result.payload
            results.append({
                "name": payload.get("name"),
                "description": payload.get("description"),
                "score": result.score,
                "command": payload.get("command"),
                "args": payload.get("args", [])
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