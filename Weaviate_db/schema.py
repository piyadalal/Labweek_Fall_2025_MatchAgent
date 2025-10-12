from Weaviate_db.client import get_client_cloud

client = get_client_cloud()

# Define the class schema
class_schema = {
    "class": "Commentary",
    "vectorizer": "none",  # Provide your own embeddings
    "properties": [
        {"name": "text", "dataType": ["text"]},
        {"name": "timestamp", "dataType": ["string"]},
        {"name": "player", "dataType": ["text"]},  # optional
        {"name": "team", "dataType": ["text"]}     # optional
    ]
}

# Check if class exists
existing_classes = [c["class"] for c in client.schema.get()["classes"]]
if "Commentary" not in existing_classes:
    client.schema.create_class(class_schema)
    print("Class 'Commentary' created!")
else:
    print("Class 'Commentary' already exists.")
