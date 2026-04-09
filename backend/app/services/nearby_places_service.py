"""
Nearby dermatology-related places.

Primary provider: Foursquare Places API (when FOURSQUARE_API_KEY is set).
Fallback providers: OpenStreetMap Overpass + Nominatim.
"""
from __future__ import annotations

import asyncio
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

from ..config.settings import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

MIN_RESULTS_TARGET = 20
MAX_RETURN = 25
AROUND_METERS = 12000
PRIMARY_RADIUS_KM = 5.0
FALLBACK_RADIUS_KM = 10.0
MIN_ACCEPTABLE_COUNT = 3

FOURSQUARE_SEARCH_URL = "https://api.foursquare.com/v3/places/search"
FOURSQUARE_DETAILS_URL = "https://api.foursquare.com/v3/places/{fsq_id}"
FOURSQUARE_TIPS_URL = "https://api.foursquare.com/v3/places/{fsq_id}/tips"
FSQ_RADIUS_M_PRIMARY = 5000
FSQ_RADIUS_M_FALLBACK = 10000
FSQ_LIMIT_PER_QUERY = 20
FSQ_DETAILS_CONCURRENCY = 6
FSQ_SEARCH_TERMS = (
    "dermatologist",
    "dermatology clinic",
    "skin clinic",
    "skin specialist",
)

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


