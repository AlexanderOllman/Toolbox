import os
import argparse
import logging
from rag_search import ToolRAG # Assuming rag_search.py is in the same directory or PYTHONPATH

# Configure logging - Optional, but good practice
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Example script to demonstrate ToolRAG functionality.")
    parser.add_argument("query", type=str, help="The search query to find relevant tools.")
    parser.add_argument("--openai-key", type=str, default=os.environ.get("OPENAI_API_KEY"), help="OpenAI API Key. Can also be set via OPENAI_API_KEY environment variable.")
    parser.add_argument("--qdrant-host", type=str, default=os.environ.get("QDRANT_HOST", "localhost"), help="Qdrant host.")
    parser.add_argument("--qdrant-port", type=int, default=int(os.environ.get("QDRANT_PORT", 6333)), help="Qdrant port.")
    parser.add_argument("--collection", type=str, default=os.environ.get("QDRANT_COLLECTION_NAME", "mcp_servers"), help="Qdrant collection name.")
    # Optional: If your payload fields are different from ToolRAG defaults
    # parser.add_argument("--name-field", type=str, default=ToolRAG.DEFAULT_PAYLOAD_NAME_FIELD, help="Payload field for tool name.")
    # parser.add_argument("--desc-field", type=str, default=ToolRAG.DEFAULT_PAYLOAD_TEXT_FIELD, help="Payload field for tool description.")

    args = parser.parse_args()

    if not args.openai_key:
        logger.error("OpenAI API Key is required. Set --openai-key or use the OPENAI_API_KEY environment variable.")
        print("Error: OpenAI API Key is required. Please provide it via --openai-key argument or set the OPENAI_API_KEY environment variable.")
        return

    logger.info(f"Running example script for query: '{args.query}'")

    try:
        # 1. Initialize the ToolRAG instance
        # You can customize parameters like payload_name_field, payload_text_field, search_limit, etc.
        # if they differ from the defaults in the ToolRAG class.
        rag_instance = ToolRAG(
            openai_api_key=args.openai_key,
            qdrant_host=args.qdrant_host,
            qdrant_port=args.qdrant_port,
            qdrant_collection_name=args.collection
            # payload_name_field=args.name_field, # Uncomment if using custom field
            # payload_text_field=args.desc_field  # Uncomment if using custom field
        )

        # 2. Use the 'ask' method to get an explanation of relevant tools
        logger.info(f"Asking ToolRAG about the query: '{args.query}'")
        explanation = rag_instance.ask(args.query)

        # 3. Print the explanation
        print("\n--- Tool Relevance Explanation ---")
        print(explanation)
        print("----------------------------------")

        # Alternatively, if you only need the raw search results (PointStruct objects):
        # search_results = rag_instance.retrieve(args.query)
        # print("\n--- Raw Qdrant Search Results ---")
        # for i, point in enumerate(search_results):
        #     print(f"Result {i+1}: ID={point.id}, Score={point.score:.4f}, Payload={point.payload}")
        # print("---------------------------------")


    except ValueError as ve: # Catch specific errors like missing API key from ToolRAG init
        logger.error(f"Configuration error: {ve}")
        print(f"Error: {ve}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"\nAn unexpected error occurred. Please check the logs. Reason: {e}")
    finally:
        logger.info("Example script execution finished.")

if __name__ == "__main__":
    main() 