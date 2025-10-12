import os
import sys
import json
from dotenv import load_dotenv
from openai import AzureOpenAI
import weaviate
from weaviate.classes.query import Filter





# -------------------- Step 1: Read and Chunk STL File --------------------
def read_stl_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def chunk_text(text, chunk_size=500):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

# -------------------- Step 2: Extract Events via LLM --------------------
def extract_events(client,chunk):
    prompt = f"""
    Extract football match events from the following commentary text:
    {chunk}

    Return a list of JSON objects with the following keys:
    - timestamp (if mentioned)
    - event_type (e.g. goal, foul, penalty, substitution, offside, free kick, yellow/red card, corner, injury)
    - player (if mentioned)
    - team (if mentioned)
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    content = response.choices[0].message.content.strip()

    # Try parsing as JSON
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            parsed = [parsed]
    except json.JSONDecodeError:
        parsed = [{"raw_text": content}]

    return parsed

# -------------------- Step 3: Store LLM Output to JSON File --------------------
def save_to_json(new_data, output_file):
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

    existing_data.extend(new_data)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

# -------------------- Step 4: Insert to Weaviate --------------------
import re


def insert_to_weaviate(wv_client, data):
    if "Commentary" not in [c for c in wv_client.collections.list_all()]:
        wv_client.collections.create(
            name="Commentary",
            properties=[
                {"name": "event_type", "dataType": "string"},
                {"name": "player", "dataType": "string"},
                {"name": "team", "dataType": "string"},
            ]
        )
        print("✓ Created 'Commentary' collection.")
    else:
        print("✓ 'Commentary' collection already exists.")

    collection = wv_client.collections.get("Commentary")
    inserted_count = 0
    skipped_count = 0

    for item in data:
        raw_text = item.get("raw_text", "")

        # Extract JSON array from the raw_text block
        try:
            # Remove ```json\n and ``` if present
            json_str = re.search(r'```json\n(.*?)```', raw_text, re.DOTALL)
            if json_str:
                parsed_events = json.loads(json_str.group(1))
            else:
                # Try fallback: look for the first valid JSON array
                parsed_events = json.loads(raw_text)
        except Exception as e:
            print(f"⚠ Skipping item due to parsing error: {e}")
            skipped_count += 1
            continue

        # Insert each parsed event
        if isinstance(parsed_events, list):
            for event in parsed_events:
                # Ensure all values are strings (convert None to empty string)
                event_type = event.get("event_type")
                player = event.get("player")
                team = event.get("team")

                # Convert to string, handling None, lists, and other types
                event_type_str = str(event_type) if event_type is not None else ""
                player_str = str(player) if player is not None and not isinstance(player, list) else ""
                team_str = str(team) if team is not None and not isinstance(team, list) else ""

                # Handle empty lists or lists with single items
                if isinstance(player, list):
                    player_str = player[0] if len(player) > 0 else ""
                if isinstance(team, list):
                    team_str = team[0] if len(team) > 0 else ""

                try:
                    collection.data.insert({
                        "event_type": event_type_str,
                        "player": player_str,
                        "team": team_str,
                    })
                    inserted_count += 1
                except Exception as e:
                    print(f"⚠ Failed to insert event: {e}")
                    print(f"  Event data: {event}")
                    skipped_count += 1
        else:
            print(f"⚠ Unexpected event format: {type(parsed_events)}")
            skipped_count += 1

    print(f"✓ Data inserted into Weaviate: {inserted_count} events inserted, {skipped_count} skipped.")


def sanity_check_weaviate_data(wv_client):
    collection = wv_client.collections.get("Commentary")
    count_result = collection.aggregate.over_all(total_count=True)
    count = count_result.total_count
    print(f"Total objects in 'Commentary': {count}")
    results = collection.query.fetch_objects(limit=20)
    for obj in results.objects:
        print(obj.properties)

def query_goals(wv_client,limit=20, event_type="goal"):
    """
    Query all football events where event_type is 'goal' from the Commentary collection.
    """
    collection = wv_client.collections.get("Commentary")

    # Use Filter with correct API for Weaviate v4
    results = collection.query.fetch_objects(
        filters=Filter.by_property("event_type").equal(event_type),
        limit=limit
    )

    output = []
    for obj in results.objects:
        output.append({
            "event_type": obj.properties.get("event_type"),
            "player": obj.properties.get("player"),
            "team": obj.properties.get("team"),
        })

    return output


# -------------------- Main Process --------------------
def main():
    # -------------------- Environment Setup --------------------
    load_dotenv()

    azure_endpoint = os.getenv("azure_endpoint_gpt4o")
    azure_api_key = os.getenv("azure_endpoint_gpt4o_key")
    openai_key = os.getenv("OPENAI_API_KEY")
    wcs_cluster_url = os.getenv("WCS_CLUSTER_URL")
    wcs_api_key = os.getenv("WCS_API_KEY")

    # Azure OpenAI Client Setup
    os.environ["OPENAI_API_KEY"] = azure_api_key
    os.environ["OPENAI_API_BASE"] = azure_endpoint
    os.environ["OPENAI_API_TYPE"] = "azure"
    os.environ["OPENAI_API_VERSION"] = "2025-01-01-preview"

    client = AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=azure_api_key,
        api_version="2025-01-01-preview",
    )

    # Weaviate Client Setup
    wv_client = weaviate.connect_to_weaviate_cloud(
        cluster_url=wcs_cluster_url,
        auth_credentials=weaviate.AuthApiKey(wcs_api_key),
        headers={"X-OpenAI-Api-Key": openai_key} if openai_key else None
    )
    print("Connected to Weaviate Cloud:", wv_client.is_ready())

    stl_file_path = "/Users/prda5207/PycharmProjects/Labweek_Fall_2025_MatchAgent/db/Data/TESTFeedforSTLsubtitlefile.stl"  # Replace with actual path
    output_json = "/Users/prda5207/PycharmProjects/Labweek_Fall_2025_MatchAgent/Events_from_STLFile/gpt_outputs/event_extraction_output.json"

    if not os.path.exists(stl_file_path):
        print(f" STL file not found: {stl_file_path}")
        return

    print("Reading STL file...")
    #text = read_stl_file(stl_file_path)
    #chunks = chunk_text(text)

    os.makedirs("gpt_outputs", exist_ok=True)

    #for chunk in chunks:
    #    extracted = extract_events(client,chunk)
    #    save_to_json(extracted, output_json)

    print("LLM extraction complete.")

    # Read saved data and insert to Weaviate
    with open(output_json, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            insert_to_weaviate(wv_client, data)
        except json.JSONDecodeError:
            print("JSON decode error in saved output.")

    print(query_goals(wv_client, limit=10,event_type="penalty"))
    wv_client.close()
    print("Processing complete.")





if __name__ == "__main__":
    main()
