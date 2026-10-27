from __future__ import annotations

from datetime import date, timedelta
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

TravelStyle = Literal["relaxed", "balanced", "packed"]
StayTier = Literal["budget", "mid", "premium"]

MAX_DAYS = 14


class TripRequest(BaseModel):
    destination: str = Field(min_length=2, max_length=80)
    start_date: date
    end_date: date
    budget: float = Field(gt=0, description="Total budget for the whole group")
    currency: str = Field("INR", min_length=3, max_length=3)
    travelers: int = Field(1, ge=1, le=20)
    travel_style: TravelStyle = "balanced"
    accommodation_tier: StayTier = "mid"
    interests: List[str] = Field(default_factory=list, max_length=10)
    notes: str = Field("", max_length=500)

    @model_validator(mode="after")
    def _check_dates(self) -> "TripRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.num_days > MAX_DAYS:
            raise ValueError(f"Trips are limited to {MAX_DAYS} days")
        return self

    @property
    def num_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def day_date(self, day: int) -> date:
        return self.start_date + timedelta(days=day - 1)


class Activity(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    time: str = "09:00"
    title: str = Field(min_length=1, max_length=160)
    category: str = "sightseeing"
    description: str = ""
    cost: float = Field(0, ge=0)
    duration_min: int = Field(60, ge=0, le=1440)


class DayPlan(BaseModel):
    day: int
    date: date
    theme: str = ""
    activities: List[Activity] = Field(default_factory=list)
    stay_name: str = ""
    stay_cost: float = Field(0, ge=0)
    transport_tip: str = ""
    transport_cost: float = Field(0, ge=0)
    day_cost: float = 0


class Itinerary(BaseModel):
    summary: str = ""
    days: List[DayPlan] = Field(default_factory=list)
    tips: List[str] = Field(default_factory=list)
    total_cost: float = 0
    generated_by: str = "builtin"

    def recompute(self) -> "Itinerary":
        total = 0.0
        for d in self.days:
            d.day_cost = round(
                sum(a.cost for a in d.activities) + d.stay_cost + d.transport_cost, 2
            )
            total += d.day_cost
        self.total_cost = round(total, 2)
        return self


class Trip(BaseModel):
    id: str
    user_id: str
    title: str
    request: TripRequest
    itinerary: Itinerary
    created_at: str
    updated_at: str


class TripUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=120)
    itinerary: Optional[Itinerary] = None


class RegenerateDayRequest(BaseModel):
    instruction: str = Field("", max_length=300)
