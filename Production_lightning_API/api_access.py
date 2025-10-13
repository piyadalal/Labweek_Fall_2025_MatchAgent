import requests
import os



# Schedule endpoint
url = "https://lightning.spex.aidisco.sky.com/lightning/schedule"
params = {"territory": "DE", "sport": "football"}
headers = {"x-api-key": os.getenv("LIGHTNING_API_KEY")}

response = requests.get(url, headers=headers, params=params)
print(response.status_code)
print(response.json())

# Example: Notifications (use a gameId from the schedule response)
#notif_url = "https://lightning.spex.aidisco.sky.com/lightning/notifications_
