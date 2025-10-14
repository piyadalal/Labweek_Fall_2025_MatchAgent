import os
import sys
from pathlib import Path
# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from typing import List
from dotenv import load_dotenv
from openai import AzureOpenAI
import weaviate
from weaviate.classes.query import Filter
from datetime import datetime
import json
import re

from GCP.sports_terms import football_terms, basketball_terms, f1_terms


# -------------------- Step 1: Read and Chunk STL File --------------------
def read_stl_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def chunk_text(text, chunk_size=500):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]


def create_football_term_folders(terms_dict, base_dir="Conciseinfo"):
    """
    Create a folder for each football term and save its definition in a text file.
    """
    os.makedirs(base_dir, exist_ok=True)
    print(football_terms)
    for key, definition in football_terms.items():
        # Normalize folder name (remove special chars, keep readability)
        folder_name = re.sub(r'[^\w\s-]', '', key).strip().replace(" ", "_")
        folder_path = os.path.join(base_dir, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Create concise_<key>.txt file
        file_name = f"concise_{folder_name}.txt"
        file_path = os.path.join(folder_path, file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(definition.strip())

        print(f"✅ Created folder and file: {file_path}")

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
    #
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



def normalize_name(name: str) -> str:
    """Lowercase and remove non-alphanumeric characters."""
    return re.sub(r'\W+', '', name.lower())


# creates folder for all the events detected in game to fill with their prompts for gemini, concise explanation and
# AI generated explanation and then their images
def read_event_folders(event_types, base_dir="output", new_base_dir="Image_prompts"):
    """
    Reads images and prompt text from folders matching event_types.
    - Folder search is case-insensitive and ignores special characters.
    - Always creates a folder for each event_type under new_base_dir (no duplicates).
    - Also creates a file named <event_type>.txt inside each new folder.
    """
    events_data = []

    # Ensure base dirs exist
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(new_base_dir, exist_ok=True)

    # List all existing folders in base_dir
    all_folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]

    for event_type in event_types:
        normalized_search = normalize_name(event_type)

        # Always create folder in Image_prompts
        new_folder_name = event_type.replace(" ", "_")
        new_folder_path = os.path.join(new_base_dir, new_folder_name)
        os.makedirs(new_folder_path, exist_ok=True)
        print(f"📁 Ensured folder exists: {new_folder_path}")

        # ✅ Create a file named after the event_type
        file_path = os.path.join(new_folder_path, f"{new_folder_name}.txt")
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"File for event type: {event_type}\n")
            print(f"📝 Created file: {file_path}")
        else:
            print(f"ℹ️ File already exists: {file_path}")

        # Find matching folders in base_dir (case-insensitive, partial)
        matching_folders = [f for f in all_folders if normalized_search in normalize_name(f)]

        if not matching_folders:
            print(f"⚠️ No folder matching '{event_type}' found in '{base_dir}'. Created new empty one.")
            continue

        # Otherwise, read images and prompt
        for folder in matching_folders:
            event_dir = os.path.join(base_dir, folder)

            # Read prompt text if exists
            prompt_file = os.path.join(event_dir, f"{folder}_prompt.txt")
            prompt_text = ""
            if os.path.exists(prompt_file):
                with open(prompt_file, "r", encoding="utf-8") as f:
                    prompt_text = f.read().strip()

            # Read all images in folder
            for file in os.listdir(event_dir):
                if file.lower().endswith((".png", ".jpg", ".jpeg")):
                    image_path = os.path.join(event_dir, file)
                    with open(image_path, "rb") as img_f:
                        image_bytes = img_f.read()
                        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

                        events_data.append({
                            "event_type": folder,
                            "prompt_text": prompt_text,
                            "image": image_base64,
                            "image_name": file
                        })

    return events_data

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


def save_llm_output_to_json(response, output_file):
    """Extracts JSON from LLM response and appends to output JSON file."""
    content = response.choices[0].message.content.strip()
    content = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.DOTALL)

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            parsed = [parsed]
    except json.JSONDecodeError:
        print("⚠️ Could not parse JSON, saving raw text.")
        parsed = [{"raw_text": content}]

    # Append to existing file if it exists
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    existing.extend(parsed)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


