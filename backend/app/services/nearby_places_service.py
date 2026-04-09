"""
Nearby doctors, clinics, and hospitals from OpenStreetMap via Overpass API.
No Google API — pairs with Leaflet + OSM tiles on the frontend.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

from ..utils.logger import get_logger

logger = get_logger(__name__)

MIN_RESULTS_TARGET = 20
MAX_RETURN = 25
AROUND_METERS = 12000

OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
)

USER_AGENT = "DermaCareAI/2.0 (nearby health POIs; student project)"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_earth = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    a = max(0.0, min(1.0, a))
    return r_earth * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _element_lat_lon(el: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    if el.get("lat") is not None and el.get("lon") is not None:
        return float(el["lat"]), float(el["lon"])
    c = el.get("center") or {}
    if c.get("lat") is not None and c.get("lon") is not None:
        return float(c["lat"]), float(c["lon"])
    return None


def _tags_addr(tags: Dict[str, str]) -> str:
    parts = []
    h = tags.get("addr:housenumber", "")
    st = tags.get("addr:street", "")
    if st:
        parts.append(f"{h + ' ' if h else ''}{st}".strip())
    elif h:
        parts.append(h)
    city = tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:village") or tags.get("addr:suburb") or ""
    if city:
        parts.append(city)
    return ", ".join(p for p in parts if p)


def _element_to_row(
    el: Dict[str, Any],
    origin_lat: float,
    origin_lng: float,
) -> Optional[Dict[str, Any]]:
    tags = el.get("tags") or {}
    name = (tags.get("name") or tags.get("operator") or "").strip()
    if not name:
        return None
    ll = _element_lat_lon(el)
    if not ll:
        return None
    plat, plng = ll
    dist = haversine_km(origin_lat, origin_lng, plat, plng)
    dkm = round(dist, 2)
    addr = _tags_addr(tags) or name
    oid = el.get("id")
    typ = el.get("type", "x")
    pid = f"osm_{typ}_{oid}" if oid is not None else f"osm_{typ}_{plat:.5f}_{plng:.5f}"
    return {
        "name": name,
        "rating": None,
        "user_ratings_total": None,
        "address": addr,
        "distance_km": dkm,
        "distance": dkm,
        "lat": plat,
        "lng": plng,
        "place_id": pid,
        "provider": "openstreetmap",
    }


def _overpass_query(lat: float, lng: float) -> str:
    # Focused query to keep public Overpass instances responsive (avoid huge unions).
    r = AROUND_METERS
    return f"""[out:json][timeout:20];
(
  nwr["amenity"="hospital"](around:{r},{lat},{lng});
  nwr["amenity"="clinic"](around:{r},{lat},{lng});
  nwr["amenity"="doctors"](around:{r},{lat},{lng});
  nwr["healthcare"="hospital"](around:{r},{lat},{lng});
  nwr["healthcare"="clinic"](around:{r},{lat},{lng});
  nwr["healthcare"="doctor"](around:{r},{lat},{lng});
  nwr["healthcare:speciality"~"dermatology|skin",i](around:{r},{lat},{lng});
);
out center tags 60;
"""


async def _fetch_overpass(client: httpx.AsyncClient, lat: float, lng: float) -> List[Dict[str, Any]]:
    q = _overpass_query(lat, lng)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    last_err: Optional[Exception] = None
    for url in OVERPASS_ENDPOINTS:
        try:
            resp = await client.post(url, data={"data": q}, headers=headers, timeout=40.0)
            resp.raise_for_status()
            data = resp.json()
            els = data.get("elements") or []
            logger.info("[nearby-osm] endpoint=%s elements=%s", url, len(els))
            return els
        except Exception as e:
            last_err = e
            logger.warning("[nearby-osm] endpoint failed %s: %s", url, e)
    if last_err:
        raise last_err
    return []


async def fetch_nearby_dermatologists(
    lat: float,
    lng: float,
    *,
    allow_mock_fallback: bool = False,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Returns (results, source).

    source:
      - openstreetmap: OSM Overpass results (possibly < 20 in sparse areas)
      - error_zero_results: nothing matched
      - error_api: network / Overpass failure
    """
    _ = allow_mock_fallback  # reserved; no mock data in production path

    try:
        async with httpx.AsyncClient() as client:
            elements = await _fetch_overpass(client, lat, lng)

        seen: Set[str] = set()
        rows: List[Dict[str, Any]] = []
        for el in elements:
            row = _element_to_row(el, lat, lng)
            if not row:
                continue
            key = f"{row['name'].lower()}|{round(row['lat'], 4)}|{round(row['lng'], 4)}"
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)

        rows.sort(key=lambda x: x["distance_km"])

        if not rows:
            logger.warning("[nearby-osm] zero results near lat=%s lng=%s", lat, lng)
            return [], "error_zero_results"

        logger.info("[nearby-osm] final_count=%s", min(len(rows), MIN_RESULTS_TARGET))
        return rows[:MIN_RESULTS_TARGET], "openstreetmap"

    except Exception as e:
        logger.exception("[nearby-osm] API failure: %s", e)
        return [], "error_api"
