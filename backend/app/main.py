from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config
from .routes import trips
from .store import get_store

app = FastAPI(title="Personalized Travel Itinerary Planner", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


@api.get("/health", tags=["meta"])
def health():
    return {
        "status": "ok",
        "ai_mode": "llm" if config.llm_enabled() else "builtin",
        "llm_model": config.LLM_MODEL if config.llm_enabled() else None,
        "storage": get_store().name,
    }


api.include_router(trips.router)
app.include_router(api)

# Serve the built React app from the same server (production / single-container deploys)
_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
