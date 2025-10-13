from .schema import create_commentary_schema
from .insert import insert_events

def main():
    # Step 1: Create schema
    create_commentary_schema()

    # Step 2: Example events to insert
    events = [
        {
            "event_type": "goal",
            "explanation": "A goal is scored when the ball crosses the goal line between the goalposts.",
            "image": "https://example.com/goal_image.png"
        },
        {
            "event_type": "penalty",
            "explanation": "A penalty is awarded for a foul inside the penalty area.",
            "image": "https://example.com/penalty_image.png"
        }
    ]

    # Step 3: Insert events
    insert_events(events)


if __name__ == "__main__":
    main()
