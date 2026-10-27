"""Built-in rule-based itinerary engine.

Used when no LLM key is configured (or when the LLM call fails), so the app always works offline.
Costs are allocated from the user's total budget so the plan never silently exceeds it.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional, Set, Tuple

from ..schemas import Activity, DayPlan, Itinerary, TripRequest

# (title, description, cost weight, duration minutes)
Item = Tuple[str, str, float, int]

GENERIC: Dict[str, List[Item]] = {
    "sightseeing": [
        ("Highlights walk of {dest}", "Orientation walk through the best-known landmarks and viewpoints.", 0.8, 150),
        ("Old town and landmarks in {dest}", "Wander the historic core, stopping at key squares and monuments.", 0.6, 120),
        ("Panoramic viewpoint over {dest}", "Head to a hilltop or rooftop lookout for wide views of the city.", 0.4, 90),
        ("City museum or heritage centre", "A compact introduction to the story of {dest}.", 0.7, 120),
        ("Local sightseeing tour", "A guided or hop-on style tour that links the major sights efficiently.", 1.0, 180),
    ],
    "culture": [
        ("Local history museum", "Exhibits on the people, trade and traditions of {dest}.", 0.7, 120),
        ("Traditional performance or workshop", "Catch a live cultural show or try a hands-on craft class.", 1.1, 120),
        ("Heritage walk through the historic quarter", "Architecture, temples/churches and stories behind them.", 0.6, 120),
        ("Art gallery and craft studio visit", "Meet local artists and see contemporary work from {dest}.", 0.6, 90),
    ],
    "adventure": [
        ("Guided outdoor activity near {dest}", "A half-day of active fun with a local operator.", 1.5, 240),
        ("Cycling tour", "Ride scenic routes and lesser-known corners of {dest}.", 1.0, 180),
        ("Day hike to a scenic trail", "Moderate hike with great views; carry water and a snack.", 0.5, 240),
        ("Water sports or zip-line session", "Pick the thrill level that suits your group.", 1.6, 150),
    ],
    "nature": [
        ("Park or botanical garden stroll", "Slow, shaded walk away from the crowds.", 0.3, 90),
        ("Lakeside or riverside walk", "Find a calm waterfront spot to slow down and take in the scenery.", 0.2, 90),
        ("Nature reserve half-day trip", "Wildlife and landscapes within easy reach of {dest}.", 1.0, 240),
        ("Scenic day trip outside {dest}", "A short drive to countryside views and a village lunch.", 1.4, 300),
    ],
    "shopping": [
        ("Local market and craft shopping", "Browse stalls for textiles, crafts and gifts; bargain politely.", 1.0, 120),
        ("Souvenir hunt in the main bazaar", "Pick up keepsakes and regional specialties.", 0.8, 90),
        ("Artisan boutique district", "Independent shops, designers and concept stores.", 1.0, 120),
    ],
    "nightlife": [
        ("Live music venue", "Local bands or DJs; check the line-up for tonight.", 1.0, 120),
        ("Rooftop bar with city views", "Sundowners with a skyline backdrop.", 1.2, 120),
        ("Night market stroll", "Street snacks, lights and people-watching after dark.", 0.5, 90),
    ],
    "relaxation": [
        ("Spa or wellness session", "Massage, steam or yoga to reset.", 1.3, 120),
        ("Slow morning at a quiet café", "No agenda: coffee, journaling, people-watching.", 0.3, 90),
        ("Poolside or beach downtime", "Recharge before the next stretch of exploring.", 0.2, 150),
    ],
}

LUNCH: List[Item] = [
    ("Local specialty lunch", "Try the signature regional dish at a well-reviewed local restaurant.", 0.6, 70),
    ("Street food crawl", "Several small bites from busy, trusted stalls.", 0.4, 75),
    ("Market-side lunch", "Eat where the locals eat, near the central market.", 0.4, 60),
    ("Café brunch stop", "Relaxed lunch with good coffee and a light menu.", 0.5, 60),
    ("Regional set-menu tasting", "A fixed menu that showcases local flavours.", 0.8, 80),
]

DINNER: List[Item] = [
    ("Dinner at a popular local spot", "Book ahead if you can; ask for the chef's recommendations.", 0.9, 90),
    ("Family-run eatery recommended by locals", "Home-style cooking and generous portions.", 0.7, 80),
    ("Sunset dinner with a view", "Pick a terrace or waterfront table at golden hour.", 1.2, 100),
    ("Regional cuisine tasting dinner", "A multi-course sampler of {dest}'s food traditions.", 1.3, 110),
]

CURATED: Dict[str, Dict[str, List[Item]]] = {
    "jaipur": {
        "sightseeing": [
            ("Amber Fort and Jaigarh viewpoint", "Hilltop fort complex with courtyards, mirror work and valley views.", 1.2, 210),
            ("City Palace and Hawa Mahal photo stop", "Royal residence museum followed by the iconic latticed facade.", 1.1, 180),
            ("Nahargarh Fort viewpoint", "Ramparts overlooking the Pink City; go late afternoon if you can for the best light.", 0.6, 120),
        ],
        "culture": [
            ("Jantar Mantar observatory", "Giant stone astronomical instruments built in the 1700s.", 0.5, 90),
            ("Block-printing workshop", "Hand-stamp your own fabric with a local artisan.", 1.0, 120),
        ],
        "shopping": [("Johari Bazaar and Bapu Bazaar", "Jewellery, textiles, juttis and lac bangles.", 1.0, 150)],
        "lunch": [("Dal baati churma lunch", "Rajasthani comfort food at a traditional restaurant.", 0.6, 70)],
        "dinner": [("Laal maas or veg thali dinner", "Classic Rajasthani flavours in a heritage setting.", 1.0, 90)],
    },
    "goa": {
        "sightseeing": [
            ("Fort Aguada and lighthouse", "17th-century Portuguese fort above the Arabian Sea.", 0.4, 90),
            ("Old Goa churches", "Basilica of Bom Jesus and Se Cathedral in the UNESCO-listed area.", 0.5, 150),
        ],
        "nature": [
            ("Dudhsagar Falls day trip", "Four-tier waterfall in the Western Ghats; allow a full day.", 1.6, 420),
            ("Palolem beach morning", "Quiet crescent beach with calm water.", 0.4, 180),
        ],
        "relaxation": [("Beach shack afternoon", "Sun loungers, sea breeze and fresh seafood.", 0.6, 180)],
        "nightlife": [("Beachside music night", "Live sets and sundowners along the northern coast.", 1.2, 150)],
        "dinner": [("Goan seafood dinner", "Fish curry rice, prawn balchão and sol kadhi.", 1.1, 100)],
    },
    "paris": {
        "sightseeing": [
            ("Eiffel Tower and Trocadéro", "Classic views from the esplanade; book summit tickets ahead.", 1.4, 150),
            ("Montmartre and Sacré-Cœur", "Cobbled lanes, artists' square and a hilltop basilica.", 0.5, 150),
            ("Seine river cruise", "An hour on the water passing the major monuments.", 0.9, 90),
        ],
        "culture": [
            ("Louvre Museum highlights", "Focus on a handful of masterpieces; pre-book a time slot.", 1.2, 180),
            ("Musée d'Orsay", "Impressionist collection inside a former railway station.", 1.0, 150),
        ],
        "nature": [("Luxembourg Gardens", "Tree-lined paths, fountains and the classic green chairs.", 0.2, 90)],
        "lunch": [("Bistro lunch in Le Marais", "Prix-fixe menu in a lively historic district.", 0.7, 80)],
        "dinner": [("Classic French dinner in Saint-Germain", "Traditional brasserie dishes and a good wine list.", 1.4, 110)],
    },
}

EXPLORE_CATEGORIES = ["sightseeing", "culture", "adventure", "nature", "shopping", "nightlife", "relaxation"]
DEFAULT_EXPLORE = ["sightseeing", "culture", "nature"]

# (time, kind)
SLOTS = {
    "relaxed": [("10:30", "explore"), ("13:30", "lunch"), ("16:30", "explore"), ("19:30", "dinner")],
    "balanced": [("09:00", "explore"), ("12:30", "lunch"), ("14:30", "explore"), ("17:00", "explore"), ("19:30", "dinner")],
    "packed": [
        ("08:00", "explore"), ("10:30", "explore"), ("13:00", "lunch"),
        ("15:00", "explore"), ("17:30", "explore"), ("20:00", "dinner"),
    ],
}

STAY_SHARE = {"budget": 0.28, "mid": 0.38, "premium": 0.50}
STAY_NAME = {
    "budget": "Well-rated hostel or guesthouse in {dest}",
    "mid": "Comfortable 3-4 star hotel in {dest}",
    "premium": "Boutique or luxury hotel in {dest}",
}
TRANSPORT_SHARE = 0.10
BUFFER = 0.10  # share of the budget deliberately left unallocated


def _norm_interests(interests: List[str]) -> List[str]:
    out = []
    for i in interests:
        k = i.strip().lower()
        if k in EXPLORE_CATEGORIES and k not in out:
            out.append(k)
    return out


def _pool(dest_key: str, category: str) -> Tuple[List[Item], List[Item]]:
    curated = CURATED.get(dest_key, {}).get(category, [])
    if category == "lunch":
        generic = LUNCH
    elif category == "dinner":
        generic = DINNER
    else:
        generic = GENERIC.get(category, [])
    return list(curated), list(generic)


def _pick(dest_key: str, category: str, used: Set[str], rng: random.Random) -> Item:
    curated, generic = _pool(dest_key, category)
    rng.shuffle(curated)
    rng.shuffle(generic)
    for item in curated + generic:
        if item[0] not in used:
            return item
    # everything used (long trip): allow repeats
    return (curated + generic)[rng.randrange(len(curated + generic))]


def _transport_tip(req: TripRequest, day: int) -> str:
    if day == 1:
        return f"Arrange an airport/station transfer into {req.destination}; pre-book or use a ride-hailing app."
    if req.travel_style == "packed":
        return "Cluster stops by neighbourhood and use ride-hailing or a day cab to save time."
    return "Use local transit or short ride-hailing hops; walk where the sights are close together."


def build_day(
    req: TripRequest,
    day: int,
    rng: random.Random,
    used: Set[str],
    nights: int,
    stay_total: float,
    transport_day: float,
    activity_day: float,
) -> DayPlan:
    dest_key = req.destination.strip().lower()
    n = req.num_days
    slots = list(SLOTS[req.travel_style])
    if n > 1 and day == 1:
        slots = slots[1:]  # arrival day starts later
    if n > 1 and day == n and len(slots) > 3:
        slots = slots[:-1]  # departure day finishes earlier
    explore_cats = _norm_interests(req.interests) or DEFAULT_EXPLORE
    # rotate the starting interest each day so every interest gets airtime
    offset = (day - 1) % len(explore_cats)
    cats_cycle = explore_cats[offset:] + explore_cats[:offset]

    picked: List[Tuple[str, str, Item, str]] = []  # time, kind, item, category
    ci = 0
    for time, kind in slots:
        if kind == "explore":
            cat = cats_cycle[ci % len(cats_cycle)]
            ci += 1
        else:
            cat = kind
        item = _pick(dest_key, cat, used, rng)
        used.add(item[0])
        picked.append((time, kind, item, "food" if kind in ("lunch", "dinner") else cat))

    weight_sum = sum(p[2][2] for p in picked) or 1.0
    unit = activity_day / weight_sum
    activities = []
    for time, _kind, item, cat in picked:
        activities.append(
            Activity(
                time=time,
                title=item[0].format(dest=req.destination),
                category=cat,
                description=item[1].format(dest=req.destination),
                cost=round(item[2] * unit),
                duration_min=item[3],
            )
        )
    primary = [a.category for a in activities if a.category != "food"]
    theme_cat = primary[0].title() if primary else "Local"
    if n > 1 and day == 1:
        theme = f"Arrival and {theme_cat.lower()} warm-up"
    elif n > 1 and day == n:
        theme = f"{theme_cat} and a relaxed farewell"
    else:
        theme = f"{theme_cat} and local flavours"

    has_night = day <= nights
    return DayPlan(
        day=day,
        date=req.day_date(day),
        theme=theme,
        activities=activities,
        stay_name=STAY_NAME[req.accommodation_tier].format(dest=req.destination) if has_night else "",
        stay_cost=round(stay_total / nights) if has_night and nights else 0,
        transport_tip=_transport_tip(req, day),
        transport_cost=round(transport_day),
    )


def _budget_split(req: TripRequest) -> Tuple[int, float, float, float]:
    n = req.num_days
    usable = req.budget * (1 - BUFFER)
    nights = n - 1 if n > 1 else 0
    stay_share = STAY_SHARE[req.accommodation_tier] if nights else 0.0
    stay_total = usable * stay_share
    transport_day = usable * TRANSPORT_SHARE / n
    activity_day = usable * (1 - stay_share - TRANSPORT_SHARE) / n
    return nights, stay_total, transport_day, activity_day


def _tips(req: TripRequest) -> List[str]:
    tips = [
        "All costs are estimates for your whole group; actual prices vary by season and venue.",
        f"About {int(BUFFER * 100)}% of your budget is intentionally unallocated as a contingency buffer.",
        "Check opening hours and book popular attractions in advance.",
    ]
    if req.travelers > 4:
        tips.append("Large groups: reserve restaurants ahead and consider splitting into two cabs.")
    if req.notes:
        tips.append(f"Your note was: \"{req.notes}\". Edit activities to fit it exactly.")
    return tips


def generate_builtin(req: TripRequest, seed: Optional[int] = None) -> Itinerary:
    rng = random.Random(seed if seed is not None else random.randrange(10**9))
    nights, stay_total, transport_day, activity_day = _budget_split(req)
    used: Set[str] = set()
    days = [
        build_day(req, d, rng, used, nights, stay_total, transport_day, activity_day)
        for d in range(1, req.num_days + 1)
    ]
    itin = Itinerary(days=days, tips=_tips(req), generated_by="builtin").recompute()
    itin.summary = make_summary(req, itin)
    return itin


def regenerate_day_builtin(req: TripRequest, itin: Itinerary, day: int, seed: Optional[int] = None) -> Itinerary:
    rng = random.Random(seed if seed is not None else random.randrange(10**9))
    nights, stay_total, transport_day, activity_day = _budget_split(req)
    used = {a.title for d in itin.days if d.day != day for a in d.activities}
    new_day = build_day(req, day, rng, used, nights, stay_total, transport_day, activity_day)
    itin.days = [new_day if d.day == day else d for d in itin.days]
    itin.recompute()
    itin.summary = make_summary(req, itin)
    return itin


def make_summary(req: TripRequest, itin: Itinerary) -> str:
    chosen = [i.strip().lower() for i in req.interests if i.strip()]
    interests = ", ".join(dict.fromkeys(chosen)) or "a mix of sightseeing, culture and nature"
    who = "1 traveler" if req.travelers == 1 else f"{req.travelers} travelers"
    return (
        f"{req.num_days}-day {req.travel_style} trip to {req.destination} for {who}, "
        f"focused on {interests}. Estimated total {req.currency} {itin.total_cost:,.0f} "
        f"of your {req.currency} {req.budget:,.0f} budget."
    )
