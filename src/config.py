"""
config — Project paths, environment variables, and shared data.

Loads the .env file, the song dataset, and the LLM prompt template once
at import time so every other module can simply ``from src.config import ...``.
"""

import json
import os
from pathlib import Path

import dotenv

# ── Paths ─────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent

dotenv.load_dotenv(PROJECT_ROOT / ".env")

# ── Ollama settings ───────────────────────────────────────────────────────────

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
API_URL = f"{OLLAMA_BASE_URL}/api/generate"
MODEL = os.getenv("OLLAMA_MODEL", "phi3")

# ── Dataset & prompt ──────────────────────────────────────────────────────────

with open(PROJECT_ROOT / "data" / "dataset.json") as _f:
    SONGS: list[dict] = json.load(_f)

with open(PROJECT_ROOT / "data" / "prompt.txt") as _f:
    BASE_PROMPT: str = _f.read()

# ── Optional live search fallback ─────────────────────────────────────────────

ENABLE_LIVE_YOUTUBE_SEARCH = os.getenv("ENABLE_LIVE_YOUTUBE_SEARCH", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
LIVE_SEARCH_LIMIT = int(os.getenv("LIVE_SEARCH_LIMIT", "8"))
