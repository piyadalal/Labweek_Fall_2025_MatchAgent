
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv
from openai import OpenAI
import weaviate
from openai import AzureOpenAI
import weaviate
import json
import os

# -------------------- Load environment --------------------
load_dotenv()

azure_endpoint = os.getenv("azure_endpoint_gpt4o")
azure_api_key = os.getenv("azure_endpoint_gpt4o_key")
wcs_cluster_url = os.getenv("WCS_CLUSTER_URL")
wcs_api_key = os.getenv("WCS_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")  # optional for Weaviate if using text2vec-openai

# -------------------- Initialize Azure OpenAI --------------------
os.environ["OPENAI_API_KEY"] = azure_api_key
os.environ["OPENAI_API_BASE"] = azure_endpoint
os.environ["OPENAI_API_TYPE"] = "azure"
os.environ["OPENAI_API_VERSION"] = "2025-01-01-preview"

client = AzureOpenAI(
    azure_endpoint=azure_endpoint,
    api_key=azure_api_key,
    api_version="2025-01-01-preview",
)

# -------------------- Connect to Weaviate Cloud --------------------
wv_client = weaviate.connect_to_weaviate_cloud(
    cluster_url=wcs_cluster_url,
    auth_credentials=weaviate.AuthApiKey(wcs_api_key),
    headers={"X-OpenAI-Api-Key": openai_key} if openai_key else None
)
print("Connected to Weaviate Cloud:", wv_client.is_ready())





# -------------------- send the chunk to LLM to extract football events in JSON:--------------------

def extract_events(chunk):
    """
    Send the chunk to LLM to extract football events in JSON:
    [{timestamp, event_type, player, team}]
    """
    prompt = f"""
    Extract football match events from the following text:
    {chunk}

    For each event, return JSON with fields: timestamp (if mentioned), event_type 
    (goal, foul, penalty, substitution, offside, free kick, yellow/red card, corner, injury),
    player (if mentioned), team (if mentioned). Return as a list of objects.
    """
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    # Response text
    content = resp.choices[0].message.content

    # storing content to file
    import json
    output_dir = "gpt_outputs"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "event_extraction_output.json")

    # Load existing data if available and valid
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        with open(output_file, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = [existing_data]
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []

    # Try to parse GPT content as JSON
    try:
        new_data = json.loads(content)
        if isinstance(new_data, dict):
            new_data = [new_data]  # wrap single dict in list
    except json.JSONDecodeError:
        # If GPT output is not valid JSON, store it as raw text
        new_data = [{"raw_text": content}]

    # Append new data
    existing_data.extend(new_data)

    # Save back to file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)




# -------------------- Helper functions --------------------
def chunk_text(text, chunk_size=500):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

def get_embedding(text):
    resp = client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    print(resp.data[0].embedding)
    return resp.data[0].embedding




# -------------------- Weaviate : create schema add data from gpt to schema--------------------


if "Commentary" not in [c for c in wv_client.collections.list_all()]:
    client.collections.create(
        name="Commentary",
        properties=[
            {"name": "event_type", "dataType": "string"},
            {"name": "player", "dataType": "string"},
            {"name": "team", "dataType": "string"},
        ]
    )
    print("Collection created!")
else:
    print("Collection already exists.")


# -------------------- Load saved GPT response --------------------
output_file = "/SubtitlesToRules/gpt_outputs/event_extraction_output.json"

if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)  # This should be a list of event dicts
        except json.JSONDecodeError:
            print("Error: GPT output JSON is invalid")
            data = []
else:
    print("No GPT output found")
    data = []

# --- Insert the data ---
collection = wv_client.collections.get("Commentary")

# --- insert data from JSON ---
for item in data:
    collection.data.insert({
        "event_type": item.get("event_type"),
        "player": item.get("player"),
        "team": item.get("team"),
    })

print(" Data successfully saved to Weaviate!")


# -------------------- Close client --------------------
wv_client.close()
print("Processing complete!")


