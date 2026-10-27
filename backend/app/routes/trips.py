from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response

from ..deps import current_user
from ..schemas import RegenerateDayRequest, Trip, TripRequest, TripUpdate
from ..services.generator import generate_itinerary, regenerate_day
from ..store import get_store

router = APIRouter(prefix="/trips", tags=["trips"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(uid: str, trip_id: str) -> Trip:
    raw = get_store().get(uid, trip_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Trip not found")
    return Trip.model_validate(raw)


def _save(trip: Trip) -> Trip:
    trip.updated_at = _now()
    get_store().save(trip.model_dump(mode="json"))
    return trip


@router.get("", response_model=List[Trip])
def list_trips(uid: str = Depends(current_user)):
    return [Trip.model_validate(t) for t in get_store().list(uid)]


@router.post("", response_model=Trip, status_code=201)
def create_trip(req: TripRequest, uid: str = Depends(current_user)):
    now = _now()
    trip = Trip(
        id=str(uuid4()),
        user_id=uid,
        title=f"{req.destination.strip().title()} · {req.start_date:%d %b %Y}",
        request=req,
        itinerary=generate_itinerary(req),
        created_at=now,
        updated_at=now,
    )
    get_store().save(trip.model_dump(mode="json"))
    return trip


@router.get("/{trip_id}", response_model=Trip)
def get_trip(trip_id: str, uid: str = Depends(current_user)):
    return _load(uid, trip_id)


@router.put("/{trip_id}", response_model=Trip)
def update_trip(trip_id: str, body: TripUpdate, uid: str = Depends(current_user)):
    trip = _load(uid, trip_id)
    if body.title is not None:
        trip.title = body.title
    if body.itinerary is not None:
        if len(body.itinerary.days) != trip.request.num_days:
            raise HTTPException(status_code=422, detail="Itinerary day count must match the trip dates")
        generated_by = trip.itinerary.generated_by
        trip.itinerary = body.itinerary.recompute()
        trip.itinerary.generated_by = generated_by
    return _save(trip)


@router.delete("/{trip_id}", status_code=204)
def delete_trip(trip_id: str, uid: str = Depends(current_user)):
    if not get_store().delete(uid, trip_id):
        raise HTTPException(status_code=404, detail="Trip not found")
    return Response(status_code=204)


@router.post("/{trip_id}/regenerate", response_model=Trip)
def regenerate_trip(trip_id: str, uid: str = Depends(current_user)):
    trip = _load(uid, trip_id)
    trip.itinerary = generate_itinerary(trip.request)
    return _save(trip)


@router.post("/{trip_id}/days/{day}/regenerate", response_model=Trip)
def regenerate_trip_day(
    trip_id: str,
    day: int,
    body: Optional[RegenerateDayRequest] = None,
    uid: str = Depends(current_user),
):
    trip = _load(uid, trip_id)
    if not any(d.day == day for d in trip.itinerary.days):
        raise HTTPException(status_code=404, detail=f"Day {day} not found")
    trip.itinerary = regenerate_day(
        trip.request, trip.itinerary, day, body.instruction if body else ""
    )
    return _save(trip)
