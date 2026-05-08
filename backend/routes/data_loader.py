"""Load the fuel-price CSV and resolve coordinates for each truck-stop.

Coordinates are derived offline using `geonamescache` (city + state -> lat/lng),
so we don't burn external geocoder quota. Results are cached in MongoDB after
first build, then loaded into a process-local list for fast lookups.
"""
from __future__ import annotations

import csv
import logging
import threading
from typing import Optional

import geonamescache
from django.conf import settings
from pymongo import MongoClient

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_STATIONS: list[dict] = []
_LOADED = False

# Map full state names -> 2-letter codes (geonamescache uses codes).
_STATE_NAME_TO_CODE: Optional[dict[str, str]] = None


def _build_city_index() -> dict[tuple[str, str], tuple[float, float]]:
    """Index (city_lower, state_code) -> (lat, lng) using geonamescache.

    For ambiguity (multiple cities of same name in a state), keep the most
    populous one – truck stops are usually in larger cities/along highways.
    """
    gc = geonamescache.GeonamesCache(min_city_population=500)
    cities = gc.get_cities()
    index: dict[tuple[str, str], tuple[float, float, int]] = {}
    for c in cities.values():
        if c.get("countrycode") != "US":
            continue
        state_code = c.get("admin1code", "")
        name_key = (c["name"].lower(), state_code)
        pop = c.get("population", 0) or 0
        prev = index.get(name_key)
        if prev is None or pop > prev[2]:
            index[name_key] = (c["latitude"], c["longitude"], pop)
    return {k: (v[0], v[1]) for k, v in index.items()}


def _aggregate_station_records(csv_path: str) -> list[dict]:
    """Read CSV and aggregate by truckstop id, taking the latest retail price."""
    by_id: dict[str, dict] = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                stop_id = (row.get("OPIS Truckstop ID") or "").strip()
                price = float((row.get("Retail Price") or "0").strip())
            except ValueError:
                continue
            if not stop_id:
                continue
            record = {
                "opis_id": stop_id,
                "name": (row.get("Truckstop Name") or "").strip(),
                "address": (row.get("Address") or "").strip(),
                "city": (row.get("City") or "").strip(),
                "state": (row.get("State") or "").strip().upper(),
                "price": price,
            }
            # Prefer entries with non-empty name; otherwise keep last.
            existing = by_id.get(stop_id)
            if existing is None or (not existing["name"] and record["name"]):
                by_id[stop_id] = record
    return list(by_id.values())


def _resolve_coords(stations: list[dict]) -> list[dict]:
    city_idx = _build_city_index()
    enriched: list[dict] = []
    misses = 0
    for s in stations:
        key = (s["city"].lower(), s["state"])
        coords = city_idx.get(key)
        if not coords:
            misses += 1
            continue
        s = dict(s)
        s["lat"] = coords[0]
        s["lng"] = coords[1]
        enriched.append(s)
    logger.info(
        "Geocoded fuel stations: %d resolved, %d skipped (city not in offline DB)",
        len(enriched),
        misses,
    )
    return enriched


def _mongo_client() -> MongoClient:
    return MongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=2000)


def _load_from_mongo() -> Optional[list[dict]]:
    try:
        client = _mongo_client()
        coll = client[settings.DB_NAME]["fuel_stations"]
        docs = list(coll.find({}, {"_id": 0}))
        client.close()
        if docs:
            return docs
    except Exception as exc:  # noqa: BLE001
        logger.warning("Mongo unavailable, will rebuild from CSV: %s", exc)
    return None


def _save_to_mongo(stations: list[dict]) -> None:
    try:
        client = _mongo_client()
        coll = client[settings.DB_NAME]["fuel_stations"]
        coll.delete_many({})
        if stations:
            coll.insert_many([dict(s) for s in stations])
        client.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to cache stations to Mongo: %s", exc)


def ensure_loaded() -> list[dict]:
    """Idempotent: returns the in-memory list of stations with coords."""
    global _LOADED, _STATIONS
    if _LOADED:
        return _STATIONS
    with _LOCK:
        if _LOADED:
            return _STATIONS
        cached = _load_from_mongo()
        if cached:
            _STATIONS = cached
        else:
            raw = _aggregate_station_records(settings.FUEL_CSV_PATH)
            _STATIONS = _resolve_coords(raw)
            _save_to_mongo(_STATIONS)
        _LOADED = True
        logger.info("Fuel stations loaded into memory: %d", len(_STATIONS))
    return _STATIONS


def get_stations() -> list[dict]:
    return ensure_loaded()
