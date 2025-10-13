from . import client
from weaviate.classes.config import Property, DataType


def create_commentary_schema():
    wv_client = client.get_client_cloud()
    print("Connected to Weaviate Cloud:", wv_client.is_ready())

    if "ImageData" not in [c for c in wv_client.collections.list_all()]:
        wv_client.collections.create(
            name="ImageData",
            properties=[
                Property(name="event_type", data_type=DataType.TEXT),
                Property(name="explanation", data_type=DataType.TEXT),
                Property(name="image", data_type=DataType.TEXT),
            ]
        )
        print("✓ Created 'ImageData' collection with properties: event_type, explanation, image")
    else:
        print("✓ 'ImageData' collection already exists.")

    wv_client.close()