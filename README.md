# Labweek_Fall_2025_MatchAgent

# MatchEventExtractor

A Python-based pipeline to extract, store, and explain key football match events from subtitle files using GPT-4o and Weaviate.


## Project Overview

This project enables automatic extraction and analysis of football match events from subtitle (`.stl`) files. It uses:

- **Azure OpenAI GPT-4o** to extract structured events from raw match commentary.
- **Weaviate vector database** to store and query event data.
- **Live explanations** for each event type (e.g. foul, goal, offside) for new football audiences.

---

## Features

- Extract football events with GPT-4o
- Store structured data in Weaviate
- Query by event types (e.g. goals, fouls, red cards)
- Auto-generate rule-based explanations of event types
-  Save all outputs to user-defined folders

---

## Setup Instructions

- Clone the repository

git clone https://github.com/your-username/MatchEventExtractor.git
cd MatchEventExtractor

- Install the dependencies: 
pip install -r requirements.txt

- Azure Setup: 
Deploy a gpt 4o model and get its endpoint and API keys


- Weaviate Setup
Create a Weaviate Cloud Cluster
Go to Weaviate Cloud Console and Create a new cluster and note down your Cluster URL and API Key.

- Create a .env file with your keys:
azure_endpoint_gpt4o=YOUR_AZURE_OPENAI_ENDPOINT
azure_endpoint_gpt4o_key=YOUR_AZURE_OPENAI_KEY
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
WCS_CLUSTER_URL=YOUR_WEAVIATE_CLUSTER_URL
WCS_API_KEY=YOUR_WEAVIATE_API_KEY
