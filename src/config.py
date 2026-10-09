import os
from pathlib import Path

from dotenv import load_dotenv


# Load environment variables from .env
load_dotenv()

# Project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
UPDATES_DATA_DIR = BASE_DIR / "data" / "updates"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

# Qdrant local storage
QDRANT_DATA_DIR = BASE_DIR / "qdrant_data"

# Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Create required directories
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
UPDATES_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

if not GROQ_API_KEY:
    print("Warning: GROQ_API_KEY is not configured.")