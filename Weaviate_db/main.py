from .schema import create_commentary_schema
from .insert import insert_events
import os
def main():
    # Step 1: Create schema
    create_commentary_schema()

    # Step 2: Example events to insert
    base_path = "Data/gemini"

    events = [
        {"event_type": "goal",
         "explanation": "A goal is scored when the ball crosses the goal line between the goalposts."},
        {"event_type": "penalty", "explanation": "A penalty is awarded for a foul inside the penalty area."},
        {"event_type": "foul",
         "explanation": "A foul occurs when a player breaks the rules by unfairly contacting another player."},
        {"event_type": "redcard",
         "explanation": "A red card is shown to a player who commits a serious offense and is sent off."},
    ]

    # Dynamically assign image paths
    for event in events:
        event_type = event["event_type"]
        event["image"] = os.path.join(base_path, f"{event_type}_.img")

    # ✅ Print to verify
    for e in events:
        print(e)

    # Step 3: Insert events
    insert_events(events)


if __name__ == "__main__":
    main()
