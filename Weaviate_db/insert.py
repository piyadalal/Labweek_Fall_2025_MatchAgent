def insert_events(client, events):
    """
    events: List of dicts like
    {"timestamp": "00:12", "event_type": "goal", "player_team": "Player X", "commentary_chunk": "..."}
    """
    collection = client.collections.get("Event")

    for e in events:
        collection.data.insert(
            properties={
                "timestamp": e.get("timestamp", ""),
                "event_type": e.get("event", ""),
                "player_team": e.get("player_team", ""),
                "commentary_chunk": e.get("commentary_chunk", "")
            }
        )
    print(f"{len(events)} events inserted.")
