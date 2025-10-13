from Weaviate_db.client import get_client_cloud
from weaviate.classes.query import Filter

def fetch_events_by_type(event_type, limit=20):
    """
    Fetch events from the 'Commentary' collection filtered by event_type.
    Returns a list of dicts with keys: event_type, explanation, image.
    """
    wv_client = get_client_cloud()
    collection = wv_client.collections.get("ImageData")

    # Use Weaviate filter with Filter class
    results = collection.query.fetch_objects(
        filters=Filter.by_property("event_type").equal(event_type),
        limit=limit
    )

    output = []
    for obj in results.objects:
        output.append({
            "event_type": obj.properties.get("event_type"),
            "explanation": obj.properties.get("explanation"),
            "image": obj.properties.get("image"),
        })

    wv_client.close()
    return output


def fetch_all_events(limit=50):
    """
    Fetch all events from the 'Commentary' collection.
    """
    wv_client = get_client_cloud()
    collection = wv_client.collections.get("Commentary")

    results = collection.query.fetch_objects(limit=limit)

    output = []
    for obj in results.objects:
        output.append({
            "event_type": obj.properties.get("event_type"),
            "explanation": obj.properties.get("explanation"),
            "image": obj.properties.get("image"),
        })

    wv_client.close()
    return output


# Example usage
if __name__ == "__main__":
    events = fetch_events_by_type("goal", limit=5)
    for e in events:
        print(f"{e['event_type']}: {e['explanation']} ({e['image']})")