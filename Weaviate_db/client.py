import os
import weaviate
from weaviate.auth import AuthApiKey
from dotenv import load_dotenv


load_dotenv()

def get_client_cloud():
    # Load credentials from .env file
    load_dotenv()

    cluster_url = os.getenv("WCS_CLUSTER_URL")
    api_key = os.getenv("WCS_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")  # Optional: if you plan to use OpenAI module

    # Connect to your Weaviate Cloud instance
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=cluster_url,
        auth_credentials=AuthApiKey(api_key),
        headers={"X-OpenAI-Api-Key": openai_key} if openai_key else None
    )

    print("Connected to Weaviate Cloud!")
    return client



def get_client_local():
    # For local instance at http://localhost:8080
    client = weaviate.connect_to_local(
        host="localhost",
        port=8080
    )

    return client




with get_client_cloud() as c:
    print(c.is_ready())  # Should return True

