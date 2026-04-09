"""
Nearby dermatology-related places.

- If GOOGLE_PLACES_API_KEY is set: Google Places Nearby Search + Place Details
  (ratings, review text, opening hours, formatted address). Map stays Leaflet on the client.
- Otherwise: OpenStreetMap via Overpass (no ratings/reviews).
"""
from __future__ import annotations

import asyncio
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

from ..config.settings import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

MIN_RESULTS_TARGET = 20
MAX_RETURN = 25
AROUND_METERS = 12000

NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
PAGE_DELAY_SEC = 2.1
MAX_NEARBY_PAGES = 3
DETAILS_FIELDS = "name,formatted_address,geometry,rating,user_ratings_total,opening_hours,reviews,business_status"
DETAILS_CONCURRENCY = 8

OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_KEYWORDS = (
    "dermatologist",
    "dermatology clinic",
    "skin clinic",
    "hospital dermatology",
    "skin specialist",
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


def _looks_dermatology(name: str, tags: Dict[str, Any]) -> bool:
    n = (name or "").lower()
    spec = str(tags.get("healthcare:speciality", "")).lower()
    spec2 = str(tags.get("speciality", "")).lower()
    desc = str(tags.get("description", "")).lower()
    combo = " ".join([n, spec, spec2, desc])
    keys = ("dermat", "skin", "cosmetic", "laser", "tricholog", "venereolog")
    return any(k in combo for k in keys)


# ── Google Places ───────────────────────────────────────────────────────────


def _nearby_result_to_stub(r: Dict[str, Any], origin_lat: float, origin_lng: float) -> Optional[Dict[str, Any]]:
    loc = (r.get("geometry") or {}).get("location") or {}
    plat, plng = loc.get("lat"), loc.get("lng")
    pid = r.get("place_id")
    if plat is None or plng is None or not pid:
        return None
    d = haversine_km(origin_lat, origin_lng, float(plat), float(plng))
    return {
        "place_id": pid,
        "lat": float(plat),
        "lng": float(plng),
        "distance_km": round(d, 2),
        "name_preview": r.get("name") or "",
    }


async def _fetch_google_nearby_stubs(
    client: httpx.AsyncClient, lat: float, lng: float, api_key: str
) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    next_token: Optional[str] = None

    for page in range(MAX_NEARBY_PAGES):
        if page == 0:
            params: Dict[str, Any] = {
                "location": f"{lat},{lng}",
                "radius": 10000,
                "keyword": "dermatologist skin clinic",
                "key": api_key,
            }
        else:
            if not next_token:
                break
            await asyncio.sleep(PAGE_DELAY_SEC)
            params = {"pagetoken": next_token, "key": api_key}

        resp = await client.get(NEARBY_URL, params=params, timeout=30.0)
        data = resp.json()
        status = data.get("status")
        logger.info(
            "[nearby-google] nearby page=%s status=%s n=%s",
            page,
            status,
            len(data.get("results") or []),
        )

        if status not in ("OK", "ZERO_RESULTS"):
            logger.warning("[nearby-google] nearby non-OK: %s %s", status, data.get("error_message"))
            break

        for r in data.get("results") or []:
            stub = _nearby_result_to_stub(r, lat, lng)
            if stub:
                collected.append(stub)

        next_token = data.get("next_page_token")
        if not next_token:
            break

    # Dedupe by place_id, sort by distance
    seen: Set[str] = set()
    uniq: List[Dict[str, Any]] = []
    for s in sorted(collected, key=lambda x: x["distance_km"]):
        pid = s["place_id"]
        if pid in seen:
            continue
        seen.add(pid)
        uniq.append(s)

    return uniq[:MIN_RESULTS_TARGET]


async def _fetch_place_details(
    client: httpx.AsyncClient,
    place_id: str,
    api_key: str,
    sem: asyncio.Semaphore,
) -> Optional[Dict[str, Any]]:
    async with sem:
        try:
            resp = await client.get(
                DETAILS_URL,
                params={
                    "place_id": place_id,
                    "fields": DETAILS_FIELDS,
                    "key": api_key,
                },
                timeout=25.0,
            )
            data = resp.json()
            if data.get("status") != "OK":
                logger.warning("[nearby-google] details status=%s place_id=%s", data.get("status"), place_id[:16])
                return None
            return data.get("result") or {}
        except Exception as e:
            logger.warning("[nearby-google] details error place_id=%s: %s", place_id[:16], e)
            return None


def _details_to_row(
    stub: Dict[str, Any],
    result: Dict[str, Any],
    origin_lat: float,
    origin_lng: float,
) -> Dict[str, Any]:
    loc = (result.get("geometry") or {}).get("location") or {}
    plat = loc.get("lat", stub["lat"])
    plng = loc.get("lng", stub["lng"])
    dist = haversine_km(origin_lat, origin_lng, float(plat), float(plng))
    dkm = round(dist, 2)
    oh = result.get("opening_hours") or {}
    reviews_out: List[Dict[str, Any]] = []
    for r in (result.get("reviews") or [])[:5]:
        reviews_out.append(
            {
                "author_name": r.get("author_name"),
                "rating": r.get("rating"),
                "text": r.get("text"),
                "relative_time_description": r.get("relative_time_description"),
            }
        )
    name = result.get("name") or stub.get("name_preview") or "Clinic"
    addr = result.get("formatted_address") or ""
    return {
        "name": name,
        "doctor_name": None,
        "rating": result.get("rating"),
        "user_ratings_total": result.get("user_ratings_total"),
        "address": addr,
        "distance_km": dkm,
        "distance": dkm,
        "lat": float(plat),
        "lng": float(plng),
        "place_id": stub["place_id"],
        "provider": "google",
        "open_now": oh.get("open_now"),
        "weekday_text": oh.get("weekday_text"),
        "reviews": reviews_out,
        "business_status": result.get("business_status"),
    }


async def _google_fetch_and_enrich(
    client: httpx.AsyncClient, lat: float, lng: float, api_key: str
) -> List[Dict[str, Any]]:
    stubs = await _fetch_google_nearby_stubs(client, lat, lng, api_key)
    if not stubs:
        return []

    sem = asyncio.Semaphore(DETAILS_CONCURRENCY)
    tasks = [_fetch_place_details(client, s["place_id"], api_key, sem) for s in stubs]
    details_list = await asyncio.gather(*tasks)

    rows: List[Dict[str, Any]] = []
    for stub, det in zip(stubs, details_list):
        if not det:
            # Minimal row from stub + nearby preview if details failed
            rows.append(
                {
                    "name": stub.get("name_preview") or "Place",
                    "doctor_name": None,
                    "rating": None,
                    "user_ratings_total": None,
                    "address": "",
                    "distance_km": stub["distance_km"],
                    "distance": stub["distance_km"],
                    "lat": stub["lat"],
                    "lng": stub["lng"],
                    "place_id": stub["place_id"],
                    "provider": "google",
                    "open_now": None,
                    "weekday_text": None,
                    "reviews": [],
                    "business_status": None,
                }
            )
            continue
        rows.append(_details_to_row(stub, det, lat, lng))

    rows.sort(key=lambda x: x["distance_km"])
    return rows[:MIN_RESULTS_TARGET]


# ── OpenStreetMap (Overpass) ────────────────────────────────────────────────


def _element_lat_lon(el: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    if el.get("lat") is not None and el.get("lon") is not None:
        return float(el["lat"]), float(el["lon"])
    c = el.get("center") or {}
    if c.get("lat") is not None and c.get("lon") is not None:
        return float(c["lat"]), float(c["lon"])
    return None


def _tags_addr(tags: Dict[str, Any]) -> str:
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
    if not _looks_dermatology(name, tags):
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
    opening = str(tags.get("opening_hours", "")).strip()
    doctor_name = (tags.get("contact:person") or tags.get("doctor") or tags.get("operator") or "").strip() or None
    return {
        "name": name,
        "doctor_name": doctor_name,
        "rating": None,
        "user_ratings_total": None,
        "address": addr,
        "distance_km": dkm,
        "distance": dkm,
        "lat": plat,
        "lng": plng,
        "place_id": pid,
        "provider": "openstreetmap",
        "open_now": None,
        "weekday_text": [f"Hours: {opening}"] if opening else None,
        "reviews": [],
        "business_status": None,
    }


def _overpass_query(lat: float, lng: float) -> str:
    r = AROUND_METERS
    return f"""[out:json][timeout:20];
(
  nwr["healthcare:speciality"~"dermatology|skin",i](around:{r},{lat},{lng});
  nwr["speciality"~"dermatology|skin",i](around:{r},{lat},{lng});
  nwr["name"~"Dermat|Skin|Derma|Cosmetic|Laser",i]["amenity"~"hospital|clinic|doctors"](around:{r},{lat},{lng});
  nwr["name"~"Dermat|Skin|Derma|Cosmetic|Laser",i]["healthcare"~"hospital|clinic|doctor"](around:{r},{lat},{lng});
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


async def _fetch_nominatim_rows(client: httpx.AsyncClient, lat: float, lng: float) -> List[Dict[str, Any]]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    # ~10-15km bounding box to keep results relevant
    margin = 0.12
    viewbox = f"{lng-margin},{lat+margin},{lng+margin},{lat-margin}"
    rows: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for kw in NOMINATIM_KEYWORDS:
        params = {
            "q": kw,
            "format": "json",
            "limit": "30",
            "addressdetails": "1",
            "viewbox": viewbox,
            "bounded": "0",
        }
        try:
            resp = await client.get(NOMINATIM_URL, params=params, headers=headers, timeout=25.0)
            resp.raise_for_status()
            items = resp.json() or []
            logger.info("[nearby-nominatim] keyword=%r results=%s", kw, len(items))
            for it in items:
                name = (it.get("display_name", "").split(",")[0] or "").strip()
                ilat, ilon = it.get("lat"), it.get("lon")
                if not name or ilat is None or ilon is None:
                    continue
                plat, plng = float(ilat), float(ilon)
                key = f"{name.lower()}|{round(plat,4)}|{round(plng,4)}"
                if key in seen:
                    continue
                seen.add(key)
                dist = round(haversine_km(lat, lng, plat, plng), 2)
                rows.append(
                    {
                        "name": name,
                        "doctor_name": None,
                        "rating": None,
                        "user_ratings_total": None,
                        "address": it.get("display_name") or name,
                        "distance_km": dist,
                        "distance": dist,
                        "lat": plat,
                        "lng": plng,
                        "place_id": f"nominatim_{it.get('osm_type','x')}_{it.get('osm_id', '')}",
                        "provider": "openstreetmap",
                        "open_now": None,
                        "weekday_text": None,
                        "reviews": [],
                        "business_status": None,
                    }
                )
        except Exception as e:
            logger.warning("[nearby-nominatim] keyword failed %r: %s", kw, e)

    rows.sort(key=lambda x: x["distance_km"])
    return rows[:MIN_RESULTS_TARGET]


async def _fetch_osm(lat: float, lng: float) -> Tuple[List[Dict[str, Any]], str]:
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
            logger.warning("[nearby-osm] zero results near lat=%s lng=%s; trying nominatim fallback", lat, lng)
            async with httpx.AsyncClient() as client:
                n_rows = await _fetch_nominatim_rows(client, lat, lng)
            if n_rows:
                logger.info("[nearby-nominatim] final_count=%s", len(n_rows))
                return n_rows, "openstreetmap"
            return [], "error_zero_results"

        logger.info("[nearby-osm] final_count=%s", min(len(rows), MIN_RESULTS_TARGET))
        return rows[:MIN_RESULTS_TARGET], "openstreetmap"

    except Exception as e:
        logger.exception("[nearby-osm] API failure: %s", e)
        # Resilient fallback when Overpass is down/throttled.
        try:
            async with httpx.AsyncClient() as client:
                n_rows = await _fetch_nominatim_rows(client, lat, lng)
            if n_rows:
                logger.info("[nearby-nominatim] fallback_count=%s", len(n_rows))
                return n_rows, "openstreetmap"
        except Exception as ne:
            logger.warning("[nearby-nominatim] fallback failed: %s", ne)
        return [], "error_api"


async def fetch_nearby_dermatologists(
    lat: float,
    lng: float,
    *,
    allow_mock_fallback: bool = False,
    require_rich_details: bool = False,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Returns (results, source).

    source: openstreetmap | error_zero_results | error_api
    """
    _ = allow_mock_fallback
    _ = require_rich_details
    return await _fetch_osm(lat, lng)