def _limit_to_nearby_radius(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Keep places within 5km by default.
    If results are too few, expand to 10km.
    """
    within_5 = [r for r in rows if float(r.get("distance_km", 9999)) <= PRIMARY_RADIUS_KM]
    if len(within_5) >= MIN_ACCEPTABLE_COUNT:
        return within_5[:MIN_RESULTS_TARGET]
    within_10 = [r for r in rows if float(r.get("distance_km", 9999)) <= FALLBACK_RADIUS_KM]
    return within_10[:MIN_RESULTS_TARGET]


def _looks_dermatology(name: str, tags: Dict[str, Any]) -> bool:
    n = (name or "").lower()
    spec = str(tags.get("healthcare:speciality", "")).lower()
    spec2 = str(tags.get("speciality", "")).lower()
    desc = str(tags.get("description", "")).lower()
    combo = " ".join([n, spec, spec2, desc])
    keys = ("dermat", "skin", "cosmetic", "laser", "tricholog", "venereolog")
    return any(k in combo for k in keys)


# ── Foursquare Places ────────────────────────────────────────────────────────


def _fsq_extract_lat_lng(item: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    geo = item.get("geocodes") or {}
    main = geo.get("main") or {}
    lat = main.get("latitude")
    lng = main.get("longitude")
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)


def _fsq_weekday_text(hours_obj: Dict[str, Any]) -> Optional[List[str]]:
    if not isinstance(hours_obj, dict):
        return None
    display = hours_obj.get("display")
    if isinstance(display, list):
        out = [str(x) for x in display if str(x).strip()]
        return out or None
    if isinstance(display, str) and display.strip():
        return [display.strip()]
    return None


async def _fetch_fsq_tips(client: httpx.AsyncClient, fsq_id: str) -> List[Dict[str, Any]]:
    try:
        resp = await client.get(FOURSQUARE_TIPS_URL.format(fsq_id=fsq_id), params={"limit": 3}, timeout=20.0)
        if resp.status_code >= 400:
            return []
        data = resp.json()
        tips = data if isinstance(data, list) else data.get("results") or []
        out: List[Dict[str, Any]] = []
        for t in tips[:3]:
            out.append(
                {
                    "author_name": (t.get("user") or {}).get("first_name") or "Foursquare user",
                    "rating": None,
                    "text": t.get("text"),
                    "relative_time_description": t.get("created_at"),
                }
            )
        return out
    except Exception:
        return []


async def _fetch_fsq_details(
    client: httpx.AsyncClient,
    fsq_id: str,
    sem: asyncio.Semaphore,
) -> Optional[Dict[str, Any]]:
    async with sem:
        try:
            resp = await client.get(FOURSQUARE_DETAILS_URL.format(fsq_id=fsq_id), timeout=20.0)
            if resp.status_code >= 400:
                return None
            return resp.json()
        except Exception:
            return None


def _fsq_result_to_row(
    src: Dict[str, Any],
    details: Optional[Dict[str, Any]],
    tips: List[Dict[str, Any]],
    origin_lat: float,
    origin_lng: float,
) -> Optional[Dict[str, Any]]:
    base = details or src
    ll = _fsq_extract_lat_lng(base) or _fsq_extract_lat_lng(src)
    if not ll:
        return None
    plat, plng = ll
    dist = round(haversine_km(origin_lat, origin_lng, plat, plng), 2)
    location = base.get("location") or {}
    formatted = location.get("formatted_address") or src.get("location", {}).get("formatted_address") or ""
    fsq_id = base.get("fsq_id") or src.get("fsq_id")
    rating = base.get("rating")
    stats = base.get("stats") or {}
    review_count = stats.get("total_ratings") or stats.get("total_tips") or None
    hours = base.get("hours") or {}
    doctor_name = (base.get("related_places") or {}).get("parent", {}).get("name")
    return {
        "name": base.get("name") or src.get("name") or "Clinic",
        "doctor_name": doctor_name,
        "rating": float(rating) if isinstance(rating, (int, float)) else None,
        "user_ratings_total": review_count,
        "address": formatted,
        "distance_km": dist,
        "distance": dist,
        "lat": plat,
        "lng": plng,
        "place_id": fsq_id,
        "provider": "foursquare",
        "open_now": hours.get("open_now"),
        "weekday_text": _fsq_weekday_text(hours),
        "reviews": tips,
        "business_status": "OPERATIONAL" if base.get("closed_bucket") in (None, "VeryLikelyOpen") else "CLOSED_TEMPORARILY",
        "place_url": f"https://foursquare.com/v/{fsq_id}" if fsq_id else None,
        "website": base.get("website"),
    }


async def _fetch_foursquare_rows(lat: float, lng: float, api_key: str) -> List[Dict[str, Any]]:
    headers = {"Authorization": api_key, "Accept": "application/json"}
    collected: Dict[str, Dict[str, Any]] = {}

    async with httpx.AsyncClient(headers=headers) as client:
        for radius in (FSQ_RADIUS_M_PRIMARY, FSQ_RADIUS_M_FALLBACK):
            for term in FSQ_SEARCH_TERMS:
                try:
                    resp = await client.get(
                        FOURSQUARE_SEARCH_URL,
                        params={
                            "query": term,
                            "ll": f"{lat},{lng}",
                            "radius": radius,
                            "limit": FSQ_LIMIT_PER_QUERY,
                        },
                        timeout=20.0,
                    )
                    if resp.status_code >= 400:
                        continue
                    data = resp.json()
                    results = data.get("results") or []
                    for it in results:
                        fsq_id = it.get("fsq_id")
                        if not fsq_id:
                            continue
                        name = it.get("name") or ""
                        cats = " ".join((c.get("name") or "") for c in (it.get("categories") or []))
                        if "dermat" not in (name + " " + cats).lower() and "skin" not in (name + " " + cats).lower():
                            continue
                        if fsq_id not in collected:
                            collected[fsq_id] = it
                except Exception:
                    continue
            if len(collected) >= MIN_RESULTS_TARGET:
                break

        if not collected:
            return []

        sem = asyncio.Semaphore(FSQ_DETAILS_CONCURRENCY)
        ids = list(collected.keys())[:MAX_RETURN]
        detail_tasks = [_fetch_fsq_details(client, fsq_id, sem) for fsq_id in ids]
        details = await asyncio.gather(*detail_tasks)
        tips_tasks = [_fetch_fsq_tips(client, fsq_id) for fsq_id in ids]
        tips_arr = await asyncio.gather(*tips_tasks)

    rows: List[Dict[str, Any]] = []
    for fsq_id, det, tips in zip(ids, details, tips_arr):
        src = collected.get(fsq_id, {})
        row = _fsq_result_to_row(src, det, tips, lat, lng)
        if row:
            rows.append(row)
    rows.sort(key=lambda x: x["distance_km"])
    return _limit_to_nearby_radius(rows)


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
    return _limit_to_nearby_radius(rows)


# ── OpenStreetMap (Overpass) ────────────────────────────────────────────────


def _element_lat_lon(el: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    if el.get("lat") is not None and el.get("lon") is not None:
        return float(el["lat"]), float(el["lon"])
    c = el.get("center") or {}
    if c.get("lat") is not None and c.get("lon") is not None:
        return float(c["lat"]), float(c["lon"])
    return None


def _beautify_osm_opening_hours(raw: str) -> List[str]:
    """
    Turn OSM opening_hours strings into readable lines (e.g. Mo-Fr 09:00-17:00).
    See https://wiki.openstreetmap.org/wiki/Key:opening_hours
    """
    if not raw or not str(raw).strip():
        return []
    s = str(raw).strip()
    low = s.lower()
    if low in ("24/7", "24/7 open", "open 24/7", "always", "always open"):
        return ["Open 24 hours"]
    parts = [p.strip() for p in s.split(";") if p.strip()]
    lines: List[str] = []
    range_pairs = (
        ("Mo-Fr", "Mon–Fri"),
        ("Mo-Sa", "Mon–Sat"),
        ("Mo-Th", "Mon–Thu"),
        ("Tu-Fr", "Tue–Fri"),
        ("Tu-Sa", "Tue–Sat"),
        ("We-Fr", "Wed–Fri"),
        ("Th-Fr", "Thu–Fri"),
        ("Sa-Su", "Sat–Sun"),
        ("Mo-Su", "Mon–Sun"),
    )
    single_days = (
        ("Mo", "Mon"),
        ("Tu", "Tue"),
        ("We", "Wed"),
        ("Th", "Thu"),
        ("Fr", "Fri"),
        ("Sa", "Sat"),
        ("Su", "Sun"),
    )
    for p in parts:
        line = p
        for a, b in range_pairs:
            line = line.replace(a, b)
        for ab, full in single_days:
            line = re.sub(rf"(?<![A-Za-z]){ab}(?![a-z])", full, line)
        line = line.replace(" PH", " · PH").replace(" PH closed", " · closed (public holidays)")
        lines.append(line)
    return lines


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
    hours_lines = _beautify_osm_opening_hours(opening) if opening else None
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
        "weekday_text": hours_lines,
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
    return _limit_to_nearby_radius(rows)


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
        rows = _limit_to_nearby_radius(rows)

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

    source: foursquare | openstreetmap | error_zero_results | error_api
    """
    _ = allow_mock_fallback
    _ = require_rich_details

    fsq_key = (settings.FOURSQUARE_API_KEY or "").strip()
    if fsq_key:
        try:
            fsq_rows = await _fetch_foursquare_rows(lat, lng, fsq_key)
            if fsq_rows:
                logger.info("[nearby] returning %s foursquare rows", len(fsq_rows))
                return fsq_rows, "foursquare"
            logger.warning("[nearby] foursquare returned no rows; using OSM fallback")
        except Exception as e:
            logger.warning("[nearby] foursquare failed (%s); using OSM fallback", e)

    return await _fetch_osm(lat, lng)
