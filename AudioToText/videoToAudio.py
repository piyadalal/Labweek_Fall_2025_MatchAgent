import subprocess
from azure.storage.blob import BlobServiceClient, BlobClient
import os
from openai import AzureOpenAI
import io
from dotenv import load_dotenv
import tempfile


load_dotenv()

# Azure Blob setup
conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
container_name = "labweek3773blob"
blob_name = "match_video_1.mp4"
blob_service_client = BlobServiceClient.from_connection_string(conn_str)

# ONE TIME UPLOAD
try:
    blob_service_client.create_container(container_name)
except Exception as e:
    print("Container may already exist:", e)

blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
file = "/Users/prda5207/PycharmProjects/Labweek_Fall_2025_MatchAgent/AudioToText/Data/TEST Feed for STL subtitle file.mp4"

print(f"Uploaded {file} to blob {blob_name} in container {container_name}")

# Load credentials from environment
whisper_key = os.getenv("Whisper_key")
whisper_endpoint_full = os.getenv("Whisper_endpoint")
whisper_deployment = os.getenv("WHISPER_DEPLOYMENT_NAME", "whisper")

# Extract base endpoint from full URL
azure_endpoint = whisper_endpoint_full.split("/openai/")[0] if whisper_endpoint_full else None

# Initialize Azure OpenAI client
client = AzureOpenAI(
    api_key=whisper_key,
    api_version="2024-06-01",
    azure_endpoint=azure_endpoint
)

print("Downloading blob content into memory...")
blob_data = blob_client.download_blob()
video_stream = io.BytesIO(blob_data.readall())

# Create temporary files for processing
with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
    temp_video.write(video_stream.getvalue())
    temp_video_path = temp_video.name

with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
    temp_audio_path = temp_audio.name

try:
    print("Extracting audio from video using ffmpeg...")
    # Extract audio from video and convert to MP3
    # -i: input file
    # -vn: disable video
    # -acodec libmp3lame: use MP3 codec
    # -ar 16000: set sample rate to 16kHz (optimal for Whisper)
    # -ac 1: mono audio
    # -b:a 128k: bitrate 128kbps
    subprocess.run([
        'ffmpeg', '-i', temp_video_path,
        '-vn', '-acodec', 'libmp3lame',
        '-ar', '16000', '-ac', '1',
        '-b:a', '128k', temp_audio_path,
        '-y'  # overwrite output file if exists
    ], check=True, capture_output=True)

    print("Audio extraction successful!")

    # Check file size (Whisper limit is 25MB)
    audio_size = os.path.getsize(temp_audio_path)
    print(f"Audio file size: {audio_size / (1024 * 1024):.2f} MB")

    if audio_size > 25 * 1024 * 1024:
        print("Warning: File size exceeds 25MB. Consider splitting the audio.")

    # Read the audio file and send to Whisper
    with open(temp_audio_path, 'rb') as audio_file:
        print("Sending to Whisper for transcription...")
        transcription = client.audio.transcriptions.create(
            model=whisper_deployment,
            file=audio_file,
            response_format="json"
        )

    print("\n=== Transcription ===")
    print(transcription.text)

except subprocess.CalledProcessError as e:
    print(f"Error during audio extraction: {e}")
    print(f"FFmpeg stderr: {e.stderr.decode() if e.stderr else 'No error output'}")
except Exception as e:
    print(f"Error during transcription: {e}")
finally:
    # Clean up temporary files
    if os.path.exists(temp_video_path):
        os.unlink(temp_video_path)
    if os.path.exists(temp_audio_path):
        os.unlink(temp_audio_path)
    print("Temporary files cleaned up.")