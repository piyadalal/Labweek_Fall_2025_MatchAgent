import weaviate
import os
from client import get_client_cloud
from dotenv import load_dotenv
load_dotenv()

print(weaviate.__version__)  # Must print 4.10.1



wcs_cluster_url = os.getenv("WCS_CLUSTER_URL")
wcs_api_key = os.getenv("WCS_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")
# -------------------- Connect to Weaviate Cloud --------------------


try:
    client = get_client_cloud()

    # Get your Commentary collection
    collection = client.collections.get("Commentary")

    # Query objects WITHOUT filtering to see what properties exist
    results = collection.query.fetch_objects(
        limit=10
    )

    # Print the first object to inspect available properties
    if results.objects:
        print("Sample object properties:")
        print(results.objects[0].properties)
        print("\nAll objects:")

        # Iterate through all objects
        for obj in results.objects:
            print(obj.properties)
    else:
        print("No objects found in the collection")

finally:
    # Always close the client connection
    client.close()
