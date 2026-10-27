"""Facade: try the LLM first, fall back to the built-in engine."""
from __future__ import annotations

from ..schemas import Itinerary, TripRequest
from . import llm, planner


def generate_itinerary(req: TripRequest) -> Itinerary:
    return llm.generate_itinerary_llm(req) or planner.generate_builtin(req)


def regenerate_day(req: TripRequest, itin: Itinerary, day: int, instruction: str = "") -> Itinerary:
    updated = llm.regenerate_day_llm(req, itin.model_copy(deep=True), day, instruction)
    return updated or planner.regenerate_day_builtin(req, itin, day)
