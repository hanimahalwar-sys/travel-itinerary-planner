"""LLM-backed itinerary generation (OpenAI-compatible chat API, e.g. Llama-3 on Groq).

Every public function returns None on any failure so callers can fall back to the built-in engine.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from .. import config
from ..schemas import Activity, DayPlan, Itinerary, TripRequest
from . import planner

log = logging.getLogger("planner.llm")

SYSTEM_PROMPT = (
    "You are an expert travel planner. You reply with a single valid JSON object and nothing else. "
    "Costs are TOTAL for the whole travel group, in the requested currency, as plain numbers. "
    "Keep the sum of all costs at or below 90% of the stated budget. Times use 24h HH:MM. "
    "category must be one of: sightseeing, culture, food, adventure, nature, shopping, nightlife, relaxation. "
    "Only suggest real, well-known places for the destination; never invent addresses or phone numbers."
)

DAY_SCHEMA = (
    '{"theme": str, "stay_name": str, "stay_cost": number, "transport_tip": str, "transport_cost": number, '
    '"activities": [{"time": "HH:MM", "title": str, "category": str, "description": str, '
    '"cost": number, "duration_min": int}]}'
)


def _chat_json(user_prompt: str) -> Optional[Dict[str, Any]]:
    if not config.llm_enabled():
        return None
    try:
        resp = httpx.post(
            config.LLM_API_URL,
            headers={"Authorization": f"Bearer {config.LLM_API_KEY}"},
            json={
                "model": config.LLM_MODEL,
                "temperature": 0.7,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=config.LLM_TIMEOUT,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:  # network, auth, bad JSON... all handled by falling back
        log.warning("LLM call failed: %s", exc)
        return None


def _request_brief(req: TripRequest) -> str:
    return (
        f"Destination: {req.destination}\n"
        f"Dates: {req.start_date} to {req.end_date} ({req.num_days} days)\n"
        f"Travelers: {req.travelers}\n"
        f"Total group budget: {req.budget:.0f} {req.currency}\n"
        f"Pace: {req.travel_style}\n"
        f"Accommodation tier: {req.accommodation_tier}\n"
        f"Interests: {', '.join(req.interests) or 'general sightseeing'}\n"
        f"Notes: {req.notes or 'none'}"
    )


def _to_day(raw: Dict[str, Any], req: TripRequest, day: int) -> DayPlan:
    acts: List[Activity] = []
    for a in raw.get("activities", [])[:8]:
        acts.append(
            Activity(
                time=str(a.get("time", "09:00"))[:5],
                title=str(a["title"])[:160],
                category=str(a.get("category", "sightseeing")).lower(),
                description=str(a.get("description", "")),
                cost=max(0.0, float(a.get("cost", 0) or 0)),
                duration_min=int(a.get("duration_min", 60) or 60),
            )
        )
    if not acts:
        raise ValueError("no activities")
    acts.sort(key=lambda x: x.time)
    return DayPlan(
        day=day,
        date=req.day_date(day),
        theme=str(raw.get("theme", "")),
        activities=acts,
        stay_name=str(raw.get("stay_name", "")),
        stay_cost=max(0.0, float(raw.get("stay_cost", 0) or 0)),
        transport_tip=str(raw.get("transport_tip", "")),
        transport_cost=max(0.0, float(raw.get("transport_cost", 0) or 0)),
    )


def generate_itinerary_llm(req: TripRequest) -> Optional[Itinerary]:
    prompt = (
        f"{_request_brief(req)}\n\n"
        "Create a day-by-day itinerary. Return JSON: "
        '{"summary": str, "tips": [str], "days": [' + DAY_SCHEMA + "]} "
        f"with exactly {req.num_days} entries in days, in order. "
        "Include breakfast/lunch/dinner suggestions as category food, plus nearby attractions grouped "
        "by area to minimise travel time. Give a stay for every night except the last day."
    )
    data = _chat_json(prompt)
    if not data:
        return None
    try:
        raw_days = data["days"]
        if len(raw_days) != req.num_days:
            raise ValueError("wrong number of days")
        days = [_to_day(rd, req, i + 1) for i, rd in enumerate(raw_days)]
        itin = Itinerary(
            summary=str(data.get("summary", "")),
            days=days,
            tips=[str(t) for t in data.get("tips", [])][:8],
            generated_by="llm",
        ).recompute()
        if itin.total_cost > req.budget * 1.15:
            raise ValueError("LLM plan exceeds budget")
        if not itin.summary:
            itin.summary = planner.make_summary(req, itin)
        return itin
    except Exception as exc:
        log.warning("LLM itinerary rejected: %s", exc)
        return None


def regenerate_day_llm(req: TripRequest, itin: Itinerary, day: int, instruction: str) -> Optional[Itinerary]:
    others = [a.title for d in itin.days if d.day != day for a in d.activities]
    current = next((d for d in itin.days if d.day == day), None)
    if current is None:
        return None
    prompt = (
        f"{_request_brief(req)}\n\n"
        f"Re-plan ONLY day {day} ({req.day_date(day)}). Do not repeat these activities from other days: "
        f"{json.dumps(others)}.\n"
        f"The current plan for this day totals {current.day_cost:.0f} {req.currency}; keep a similar cost.\n"
        f"Extra instruction from the traveler: {instruction or 'none, just offer a fresh alternative'}.\n"
        f"Return JSON matching: {DAY_SCHEMA}"
    )
    data = _chat_json(prompt)
    if not data:
        return None
    try:
        new_day = _to_day(data, req, day)
        itin.days = [new_day if d.day == day else d for d in itin.days]
        itin.generated_by = "llm"
        itin.recompute()
        itin.summary = planner.make_summary(req, itin)
        return itin
    except Exception as exc:
        log.warning("LLM day rejected: %s", exc)
        return None
