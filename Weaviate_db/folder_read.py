import os

base_path = "Data/gemini"

events = [
    {"event_type": "goal", "explanation": "A goal is scored when the ball crosses the goal line between the goalposts."},
    {"event_type": "penalty", "explanation": "A penalty is awarded for a foul inside the penalty area."},
    {"event_type": "foul", "explanation": "A foul occurs when a player breaks the rules by unfairly contacting another player."},
    {"event_type": "redcard", "explanation": "A red card is shown to a player who commits a serious offense and is sent off."},
]

# Dynamically assign image paths
for event in events:
    event_type = event["event_type"]
    event["image"] = os.path.join(base_path, f"{event_type}_.img")

# ✅ Print to verify
for e in events:
    print(e)
