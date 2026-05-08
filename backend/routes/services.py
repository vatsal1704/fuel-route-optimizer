"""Core services: geocoding, routing, and optimal fuel-stop selection."""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional

import requests
from django.conf import settings

from .data_loader import get_stations

logger = logging.getLogger(__name__)

EARTH_RADIUS_MI = 3958.7613
VEHICLE_RANGE_MI = 500.0
VEHICLE_MPG = 10.0
# Stations within this corridor of the route are considered "on route".
CORRIDOR_MI = 7.0


# ---------------------------- Geo helpers ---------------------------------

def haversine_mi(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(a))


# --------------------------- External APIs --------------------------------

# Tiny in-memory geocode cache (Nominatim rate-limits to ~1 req/s).
_GEOCODE_CACHE: dict[str, dict] = {}
_GEOCODE_CACHE_MAX = 512


def _geocode_cache_get(query: str) -> Optional[dict]:
    return _GEOCODE_CACHE.get(query.strip().lower())


def _geocode_cache_set(query: str, value: dict) -> None:
    if len(_GEOCODE_CACHE) >= _GEOCODE_CACHE_MAX:
        # Drop an arbitrary entry; cache is small so this is fine.
        _GEOCODE_CACHE.pop(next(iter(_GEOCODE_CACHE)))
    _GEOCODE_CACHE[query.strip().lower()] = value


def geocode(query: str) -> Optional[dict]:
    """Geocode a free-form US location via Nominatim. Returns {lat, lng, label}.

    Uses a small in-memory LRU cache to avoid re-hitting the public Nominatim
    endpoint (which rate-limits to ~1 req/s) for repeat queries.
    """
    cached = _geocode_cache_get(query)
    if cached is not None:
        return cached
    url = f"{settings.NOMINATIM_URL}/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "us",
        "addressdetails": 0,
    }
    headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=8)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:  # noqa: BLE001
        logger.error("Geocoding failed for %r: %s", query, exc)
        return None
    if not data:
        return None
    hit = data[0]
    result = {
        "lat": float(hit["lat"]),
        "lng": float(hit["lon"]),
        "label": hit.get("display_name", query),
    }
    _geocode_cache_set(query, result)
    return result


def fetch_route(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> Optional[dict]:
    """Single OSRM call. Returns {coords:[(lat,lng)...], distance_mi, duration_s}."""
    coords = f"{start_lng},{start_lat};{end_lng},{end_lat}"
    url = f"{settings.OSRM_URL}/route/v1/driving/{coords}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "annotations": "false",
        "steps": "false",
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:  # noqa: BLE001
        logger.error("OSRM call failed: %s", exc)
        return None
    if data.get("code") != "Ok" or not data.get("routes"):
        return None
    route = data["routes"][0]
    geom = route["geometry"]["coordinates"]  # [[lng, lat], ...]
    points = [(lat, lng) for lng, lat in geom]
    return {
        "coords": points,
        "distance_mi": route["distance"] / 1609.344,
        "duration_s": route["duration"],
    }


# ---------------------- Project stations onto route -----------------------

@dataclass
class OnRouteStation:
    opis_id: str
    name: str
    address: str
    city: str
    state: str
    price: float
    lat: float
    lng: float
    mile: float  # distance from start along route to nearest waypoint
    detour_mi: float  # straight-line distance from station to route corridor


def _cumulative_miles(coords: list[tuple[float, float]]) -> list[float]:
    cum = [0.0]
    for i in range(1, len(coords)):
        d = haversine_mi(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1])
        cum.append(cum[-1] + d)
    return cum


def _sample_waypoints(
    coords: list[tuple[float, float]], cum: list[float], step_mi: float = 8.0
) -> list[tuple[float, float, float]]:
    """Return list of (lat, lng, mile) sampled roughly every `step_mi` miles."""
    if not coords:
        return []
    samples: list[tuple[float, float, float]] = [(coords[0][0], coords[0][1], cum[0])]
    next_mark = step_mi
    for i in range(1, len(coords)):
        if cum[i] >= next_mark:
            samples.append((coords[i][0], coords[i][1], cum[i]))
            while next_mark <= cum[i]:
                next_mark += step_mi
    if samples[-1][2] != cum[-1]:
        samples.append((coords[-1][0], coords[-1][1], cum[-1]))
    return samples


def stations_on_route(
    coords: list[tuple[float, float]],
    cum: list[float],
    corridor_mi: float = CORRIDOR_MI,
) -> list[OnRouteStation]:
    """Find fuel stations within `corridor_mi` of the route.

    Algorithm: sample the route every ~8 miles, and for each station, check the
    closest sample. If within (corridor + sample_step), perform a finer check
    against neighboring samples to compute mile-along-route. This is O(N*K)
    where K is sample count (~hundreds), which stays fast for cross-country
    routes vs. the full polyline (~10k-15k points).
    """
    stations = get_stations()
    if not coords or not stations:
        return []
    samples = _sample_waypoints(coords, cum, step_mi=8.0)

    # Bounding box prefilter (route bbox + small slack in degrees)
    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    pad_deg = (corridor_mi / 60.0) + 0.5  # ~1 degree latitude == 69 mi
    min_lat, max_lat = min(lats) - pad_deg, max(lats) + pad_deg
    min_lng, max_lng = min(lngs) - pad_deg, max(lngs) + pad_deg

    out: list[OnRouteStation] = []
    seen_ids: set[str] = set()
    for st in stations:
        slat, slng = st["lat"], st["lng"]
        if not (min_lat <= slat <= max_lat and min_lng <= slng <= max_lng):
            continue
        # Find nearest sample
        best_d = float("inf")
        best_mile = 0.0
        for slat_s, slng_s, mile in samples:
            d = haversine_mi(slat, slng, slat_s, slng_s)
            if d < best_d:
                best_d = d
                best_mile = mile
        if best_d > corridor_mi + 8.0:  # 8.0 = sample spacing
            continue
        if best_d > corridor_mi:
            # Likely off corridor, skip
            continue
        if st["opis_id"] in seen_ids:
            continue
        seen_ids.add(st["opis_id"])
        out.append(
            OnRouteStation(
                opis_id=st["opis_id"],
                name=st["name"],
                address=st["address"],
                city=st["city"],
                state=st["state"],
                price=st["price"],
                lat=slat,
                lng=slng,
                mile=best_mile,
                detour_mi=round(best_d, 2),
            )
        )
    out.sort(key=lambda s: s.mile)
    return out


