import subprocess
from azure.storage.blob import BlobServiceClient, BlobClient
import os
from openai import AzureOpenAI
import io
from dotenv import load_dotenv
import tempfile
import wave

load_dotenv()

# Azure Blob setup
conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
container_name = "labweek3773blob"
blob_name = "match_video_1.mp4"
blob_service_client = BlobServiceClient.from_connection_string(conn_str)

# ONE TIME UPLOAD - Create container if it doesn't exist
try:
    blob_service_client.create_container(container_name)
    print(f"Created container: {container_name}")
except Exception as e:
    print(f"Container already exists: {e}")

blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

# Path to your local audio file
audio_file = "audio/match_audio.mp3"

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

# Paths
audio_dir = "audio"
audio_file_path = os.path.join(audio_dir, "match_audio.mp3")
chunks_dir = os.path.join(audio_dir, "audio_chunks")

# Create chunks folder if not exists
os.makedirs(chunks_dir, exist_ok=True)

# Check audio size
audio_size = os.path.getsize(audio_file_path)
print(f"Audio file size: {audio_size / (1024 * 1024):.2f} MB")

# Chunk File size as input
# Split only if >25MB
if audio_size > 25 * 1024 * 1024:
    print("File exceeds 25MB, splitting into chunks...")

    # Calculate number of chunks needed
    chunk_size_bytes = 25 * 1024 * 1024
    num_chunks = int(audio_size / chunk_size_bytes) + 1
    chunk_duration_seconds = None

    # Get audio duration using ffprobe
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries',
            'format=duration', '-of',
            'default=noprint_wrappers=1:nokey=1', audio_file_path
        ], capture_output=True, text=True, check=True)

        total_duration = float(result.stdout.strip())
        chunk_duration_seconds = int(total_duration / num_chunks)
        print(
            f"Total duration: {total_duration:.2f}s, splitting into {num_chunks} chunks of ~{chunk_duration_seconds}s each")

    except Exception as e:
        print(f"Could not determine duration: {e}")
        # Fallback: split by estimated time (25MB ≈ 10 minutes for typical MP3)
        chunk_duration_seconds = 600  # 10 minutes

    # Split audio into chunks using ffmpeg
    for i in range(num_chunks):
        start_time = i * chunk_duration_seconds
        chunk_filename = os.path.join(chunks_dir, f"chunk_{i + 1}.mp3")

        try:
            subprocess.run([
                'ffmpeg', '-i', audio_file_path,
                '-ss', str(start_time),
                '-t', str(chunk_duration_seconds),
                '-acodec', 'copy',
                chunk_filename,
                '-y'
            ], check=True, capture_output=True)
            print(f"Saved {chunk_filename}")
        except subprocess.CalledProcessError as e:
            print(f"Error creating chunk {i + 1}: {e}")
            if e.stderr:
                print(f"FFmpeg error: {e.stderr.decode()}")

    # Transcribe all chunks
    print("\n=== Transcribing chunks ===")
    full_transcription = []

    for i in range(num_chunks):
        chunk_filename = os.path.join(chunks_dir, f"chunk_{i + 1}.mp3")
        if os.path.exists(chunk_filename):
            try:
                with open(chunk_filename, 'rb') as chunk_file:
                    print(f"Transcribing chunk {i + 1}/{num_chunks}...")
                    transcription = client.audio.transcriptions.create(
                        model=whisper_deployment,
                        file=chunk_file,
                        language="de",
                        response_format="json"
                    )
                    full_transcription.append(transcription.text)
                    print(f"Chunk {i + 1} transcribed successfully")
            except Exception as e:
                print(f"Error transcribing chunk {i + 1}: {e}")

    print("\n=== Full Transcription ===")
    print(" ".join(full_transcription))

else:
    print("Audio size is within limit, no splitting needed.")

    try:
        # Read the audio file and send to Whisper
        with open(audio_file_path, 'rb') as audio:
            print("Sending to Whisper for transcription...")
            transcription = client.audio.transcriptions.create(
                model=whisper_deployment,
                file=audio,
                language="de",
                response_format="json"
            )

        print("\n=== Transcription ===")
        print(transcription.text)

    except Exception as e:
        print(f"Error during transcription: {e}")