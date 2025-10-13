from Weaviate_db.client import get_client_cloud

def insert_events(events):
    """
    events: List of dicts with keys: event_type, explanation, image
    """
    wv_client = get_client_cloud()
    collection = wv_client.collections.get("ImageData")

    for event in events:
        collection.data.insert(event)

    print(f"✓ {len(events)} events inserted into 'ImageData' collection.")
    wv_client.close()
