import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

# Any OpenAI-compatible chat-completions endpoint works (Groq, Together, OpenRouter, Ollama, vLLM...)
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.groq.com/openai/v1/chat/completions").strip()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant").strip()
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))

LOCAL_DATA_FILE = Path(os.getenv("LOCAL_DATA_FILE", str(BASE_DIR / "data" / "trips.json")))

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]


def supabase_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def llm_enabled() -> bool:
    return bool(LLM_API_KEY)
