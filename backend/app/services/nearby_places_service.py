"""
Google Places Nearby Search with pagination, radius expansion, Haversine sort, and mock fallback.
"""
from __future__ import annotations

import asyncio
import math
import random
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

from ..config.settings import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
MIN_RESULTS_TARGET = 20
PAGE_DELAY_SEC = 2.1  # Google requires ~2s before next_page_token is valid
MAX_PAGES_PER_QUERY = 3
RADII_METERS = (3000, 5000, 10000, 15000, 25000)
SEARCH_KEYWORDS = (
    "dermatologist",
    "skin clinic",
    "dermatology",
    "skin doctor",
    "cosmetic dermatology",
)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_earth = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    a = max(0.0, min(1.0, a))
    return r_earth * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _place_to_row(
    result: Dict[str, Any],
    origin_lat: float,
    origin_lng: float,
) -> Optional[Dict[str, Any]]:
    loc = (result.get("geometry") or {}).get("location") or {}
    plat = loc.get("lat")
    plng = loc.get("lng")
    if plat is None or plng is None:
        return None
    dist = haversine_km(origin_lat, origin_lng, float(plat), float(plng))
    addr = result.get("vicinity") or result.get("formatted_address") or ""
    rating = result.get("rating")
    dkm = round(dist, 2)
    return {
        "name": result.get("name") or "Unknown clinic",
        "rating": float(rating) if rating is not None else None,
        "user_ratings_total": result.get("user_ratings_total"),
        "address": addr,
        "distance_km": dkm,
        "distance": dkm,
        "lat": float(plat),
        "lng": float(plng),
        "place_id": result.get("place_id"),
    }


async def _fetch_nearby_query_pages(
    client: httpx.AsyncClient,
    lat: float,
    lng: float,
    radius_m: int,
    keyword: str,
    api_key: str,
) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    next_token: Optional[str] = None

    for page in range(MAX_PAGES_PER_QUERY):
        if page == 0:
            params = {
                "location": f"{lat},{lng}",
                "radius": str(radius_m),
                "type": "doctor",
                "keyword": keyword,
                "key": api_key,
            }
        else:
            if not next_token:
                break
            await asyncio.sleep(PAGE_DELAY_SEC)
            params = {"pagetoken": next_token, "key": api_key}

        resp = await client.get(PLACES_URL, params=params, timeout=25.0)
        raw_len = len(resp.text)
        data = resp.json()
        status = data.get("status")
        logger.info(
            "[nearby-places] page=%s keyword=%r radius=%sm status=%s results_in_page=%s response_chars=%s",
            page,
            keyword,
            radius_m,
            status,
            len(data.get("results") or []),
            raw_len,
        )

        if status not in ("OK", "ZERO_RESULTS"):
            logger.warning("[nearby-places] Non-OK status: %s error_message=%s", status, data.get("error_message"))

        for r in data.get("results") or []:
            collected.append(r)

        next_token = data.get("next_page_token")
        if not next_token:
            break

    return collected


def _mock_results(lat: float, lng: float, count: int = 20) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    labels = (
        "DermaCare Partner — Skin & Laser",
        "City Dermatology Clinic",
        "Advanced Skin Center",
        "Cosmetic & Medical Dermatology",
        "Pediatric Dermatology Associates",
    )
    for i in range(count):
        dlat = random.uniform(-0.04, 0.04)
        dlng = random.uniform(-0.04, 0.04)
        plat, plng = lat + dlat, lng + dlng
        dist = haversine_km(lat, lng, plat, plng)
        dkm = round(dist, 2)
        out.append(
            {
                "name": f"{labels[i % len(labels)]} #{i + 1}",
                "rating": round(3.8 + random.random() * 1.1, 1),
                "user_ratings_total": random.randint(12, 420),
                "address": "Demo data — set GOOGLE_PLACES_API_KEY for live Google Places results",
                "distance_km": dkm,
                "distance": dkm,
                "lat": plat,
                "lng": plng,
                "place_id": f"mock_{i}",
            }
        )
    out.sort(key=lambda x: x["distance_km"])
    return out


async def fetch_nearby_dermatologists(
    lat: float,
    lng: float,
    *,
    allow_mock_fallback: bool = False,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Returns (results, source).

    source values:
      - google_places: real results from Google (possibly < 20 in sparse areas)
      - mock / google_places+padded_mock: only if allow_mock_fallback=True
      - error_no_key, error_zero_results, error_api: real-only mode (empty list)
    """
    api_key = (settings.GOOGLE_PLACES_API_KEY or "").strip()
    if not api_key:
        logger.warning("[nearby-places] GOOGLE_PLACES_API_KEY missing")
        if allow_mock_fallback:
            return _mock_results(lat, lng, MIN_RESULTS_TARGET), "mock"
        return [], "error_no_key"

    seen_ids: Set[str] = set()
    merged_raw: List[Dict[str, Any]] = []

    try:
        async with httpx.AsyncClient() as client:
            for radius_m in RADII_METERS:
                for kw in SEARCH_KEYWORDS:
                    batch = await _fetch_nearby_query_pages(client, lat, lng, radius_m, kw, api_key)
                    for r in batch:
                        pid = r.get("place_id") or f"{r.get('name')}:{r.get('geometry')}"
                        if pid in seen_ids:
                            continue
                        seen_ids.add(pid)
                        merged_raw.append(r)
                    logger.info(
                        "[nearby-places] cumulative_unique=%s after radius=%sm keyword=%r",
                        len(merged_raw),
                        radius_m,
                        kw,
                    )
                    if len(merged_raw) >= MIN_RESULTS_TARGET:
                        break
                if len(merged_raw) >= MIN_RESULTS_TARGET:
                    break

        rows: List[Dict[str, Any]] = []
        for r in merged_raw:
            row = _place_to_row(r, lat, lng)
            if row:
                rows.append(row)

        rows.sort(key=lambda x: x["distance_km"])

        if not rows:
            logger.warning("[nearby-places] Zero parsed rows from Google")
            if allow_mock_fallback:
                return _mock_results(lat, lng, MIN_RESULTS_TARGET), "mock"
            return [], "error_zero_results"

        if len(rows) < 15:
            logger.warning("[nearby-places] Only %s Google results (sparse area or restrictive queries)", len(rows))

        if len(rows) < MIN_RESULTS_TARGET and allow_mock_fallback:
            mocks = _mock_results(lat, lng, MIN_RESULTS_TARGET - len(rows) + 5)
            existing = {(round(x["lat"], 5), round(x["lng"], 5)) for x in rows}
            for m in mocks:
                key = (round(m["lat"], 5), round(m["lng"], 5))
                if key in existing:
                    continue
                existing.add(key)
                rows.append(m)
                if len(rows) >= MIN_RESULTS_TARGET:
                    break
            rows.sort(key=lambda x: x["distance_km"])
            logger.info("[nearby-places] final_count=%s (google_places+padded_mock)", len(rows))
            return rows[:MIN_RESULTS_TARGET], "google_places+padded_mock"

        logger.info("[nearby-places] final_count=%s (google_places)", len(rows))
        return rows[:MIN_RESULTS_TARGET], "google_places"

    except Exception as e:
        logger.exception("[nearby-places] API failure: %s", e)
        if allow_mock_fallback:
            return _mock_results(lat, lng, MIN_RESULTS_TARGET), "mock"
        return [], "error_api"
