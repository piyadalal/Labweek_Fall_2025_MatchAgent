import subprocess
from azure.storage.blob import BlobServiceClient, BlobClient
import os
from openai import AzureOpenAI
import io
from dotenv import load_dotenv

load_dotenv()

# Azure Blob setup
conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
container_name = "labweek3773blob"
blob_name = "match_video_1.mp4"
blob_service_client = BlobServiceClient.from_connection_string(conn_str)

# Create container if it doesn't exist
try:
    blob_service_client.create_container(container_name)
    print(f"Created container: {container_name}")
except Exception as e:
    print(f"Container already exists: {e}")

blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

# Path to your local video file
local_video_path = "Data/BULI Kiel - Augsburg 15. Spieltag 2425 PGM.mp4"

# # Upload the file to blob storage
# print(f"Uploading {local_video_path} to blob storage...")
# with open(local_video_path, "rb") as data:
#     blob_client.upload_blob(data, overwrite=True)
# print(f"Successfully uploaded to blob {blob_name} in container {container_name}")

# Create 'audio' folder if it doesn't exist
os.makedirs("audio", exist_ok=True)
audio_output_path = os.path.join("audio", "match_audio.mp3")

try:
    print("Extracting audio from video using ffmpeg...")
    subprocess.run([
        'ffmpeg', '-i', local_video_path,
        '-vn', '-acodec', 'libmp3lame',
        '-ar', '16000', '-ac', '1',
        '-b:a', '128k', audio_output_path,
        '-y'
    ], check=True, capture_output=True)
    print(f"Audio successfully saved to: {audio_output_path}")

except subprocess.CalledProcessError as e:
    print(f"Error during audio extraction: {e}")
    print(f"FFmpeg stderr: {e.stderr.decode() if e.stderr else 'No error output'}")
