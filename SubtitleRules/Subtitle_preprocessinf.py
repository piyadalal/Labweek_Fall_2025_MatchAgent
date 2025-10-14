import os
import json
import re
from dotenv import load_dotenv
from openai import AzureOpenAI
import weaviate
from weaviate.classes.query import Filter
from datetime import datetime


# -------------------- Step 1: Read and Chunk STL File --------------------
def read_stl_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def chunk_text(text, chunk_size=500):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]


import os

def save_llm_output_to_json(response, output_file):
    """
    Extracts, cleans, parses, and saves JSON output from LLM response to file.
    """

    # 1️⃣ Extract content string
    content = response.choices[0].message.content.strip()

    # 2️⃣ Remove Markdown-style code fences (```json ... ```)
    content = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.DOTALL)

    # 3️⃣ Try parsing JSON output
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            parsed = [parsed]
    except json.JSONDecodeError:
        print("⚠️ LLM did not return valid JSON. Saving raw text instead.")
        parsed = [{"raw_text": content}]

    # 4️⃣ If file exists, load old data and merge
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

    # 5️⃣ Extend and save
    existing_data.extend(parsed)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {len(parsed)} events to {output_file}")


import json
import re
import json
import re

def extract_all_json_objects(json_file):
    """
    Reads the file and extracts only valid JSON arrays or objects,
    ignoring any raw text or explanation text.
    Returns a flat list of all parsed JSON entries.
    """
    with open(json_file, "r", encoding="utf-8") as f:
        raw = f.read()

    # Find all potential JSON-like lists or dicts (even inside text)
    json_blocks = re.findall(r"\[\s*{.*?}\s*\]", raw, flags=re.DOTALL)

    all_events = []

    for block in json_blocks:
        try:
            data = json.loads(block)
            # Ensure it’s a list of dicts
            if isinstance(data, list):
                all_events.extend([
                    item for item in data if isinstance(item, dict)
                ])
        except json.JSONDecodeError:
            continue

    return all_events


def read_event_types_from_json(json_file):
    """Reads only 'event_type' from valid JSON parts of the file."""
    all_events = extract_all_json_objects(json_file)
    event_types = [
        e["event_type"]
        for e in all_events
        if isinstance(e, dict) and "event_type" in e
    ]
    return event_types