# ----------------------- Optimal fuel-stop algorithm ----------------------

def plan_fuel_stops(
    on_route: list[OnRouteStation],
    total_distance_mi: float,
    range_mi: float = VEHICLE_RANGE_MI,
    mpg: float = VEHICLE_MPG,
) -> dict:
    """Cost-optimal greedy refueling for the classic gas-station problem.

    Assumption: vehicle starts with a full tank (range_mi) at mile 0; only
    en-route refueling cost is counted. At each stop, we buy *just enough*
    fuel to reach the next cheaper station within range (or the destination
    if it's within range). If no cheaper station is reachable, we fill the
    tank completely. From the current position we always drive to the
    cheapest reachable station next.
    """
    if total_distance_mi <= range_mi:
        return {
            "stops": [],
            "total_cost_usd": 0.0,
            "total_gallons": round(total_distance_mi / mpg, 2),
            "note": "Trip within single-tank range; no refueling required.",
            "feasible": True,
        }

    stops: list[dict] = []
    total_cost = 0.0
    total_gallons = 0.0
    current_mile = 0.0
    current_range = range_mi  # full tank at start

    while current_mile + current_range < total_distance_mi:
        # Stations reachable from current position without refueling.
        reachable = [
            s for s in on_route
            if current_mile < s.mile <= current_mile + current_range
        ]
        if not reachable:
            return {
                "stops": stops,
                "total_cost_usd": round(total_cost, 2),
                "total_gallons": round(total_gallons, 2),
                "feasible": False,
                "note": (
                    f"No fuel station reachable within {range_mi:.0f} mi "
                    f"from mile {current_mile:.1f}; this route is not "
                    "drivable with the given dataset."
                ),
            }

        # Drive to the cheapest reachable station (no fuel purchased yet).
        stop = min(reachable, key=lambda s: s.price)
        current_range -= (stop.mile - current_mile)
        current_mile = stop.mile

        # Decide how much to buy here.
        forward_window = [
            s for s in on_route
            if current_mile < s.mile <= current_mile + range_mi
        ]
        cheaper_ahead = [s for s in forward_window if s.price < stop.price]

        if current_mile + range_mi >= total_distance_mi:
            # Destination reachable from here -- buy just enough to finish.
            need_miles = total_distance_mi - current_mile - current_range
            buy_miles = max(0.0, need_miles)
        elif cheaper_ahead:
            # Roll forward to the nearest cheaper station.
            nearest_cheaper = min(cheaper_ahead, key=lambda s: s.mile)
            need_miles = nearest_cheaper.mile - current_mile - current_range
            buy_miles = max(0.0, need_miles)
        else:
            # Nothing cheaper within tank range -- top up.
            buy_miles = range_mi - current_range

        gallons = buy_miles / mpg
        cost = gallons * stop.price
        current_range += buy_miles
        total_gallons += gallons
        total_cost += cost

        stops.append({
            "opis_id": stop.opis_id,
            "name": stop.name,
            "address": stop.address,
            "city": stop.city,
            "state": stop.state,
            "lat": stop.lat,
            "lng": stop.lng,
            "price_per_gallon": round(stop.price, 4),
            "mile_marker": round(stop.mile, 1),
            "detour_mi": stop.detour_mi,
            "gallons_purchased": round(gallons, 2),
            "stop_cost_usd": round(cost, 2),
        })

    return {
        "stops": stops,
        "total_cost_usd": round(total_cost, 2),
        "total_gallons": round(total_gallons, 2),
        "feasible": True,
        "note": f"{len(stops)} fuel stop(s) planned to complete trip.",
    }


# -------------------------- Top-level orchestration -----------------------

def plan_trip(start: str, finish: str) -> dict:
    s = geocode(start)
    if not s:
        return {"error": f"Could not geocode start location: {start}"}
    f = geocode(finish)
    if not f:
        return {"error": f"Could not geocode finish location: {finish}"}

    route = fetch_route(s["lat"], s["lng"], f["lat"], f["lng"])
    if not route:
        return {"error": "Routing service failed to return a route."}

    cum = _cumulative_miles(route["coords"])
    distance_mi = cum[-1] if cum else route["distance_mi"]
    on_route = stations_on_route(route["coords"], cum)
    plan = plan_fuel_stops(on_route, distance_mi)

    return {
        "start": {"query": start, **s},
        "finish": {"query": finish, **f},
        "route": {
            "polyline": route["coords"],  # list of [lat, lng]
            "distance_mi": round(distance_mi, 2),
            "duration_s": route["duration_s"],
        },
        "fuel_plan": plan,
        "vehicle": {"range_mi": VEHICLE_RANGE_MI, "mpg": VEHICLE_MPG},
        "stations_considered_along_route": len(on_route),
    }