def extract_all_json_objects(file_path):
    """Reads all valid JSON objects from file."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, dict):
            data = [data]
    return data


def read_event_types_from_json(json_file):
    """Reads only 'event_type' from valid JSON parts of the file."""
    all_events = extract_all_json_objects(json_file)
    event_types = [
        e["event_type"]
        for e in all_events
        if isinstance(e, dict) and "event_type" in e
    ]
    return list(set(event_types))  # remove duplicates


def read_stl_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def chunk_text(text, chunk_size=500):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]


def subtitle_to_event_types(stl_file: str, client, llm_output_filename: str) -> List[str]:
    """
    Reads a subtitle (.stl) file, extracts football events via LLM,
    saves parsed events JSON, and returns the list of unique event types.
    """
    text = read_stl_file(stl_file)
    chunks = chunk_text(text)

    print(f"Processing {len(chunks)} text chunks from {stl_file}...")

    for i, chunk in enumerate(chunks, 1):
        print(f"→ Sending chunk {i}/{len(chunks)} to LLM...")
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

    event_types = read_event_types_from_json(llm_output_filename)
    print(f"Extracted event types: {event_types}")
    return event_types


import json
import os
import re

def append_explanation_to_json(json_file, explanation_file):
    """
    Reads a formatted explanation text file and appends the matching explanations
    to each event in the given JSON file based on event_type.
    """

    # Step 1: Read and parse the explanation text
    if not os.path.exists(explanation_file):
        print(f"⚠️ Explanation file not found: {explanation_file}")
        return

    with open(explanation_file, "r", encoding="utf-8") as f:
        text = f.read()

    # Use regex to extract sections like: **Event Type**
    # and the text that follows until the next event heading
    pattern = r"\*\*(.*?)\*\*.*?(?=\n---|\Z)"
    matches = re.findall(pattern, text, flags=re.DOTALL)

    # Create mapping of event_type → explanation text
    explanations = {}
    sections = re.split(r"\n---\n", text)

    for section in sections:
        event_match = re.search(r"\*\*(.*?)\*\*", section)
        if event_match:
            event_name = event_match.group(1).strip().lower()
            explanations[event_name] = section.strip()

    print(f"✅ Extracted {len(explanations)} event explanations from text file.")

    # Step 2: Load the JSON file
    if not os.path.exists(json_file):
        print(f"⚠️ JSON file not found: {json_file}")
        return

    with open(json_file, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Invalid JSON file format.")
            return

    if isinstance(data, dict):
        data = [data]

    # Step 3: Append matching explanations
    for event in data:
        if isinstance(event, dict) and "event_type" in event:
            etype = event["event_type"].lower()
            # Find closest matching explanation (partial match allowed)
            matched_explanation = None
            for key in explanations.keys():
                if key in etype or etype in key:
                    matched_explanation = explanations[key]
                    break
            if matched_explanation:
                event["explanation"] = matched_explanation

    # Step 4: Save updated JSON
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Explanations appended to events in {json_file}")

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

    #print("Reading STL file...")
    #event_types = subtitle_to_event_types(stl_file_path, client, llm_output_filename)
    #print(event_types)
    append_explanation_to_json(llm_output_filename, "/Users/prda5207/PycharmProjects/Labweek_Fall_2025_MatchAgent/SubtitleRules/gpt_outputs/explanation.txt")

    #text = read_stl_file(stl_file_path)
    #chunks = chunk_text(text)

    os.makedirs("gpt_outputs", exist_ok=True)
    #for chunk in chunks:
         #extract_events(client, chunk,llm_output_filename)
         #extraced_json = save_to_json(extracted, output_json)
    #print("LLM extraction complete.")
    #events=extract_all_json_objects(llm_output_filename)
    #print(events)

    #event_types = read_event_types_from_json(llm_output_filename)
    #print(event_types)

    #read_event_folders(event_types)

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
    #if event_types:
    #    event_type_explanation(client, events, dir_path="gpt_outputs/", filename="explanation.txt")
    #else:
    #    print("No events found.")

    sports_data = {
        "football": football_terms,
        #"basketball": basketball_terms,
        #"f1": f1_terms
    }
    #create_football_term_folders(football_terms)
    #print("🏁 All football term folders created successfully.")

    #wv_client.close()
    print("Processing complete.")

if __name__ == "__main__":
    main()