def read_event_types_from_json(json_file):
    """
    Reads all event types from saved JSON, including those embedded as text in raw_text fields.
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    event_types = []

    def extract_from_item(item):
        """Recursive helper to extract event types from dicts/lists/text."""
        if isinstance(item, dict):
            # If dict has event_type directly
            if "event_type" in item:
                event_types.append(item["event_type"])
            # If dict has raw_text that contains JSON — extract JSON inside text
            elif "raw_text" in item and isinstance(item["raw_text"], str):
                match = re.search(r"\[.*\]", item["raw_text"], flags=re.DOTALL)
                if match:
                    try:
                        embedded = json.loads(match.group(0))
                        extract_from_item(embedded)
                    except Exception:
                        pass
            else:
                # Recurse through all dict values
                for v in item.values():
                    extract_from_item(v)
        elif isinstance(item, list):
            for sub in item:
                extract_from_item(sub)

    extract_from_item(data)
    return event_types



# -------------------- Step 2: Extract Events via LLM --------------------
def extract_events(client, chunk, llm_output_filename):
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

    save_llm_output_to_json(response, llm_output_filename)
    # import json
    # import re
    #
    # content = response.choices[0].message.content.strip()
    # #print(content)
    #
    # # Remove ```json or ``` and closing ```
    # content = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.DOTALL)
    #
    # # Try parsing as JSON
    # try:
    #     parsed = json.loads(content)
    #     if isinstance(parsed, dict):
    #         parsed = [parsed]
    # except json.JSONDecodeError:
    #     print("⚠️ Could not parse JSON, saving raw text.")
    #     parsed = [{"raw_text": content}]
    #
    # # Save parsed data to JSON file
    # output_file = "events.json"
    # with open(output_file, "w", encoding="utf-8") as f:
    #     json.dump(parsed, f, indent=2, ensure_ascii=False)
    #
    # print(f"✓ Saved parsed content to {output_file}")


# -------------------- Step 3: Store LLM Output to JSON File --------------------
# def save_to_json(new_data, output_file):
#     if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
#         with open(output_file, "r", encoding="utf-8") as f:
#             try:
#                 existing_data = json.load(f)
#                 if not isinstance(existing_data, list):
#                     existing_data = [existing_data]
#             except json.JSONDecodeError:
#                 existing_data = []
#     else:
#         existing_data = []
#
#     existing_data.extend(new_data)
#
#     with open(output_file, "w", encoding="utf-8") as f:
#         json.dump(existing_data, f, indent=2, ensure_ascii=False)

# -------------------- Step 4: Insert to Weaviate --------------------
import json
import re

def insert_to_weaviate(wv_client, data):
    """
    Ensures 'Commentary' collection exists once,
    then inserts parsed event data every time this function is called.
    """

    # 1️⃣ Check existing collections
    existing_collections = [c for c in wv_client.collections.list_all()]

    # 2️⃣ Create only if it doesn't exist
    if "Commentary" not in existing_collections:
        wv_client.collections.create(
            name="Commentary",
            properties=[
                {"name": "event_type", "dataType": "string"},
                {"name": "player", "dataType": "string"},
                {"name": "team", "dataType": "string"},
            ]
        )
        print("✅ Created 'Commentary' collection.")
    else:
        print("✅ 'Commentary' collection already exists.")

    # 3️⃣ Get the collection reference
    collection = wv_client.collections.get("Commentary")

    inserted_count = 0
    skipped_count = 0

    # 4️⃣ Parse and insert events
    for item in data:
        raw_text = item.get("raw_text", "")

        try:
            # Extract JSON content if in ```json blocks
            json_str = re.search(r'```json\n(.*?)```', raw_text, re.DOTALL)
            if json_str:
                parsed_events = json.loads(json_str.group(1))
            else:
                parsed_events = json.loads(raw_text)
        except Exception as e:
            print(f"⚠️ Skipping item due to parsing error: {e}")
            skipped_count += 1
            continue

        print(parsed_events)

        if isinstance(parsed_events, list):
            for event in parsed_events:
                event_type = event.get("event_type")
                player = event.get("player")
                team = event.get("team")

                # Normalize potential None/list values
                event_type_str = str(event_type or "")
                player_str = str(player[0] if isinstance(player, list) and player else player or "")
                team_str = str(team[0] if isinstance(team, list) and team else team or "")

                try:
                    collection.data.insert({
                        "event_type": event_type_str,
                        "player": player_str,
                        "team": team_str,
                        "inserted_at": datetime.now(),
                    })
                    inserted_count += 1
                except Exception as e:
                    print(f"⚠️ Failed to insert event: {e}")
                    skipped_count += 1
            else:
                print(f"⚠️ Unexpected format: {type(parsed_events)}")
                skipped_count += 1

    print(f"Insert summary: {inserted_count} inserted, {skipped_count} skipped.")


# -------------------- Query and Explanation --------------------

# -------------------- Query and Explanation --------------------
def query(wv_client, limit=20, event_type=None):
    """
    Query events from Weaviate with optional filtering by event_type.
    Returns most recent events first (sorted by inserted_at descending).
    """
    collection = wv_client.collections.get("Commentary")

    # Build the query with optional filter
    if event_type:
        results = collection.query.fetch_objects(
            filters=Filter.by_property("event_type").equal(event_type),
            limit=limit
        )
    else:
        results = collection.query.fetch_objects(
            limit=limit
        )

    # Extract and sort results manually by inserted_at if needed
    output = []
    for obj in results.objects:
        output.append({
            "event_type": obj.properties.get("event_type"),
            "player": obj.properties.get("player"),
            "team": obj.properties.get("team"),
            "inserted_at": obj.properties.get("inserted_at")
        })

    # Sort by inserted_at descending (most recent first)
    output.sort(key=lambda x: x.get("inserted_at") or "", reverse=True)

    # Remove inserted_at from output for cleaner results
    for item in output:
        item.pop("inserted_at", None)

    print(output)
    return output


def parse_events_from_json(json_data):
    """
    Parses the event_extraction_output.json and extracts structured events.
    Returns a list of event dictionaries with event_type, player, and team.
    """
    parsed_events = []

    for item in json_data:
        raw_text = item.get("raw_text", "")

        if not raw_text:
            continue

        try:
            # Extract JSON content if wrapped in ```json blocks
            json_str = re.search(r'```json\n(.*?)```', raw_text, re.DOTALL)
            if json_str:
                events = json.loads(json_str.group(1))
            else:
                events = json.loads(raw_text)
        except Exception as e:
            print(f"⚠️ Skipping item due to parsing error: {e}")
            continue

        # Normalize to list
        if isinstance(events, dict):
            events = [events]

        if isinstance(events, list):
            for event in events:
                event_type = event.get("event_type", "")
                player = event.get("player", "")
                team = event.get("team", "")
                timestamp = event.get("timestamp", "")

                # Normalize list values
                if isinstance(player, list):
                    player = player[0] if player else ""
                if isinstance(team, list):
                    team = team[0] if team else ""

                parsed_events.append({
                    "timestamp": str(timestamp),
                    "event_type": str(event_type),
                    "player": str(player),
                    "team": str(team)
                })

    print(f"✅ Parsed {len(parsed_events)} events from JSON")
    return parsed_events


def event_type_explanation(client, events, dir_path, filename):
    formatted = []
    for i, event in enumerate(events, 1):
        # Skip events without event_type
        if not event.get("event_type"):
            print(f"Warning: Event {i} missing 'event_type' field, skipping...")
            continue

        parts = []
        if event.get("player"):
            parts.append(f"Player: {event['player']}")
        if event.get("team"):
            parts.append(f"Team: {event['team']}")
        parts.append(f"Event: {event['event_type']}")
        formatted.append(f"{len(formatted) + 1}. {' | '.join(parts)}")

    # Check if we have any valid events to process
    if not formatted:
        print("No valid events with 'event_type' found.")
        return None

    prompt = (
        "You are a football commentator explaining live match events to beginners. "
        "For each event (goal, foul, offside, penalty, etc.), explain briefly what it means, "
        "the rule behind it, and how it affects the match flow — in simple, clear terms. "
        "Avoid repeating rule explanations for the same event type. "
        "Focus on clarity, impact, and next actions.\n\n"
        f"Here are the match events:\n{chr(10).join(formatted)}"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )

    explanation_text = response.choices[0].message.content
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(explanation_text)

    print(f"Explanation saved to {file_path}")
    return explanation_text

# -------------------- Main Process --------------------
def main():
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



    stl_file_path = "/Users/prda5207/PycharmProjects/Labweek_Fall_2025_MatchAgent/SubtitleRules/Data/TESTFeedforSTLsubtitlefile.stl"
    #stl_file_path = "/Users/prda5207/PycharmProjects/Labweek_Fall_2025_MatchAgent/SubtitleRules/Data/AIgeneratedSubtitles.stl"
    #output_json = "/Users/prda5207/PycharmProjects/Labweek_Fall_2025_MatchAgent/SubtitleRules/gpt_outputs/event_extraction_output.json"
    llm_output_filename = "/Users/prda5207/PycharmProjects/Labweek_Fall_2025_MatchAgent/SubtitleRules/events.json"
    llm_output_filename = "/Users/prda5207/PycharmProjects/Labweek_Fall_2025_MatchAgent/SubtitleRules/match_events.json"
    if not os.path.exists(stl_file_path):
        print(f"STL file not found: {stl_file_path}")
        return

    print("Reading STL file...")
    text = read_stl_file(stl_file_path)
    chunks = chunk_text(text)
    os.makedirs("gpt_outputs", exist_ok=True)
    #for chunk in chunks:
         #extract_events(client, chunk,llm_output_filename)
         #extraced_json = save_to_json(extracted, output_json)
    print("LLM extraction complete.")
    events=extract_all_json_objects(llm_output_filename)
    print(events)

    event_types = read_event_types_from_json(llm_output_filename)
    #print(event_types)

    # # Weaviate Client Setup
    # wv_client = weaviate.connect_to_weaviate_cloud(
    #     cluster_url=wcs_cluster_url,
    #     auth_credentials=weaviate.AuthApiKey(wcs_api_key),
    #     headers={"X-OpenAI-Api-Key": openai_key} if openai_key else None
    # )
    # print("Connected to Weaviate Cloud:", wv_client.is_ready())



    # # Read saved data and insert to Weaviate
    # with open(output_json, "r", encoding="utf-8") as f:
    #     try:
    #         data = json.load(f)
    #         insert_to_weaviate(wv_client, data)
    #     except json.JSONDecodeError:
    #         print("JSON decode error in saved output.")



    # use_db = False
    # if use_db:
    #     events = query(wv_client, limit=5)
    # else:
    #     events= parse_events_from_json(output_json)
    #
    if event_types:
        event_type_explanation(client, events, dir_path="gpt_outputs/", filename="explanation.txt")
    else:
        print("No events found.")

    #wv_client.close()
    print("Processing complete.")

if __name__ == "__main__":
    main()
