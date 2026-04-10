"""
Nearby dermatology-related places.

Primary provider: Foursquare Places API (when FOURSQUARE_API_KEY is set).
Fallback providers: OpenStreetMap Overpass + Nominatim.
"""
from __future__ import annotations

import asyncio
import math
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

from ..config.settings import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

MIN_RESULTS_TARGET = 40
MAX_RETURN = 40
AROUND_METERS = 32000
# Hospitals: slightly smaller radius keeps Overpass responses fast; list still sorted by distance.
HOSPITAL_AROUND_METERS = 28000
# Single cutoff: closest-first up to MIN_RESULTS_TARGET within this radius (km).
EXTENDED_RADIUS_KM = 50.0
# Merge Nominatim keywords when Overpass list is still short of MIN_RESULTS_TARGET.
MERGE_NOMINATIM_IF_FEWER_THAN = 40

FOURSQUARE_SEARCH_URL = "https://api.foursquare.com/v3/places/search"
FOURSQUARE_DETAILS_URL = "https://api.foursquare.com/v3/places/{fsq_id}"
FOURSQUARE_TIPS_URL = "https://api.foursquare.com/v3/places/{fsq_id}/tips"
FSQ_RADIUS_M_PRIMARY = 5000
FSQ_RADIUS_M_FALLBACK = 10000
FSQ_LIMIT_PER_QUERY = 25
FSQ_DETAILS_CONCURRENCY = 6
FSQ_SEARCH_TERMS = (
    "dermatologist",
    "dermatology clinic",
    "skin clinic",
    "skin specialist",
)

# Try two mirrors only — a third retry often pushes total wall time past browser limits.
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_KEYWORDS = (
    "dermatologist",
    "dermatology clinic",
    "skin clinic",
    "hospital dermatology",
    "skin specialist",
    "skin doctor",
    "cosmetic clinic",
    "laser clinic",
)
# Bounded local search (1 req/s policy: staggered in _fetch_nominatim_hospitals_bounded).
NOMINATIM_HOSPITAL_KEYWORDS = ("hospital", "clinic", "medical centre")
USER_AGENT = "DermaCareAI/2.0 (nearby health POIs; student project)"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_earth = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    a = max(0.0, min(1.0, a))
    return r_earth * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _nominatim_primary_name(display_name: Any) -> str:
    """First segment before comma; string-safe (no brittle indexing on non-strings)."""
    if display_name is None:
        return ""
    text = display_name if isinstance(display_name, str) else str(display_name)
    text = text.strip()
    if not text:
        return ""
    head, _sep, _rest = text.partition(",")
    return head.strip()


def _limit_to_nearby_radius(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Closest-first, up to MIN_RESULTS_TARGET, within EXTENDED_RADIUS_KM.
    (Older logic stopped at 5 km whenever ≥3 hits hid farther clinics.)
    """
    rows_sorted = sorted(rows, key=lambda x: float(x.get("distance_km", 9999)))
    within = [
        r for r in rows_sorted if float(r.get("distance_km", 9999)) <= EXTENDED_RADIUS_KM
    ]
    return within[:MIN_RESULTS_TARGET]


def _row_dedupe_key(r: Dict[str, Any]) -> str:
    pid = r.get("place_id")
    if pid:
        return f"id:{pid}"
    try:
        la, lo = round(float(r["lat"]), 4), round(float(r["lng"]), 4)
    except (KeyError, TypeError, ValueError):
        la, lo = 0.0, 0.0
    nm = str(r.get("name") or "").strip().lower()[:48]
    return f"{la}|{lo}|{nm}"


def _looks_dermatology(name: str, tags: Dict[str, Any]) -> bool:
    n = (name or "").lower()
    spec = str(tags.get("healthcare:speciality", "")).lower()
    spec2 = str(tags.get("speciality", "")).lower()
    desc = str(tags.get("description", "")).lower()
    combo = " ".join([n, spec, spec2, desc])
    keys = (
        "dermat",
        "skin",
        "cosmetic",
        "laser",
        "tricholog",
        "venereolog",
        "aesthetic",
        "cosmetolog",
        "medispa",
        "mesotherapy",
    )
    return any(k in combo for k in keys)


# ── Live open / close status (uses server local time; good enough for demo) ──


def _format_ampm(h: int, m: int) -> str:
    h = h % 24
    ampm = "AM" if h < 12 else "PM"
    hh = h % 12
    if hh == 0:
        hh = 12
    return f"{hh}:{m:02d} {ampm}"


def _parse_fsq_hhmm(s: Any) -> Optional[Tuple[int, int]]:
    if s is None:
        return None
    t = str(s).strip()
    if not t.isdigit():
        return None
    if len(t) == 3:
        t = "0" + t
    if len(t) != 4:
        return None
    h, m = int(t[:2]), int(t[2:])
    if h > 24 or m > 59:
        return None
    return h, m


def _fsq_day_label(fsq_d: int) -> str:
    return ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[fsq_d - 1] if 1 <= fsq_d <= 7 else ""


def _compute_hours_live_foursquare(hours: Dict[str, Any]) -> Dict[str, Any]:
    """state: open | closed | unknown; closes_at / opens_next are human-readable labels."""
    out: Dict[str, Any] = {"state": "unknown", "closes_at": None, "opens_next": None}
    regular = hours.get("regular")
    now = datetime.now()
    now_mins = now.hour * 60 + now.minute
    fsq_today = now.weekday() + 1  # 1=Mon … 7=Sun (matches Foursquare)

    if isinstance(regular, list) and regular:
        intervals: List[Tuple[int, int]] = []
        for b in regular:
            if not isinstance(b, dict):
                continue
            try:
                d = int(b.get("day"))
            except (TypeError, ValueError):
                continue
            if d != fsq_today:
                continue
            o = _parse_fsq_hhmm(b.get("open"))
            c = _parse_fsq_hhmm(b.get("close"))
            if not o or not c:
                continue
            om, cm = o[0] * 60 + o[1], c[0] * 60 + c[1]
            if cm <= om:
                continue
            intervals.append((om, cm))
        intervals.sort(key=lambda x: x[0])

        for om, cm in intervals:
            if om <= now_mins < cm:
                out["state"] = "open"
                out["closes_at"] = f"Closes {_format_ampm(cm // 60, cm % 60)}"
                return out

        if intervals:
            if now_mins < intervals[0][0]:
                out["state"] = "closed"
                first_om = intervals[0][0]
                out["opens_next"] = f"Opens {_format_ampm(first_om // 60, first_om % 60)}"
                return out
            for om, _cm in intervals:
                if now_mins < om:
                    out["state"] = "closed"
                    out["opens_next"] = f"Opens {_format_ampm(om // 60, om % 60)}"
                    return out
        # No open interval matched (empty day or after last close / between slots).
        out["state"] = "closed"

        for delta in range(1, 8):
            target = ((fsq_today - 1 + delta) % 7) + 1
            for b in regular:
                if not isinstance(b, dict):
                    continue
                try:
                    d = int(b.get("day"))
                except (TypeError, ValueError):
                    continue
                if d != target:
                    continue
                o = _parse_fsq_hhmm(b.get("open"))
                if not o:
                    continue
                label = _fsq_day_label(target)
                out["opens_next"] = f"Opens {_format_ampm(o[0], o[1])} ({label})"
                return out
        return out

    on = hours.get("open_now")
    if on is True:
        out["state"] = "open"
    elif on is False:
        out["state"] = "closed"
    return out


_OSM_DAY = {"mo": 0, "tu": 1, "we": 2, "th": 3, "fr": 4, "sa": 5, "su": 6}
_OSM_DAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _osm_expand_days(prefix: str) -> Set[int]:
    m = re.match(r"^(Mo|Tu|We|Th|Fr|Sa|Su)(?:-(Mo|Tu|We|Th|Fr|Sa|Su))?$", prefix, re.I)
    if not m:
        return set()
    a, b = m.group(1).lower(), m.group(2)
    ia = _OSM_DAY.get(a, -1)
    if b is None:
        return {ia} if ia >= 0 else set()
    ib = _OSM_DAY.get(b.lower(), -1)
    if ia < 0 or ib < 0:
        return set()
    if ia <= ib:
        return set(range(ia, ib + 1))
    return set(range(ia, 7)) | set(range(0, ib + 1))


def _compute_hours_live_osm(opening: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"state": "unknown", "closes_at": None, "opens_next": None}
    if not opening or not str(opening).strip():
        return out
    s = str(opening).strip()
    low = s.lower().replace(" ", "")
    if low in ("24/7", "24/7open", "open24/7"):
        out["state"] = "open"
        out["closes_at"] = "Open 24 hours"
        return out
    now = datetime.now()
    wd = now.weekday()  # Mon=0
    now_mins = now.hour * 60 + now.minute
    m = re.match(
        r"^(Mo|Tu|We|Th|Fr|Sa|Su)(?:-(Mo|Tu|We|Th|Fr|Sa|Su))?\s+(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})",
        s,
        re.I,
    )
    if m:
        prefix = f"{m.group(1)}-{m.group(2)}" if m.group(2) else m.group(1)
        days = _osm_expand_days(prefix)
        if not days:
            return out
        h1, m1, h2, m2 = int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6))
        om, cm = h1 * 60 + m1, h2 * 60 + m2
        if cm <= om:
            return out
        if wd in days:
            if om <= now_mins < cm:
                out["state"] = "open"
                out["closes_at"] = f"Closes {_format_ampm(h2, m2)}"
                return out
            if now_mins < om:
                out["state"] = "closed"
                out["opens_next"] = f"Opens {_format_ampm(h1, m1)}"
                return out
            out["state"] = "closed"
            for add in range(1, 8):
                nwd = (wd + add) % 7
                if nwd in days:
                    out["opens_next"] = f"Opens {_format_ampm(h1, m1)} ({_OSM_DAY_LABELS[nwd]})"
                    return out
            return out
        out["state"] = "closed"
        for add in range(1, 8):
            nwd = (wd + add) % 7
            if nwd in days:
                out["opens_next"] = f"Opens {_format_ampm(h1, m1)} ({_OSM_DAY_LABELS[nwd]})"
                return out
        return out
    return out


# ── Foursquare Places ────────────────────────────────────────────────────────


def _fsq_extract_lat_lng(item: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    geo = item.get("geocodes") or {}
    main = geo.get("main") or {}
    lat = main.get("latitude")
    lng = main.get("longitude")
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)


def _fsq_format_regular_hours(regular: List[Dict[str, Any]]) -> List[str]:
    """Format Foursquare Places API hours.regular into readable lines."""
    if not regular:
        return []
    day_names = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

    def fmt_time(t: Any) -> str:
        if t is None or t == "":
            return ""
        s = str(t).strip()
        if len(s) == 4 and s.isdigit():
            return f"{s[:2]}:{s[2:]}"
        return s

    lines: List[str] = []
    for block in regular:
        if not isinstance(block, dict):
            continue
        day = block.get("day")
        open_t = block.get("open")
        close = block.get("close")
        if day is None:
            continue
        try:
            di = int(day)
        except (TypeError, ValueError):
            continue
        # Common: 1=Mon … 7=Sun (Foursquare) or 0=Sun … 6=Sat
        if 1 <= di <= 7:
            label = day_names[di - 1]
        elif 0 <= di <= 6:
            label = day_names[di]
        else:
            label = f"Day {di}"
        o = fmt_time(open_t)
        c = fmt_time(close)
        if not o and not c:
            continue
        if o and c:
            lines.append(f"{label}: {o}–{c}")
        else:
            lines.append(f"{label}: {o or c}")
    return lines


def _fsq_weekday_text(hours_obj: Dict[str, Any]) -> Optional[List[str]]:
    if not isinstance(hours_obj, dict):
        return None
    display = hours_obj.get("display")
    if isinstance(display, list):
        out = [str(x) for x in display if str(x).strip()]
        if out:
            return out
    if isinstance(display, str) and display.strip():
        return [display.strip()]
    regular = hours_obj.get("regular")
    if isinstance(regular, list) and regular:
        out = _fsq_format_regular_hours(regular)
        return out or None
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
    cats = base.get("categories") or src.get("categories") or []
    category_label = None
    for c in cats:
        if isinstance(c, dict):
            nm = (c.get("name") or "").strip()
            if nm:
                category_label = nm
                break
    live = _compute_hours_live_foursquare(hours)
    open_now_val = hours.get("open_now")
    if live["state"] == "open":
        open_now_val = True
    elif live["state"] == "closed":
        open_now_val = False
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
        "open_now": open_now_val,
        "hours_live": live,
        "weekday_text": _fsq_weekday_text(hours),
        "reviews": tips,
        "business_status": "OPERATIONAL" if base.get("closed_bucket") in (None, "VeryLikelyOpen") else "CLOSED_TEMPORARILY",
        "place_url": f"https://foursquare.com/v/{fsq_id}" if fsq_id else None,
        "website": base.get("website"),
        "category": category_label,
        "wheelchair": None,
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
    raw_reviews = result.get("reviews")
    if isinstance(raw_reviews, list):
        for r in raw_reviews:
            if len(reviews_out) >= 5:
                break
            if not isinstance(r, dict):
                continue
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
    spec_raw = (tags.get("healthcare:speciality") or tags.get("speciality") or "").strip()
    category_label = spec_raw.replace("_", " ").strip() or None
    wh = (tags.get("wheelchair") or "").strip().lower() or None
    hours_lines = _beautify_osm_opening_hours(opening) if opening else None
    live = _compute_hours_live_osm(opening)
    on = None
    if live["state"] == "open":
        on = True
    elif live["state"] == "closed":
        on = False
    otype = str(typ).lower() if typ else ""
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
        "open_now": on,
        "hours_live": live,
        "weekday_text": hours_lines,
        "reviews": [],
        "business_status": None,
        "category": category_label,
        "wheelchair": wh,
        # Internal: used for batched opening_hours fetch, stripped before API response.
        "_osm_type": otype if otype in ("node", "way", "relation") else None,
        "_osm_id": int(oid) if oid is not None else None,
    }


def _overpass_query(lat: float, lng: float) -> str:
    r = AROUND_METERS
    # Broader union: tagged speciality, name hints on clinics/doctors, and common amenity types.
    # timeout: server-side cap; keep moderate so slow mirrors fail fast to the next endpoint.
    return f"""[out:json][timeout:22];
(
  nwr["healthcare:speciality"~"dermatology|skin",i](around:{r},{lat},{lng});
  nwr["speciality"~"dermatology|skin",i](around:{r},{lat},{lng});
  nwr["name"~"Dermat|Skin|Derma|Cosmetic|Laser|Aesthetic|Tricholog|Medispa",i]["amenity"~"hospital|clinic|doctors"](around:{r},{lat},{lng});
  nwr["name"~"Dermat|Skin|Derma|Cosmetic|Laser|Aesthetic|Tricholog|Medispa",i]["healthcare"~"hospital|clinic|doctor"](around:{r},{lat},{lng});
  nwr["amenity"="doctors"]["name"~"Dermat|Skin|Derma|Cosmetic|Laser|Aesthetic|Tricholog|Medispa",i](around:{r},{lat},{lng});
  nwr["healthcare"="doctor"]["name"~"Dermat|Skin|Derma|Cosmetic|Laser|Aesthetic|Tricholog",i](around:{r},{lat},{lng});
  nwr["amenity"="clinic"]["name"~"Dermat|Skin|Derma|Cosmetic|Laser|Aesthetic|Tricholog|Medispa",i](around:{r},{lat},{lng});
);
out center tags 60;
"""


def _hospital_tags(tags: Dict[str, Any]) -> bool:
    amenity = str(tags.get("amenity") or "").lower()
    healthcare = str(tags.get("healthcare") or "").lower()
    building = str(tags.get("building") or "").lower()
    return amenity == "hospital" or healthcare == "hospital" or building == "hospital"


def _overpass_query_hospitals(lat: float, lng: float) -> str:
    r = HOSPITAL_AROUND_METERS
    return f"""[out:json][timeout:22];
(
  nwr["amenity"="hospital"](around:{r},{lat},{lng});
  nwr["healthcare"="hospital"](around:{r},{lat},{lng});
  nwr["building"="hospital"](around:{r},{lat},{lng});
);
out center tags 80;
"""


def _element_to_hospital_row(
    el: Dict[str, Any],
    origin_lat: float,
    origin_lng: float,
) -> Optional[Dict[str, Any]]:
    tags = el.get("tags") or {}
    if not _hospital_tags(tags):
        return None
    name = (tags.get("name") or tags.get("name:en") or tags.get("operator") or "").strip()
    if not name:
        name = "Hospital"
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
    emergency = str(tags.get("emergency") or "").strip().lower()
    category_label = "Emergency hospital" if emergency in ("yes", "only") else "Hospital"
    wh = (tags.get("wheelchair") or "").strip().lower() or None
    hours_lines = _beautify_osm_opening_hours(opening) if opening else None
    live = _compute_hours_live_osm(opening)
    on = None
    if live["state"] == "open":
        on = True
    elif live["state"] == "closed":
        on = False
    otype = str(typ).lower() if typ else ""
    return {
        "name": name,
        "doctor_name": None,
        "rating": None,
        "user_ratings_total": None,
        "address": addr,
        "distance_km": dkm,
        "distance": dkm,
        "lat": plat,
        "lng": plng,
        "place_id": pid,
        "provider": "openstreetmap",
        "open_now": on,
        "hours_live": live,
        "weekday_text": hours_lines,
        "reviews": [],
        "business_status": None,
        "category": category_label,
        "wheelchair": wh,
        "_osm_type": otype if otype in ("node", "way", "relation") else None,
        "_osm_id": int(oid) if oid is not None else None,
    }


_PLACE_ID_OSM_RE = re.compile(r"^(?:osm|nominatim)_(node|way|relation)_(\d+)$", re.I)


def _osm_ref_from_row(r: Dict[str, Any]) -> Optional[Tuple[str, int]]:
    otype = r.get("_osm_type")
    oid = r.get("_osm_id")
    if otype and oid is not None:
        ot = str(otype).lower()
        if ot in ("node", "way", "relation"):
            try:
                return ot, int(oid)
            except (TypeError, ValueError):
                pass
    m = _PLACE_ID_OSM_RE.match(str(r.get("place_id") or "").strip())
    if m:
        return m.group(1).lower(), int(m.group(2))
    return None


def _strip_osm_internal_refs(rows: List[Dict[str, Any]]) -> None:
    for r in rows:
        r.pop("_osm_type", None)
        r.pop("_osm_id", None)


async def _batch_enrich_opening_hours(client: httpx.AsyncClient, rows: List[Dict[str, Any]]) -> None:
    """
    Batched Overpass `out tags` for rows that still lack opening-hours text and live status.
    Covers Nominatim results (merge) and OSM objects whose first response omitted opening_hours.
    """
    unique_refs: List[Tuple[str, int]] = []
    seen: Set[str] = set()
    row_by_key: Dict[str, List[Dict[str, Any]]] = {}

    for r in rows:
        if r.get("weekday_text"):
            continue
        live = r.get("hours_live") or {}
        if live.get("state") in ("open", "closed"):
            continue
        ref = _osm_ref_from_row(r)
        if not ref:
            continue
        sk = f"{ref[0]}_{ref[1]}"
        row_by_key.setdefault(sk, []).append(r)
        if sk not in seen:
            seen.add(sk)
            unique_refs.append(ref)

    if not unique_refs:
        return

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    chunk_size = 20
    for off in range(0, len(unique_refs), chunk_size):
        chunk = unique_refs[off : off + chunk_size]
        parts: List[str] = []
        for otype, oid in chunk:
            if otype == "node":
                parts.append(f"node({oid});")
            elif otype == "way":
                parts.append(f"way({oid});")
            elif otype == "relation":
                parts.append(f"relation({oid});")
        if not parts:
            continue
        q = f"[out:json][timeout:20];\n({''.join(parts)});\nout tags;"
        data: Optional[Dict[str, Any]] = None
        for url in OVERPASS_ENDPOINTS:
            try:
                resp = await client.post(url, data={"data": q}, headers=headers, timeout=24.0)
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                logger.debug("[nearby-osm] batch hours %s: %s", url, e)
        if not data:
            continue
        for el in data.get("elements") or []:
            typ = el.get("type")
            eid = el.get("id")
            if not typ or eid is None:
                continue
            sk = f"{str(typ).lower()}_{int(eid)}"
            tags = el.get("tags") or {}
            oh = str(tags.get("opening_hours") or "").strip()
            if not oh:
                continue
            for target in row_by_key.get(sk, []):
                target["weekday_text"] = _beautify_osm_opening_hours(oh)
                live = _compute_hours_live_osm(oh)
                target["hours_live"] = live
                if live["state"] == "open":
                    target["open_now"] = True
                elif live["state"] == "closed":
                    target["open_now"] = False

    logger.info("[nearby-osm] batch opening_hours keys=%s", len(unique_refs))


async def _fetch_overpass(client: httpx.AsyncClient, lat: float, lng: float) -> List[Dict[str, Any]]:
    q = _overpass_query(lat, lng)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    last_err: Optional[Exception] = None
    for url in OVERPASS_ENDPOINTS:
        try:
            resp = await client.post(url, data={"data": q}, headers=headers, timeout=26.0)
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


async def _fetch_overpass_hospitals(client: httpx.AsyncClient, lat: float, lng: float) -> List[Dict[str, Any]]:
    q = _overpass_query_hospitals(lat, lng)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    last_err: Optional[Exception] = None
    for url in OVERPASS_ENDPOINTS:
        try:
            resp = await client.post(url, data={"data": q}, headers=headers, timeout=26.0)
            resp.raise_for_status()
            data = resp.json()
            els = data.get("elements") or []
            logger.info("[nearby-hospitals] endpoint=%s elements=%s", url, len(els))
            return els
        except Exception as e:
            last_err = e
            logger.warning("[nearby-hospitals] endpoint failed %s: %s", url, e)
    if last_err:
        raise last_err
    return []


async def _enrich_nominatim_rows_opening_hours(
    client: httpx.AsyncClient,
    rows: List[Dict[str, Any]],
) -> None:
    """Fill weekday_text from Overpass using Nominatim osm ids (opening_hours tag)."""
    need: List[Dict[str, Any]] = []
    for r in rows:
        oid = r.get("_osm_id")
        otype = (r.get("_osm_type") or "").lower()
        if oid is None or otype not in ("node", "way", "relation"):
            continue
        need.append(r)
    if not need:
        for r in rows:
            r.pop("_osm_type", None)
            r.pop("_osm_id", None)
        return

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    chunk_size = 18
    for off in range(0, len(need), chunk_size):
        chunk = need[off : off + chunk_size]
        parts: List[str] = []
        for r in chunk:
            try:
                oid = int(r["_osm_id"])
            except (TypeError, ValueError):
                continue
            otype = str(r["_osm_type"]).lower()
            if otype == "node":
                parts.append(f"node({oid});")
            elif otype == "way":
                parts.append(f"way({oid});")
            elif otype == "relation":
                parts.append(f"relation({oid});")
        if not parts:
            continue
        q = f"[out:json][timeout:18];\n({''.join(parts)});\nout tags;"
        data: Optional[Dict[str, Any]] = None
        for url in OVERPASS_ENDPOINTS:
            try:
                resp = await client.post(url, data={"data": q}, headers=headers, timeout=22.0)
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                logger.debug("[nearby-osm] enrich hours %s: %s", url, e)
                continue
        if not data:
            continue
        by_key: Dict[str, Dict[str, Any]] = {}
        for el in data.get("elements") or []:
            typ = el.get("type")
            eid = el.get("id")
            if typ and eid is not None:
                by_key[f"{typ}_{eid}"] = el.get("tags") or {}
        for r in chunk:
            try:
                oid = int(r["_osm_id"])
            except (TypeError, ValueError):
                continue
            otype = str(r["_osm_type"]).lower()
            tags = by_key.get(f"{otype}_{oid}")
            if not tags:
                continue
            oh = str(tags.get("opening_hours") or "").strip()
            if oh:
                r["weekday_text"] = _beautify_osm_opening_hours(oh)
                live = _compute_hours_live_osm(oh)
                r["hours_live"] = live
                if live["state"] == "open":
                    r["open_now"] = True
                elif live["state"] == "closed":
                    r["open_now"] = False

    for r in rows:
        r.pop("_osm_type", None)
        r.pop("_osm_id", None)


async def _fetch_nominatim_rows(
    client: httpx.AsyncClient,
    lat: float,
    lng: float,
    *,
    enrich_opening_hours: bool = True,
    keywords: Optional[Tuple[str, ...]] = None,
) -> List[Dict[str, Any]]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    # Viewbox ~matches EXTENDED_RADIUS_KM so distant Nominatim hits still appear.
    margin = max(0.18, min(0.55, EXTENDED_RADIUS_KM / 90.0))
    viewbox = f"{lng-margin},{lat+margin},{lng+margin},{lat-margin}"
    rows: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    kw_list = keywords if keywords is not None else NOMINATIM_KEYWORDS

    for kw in kw_list:
        params = {
            "q": kw,
            "format": "json",
            "limit": "40",
            "addressdetails": "1",
            "viewbox": viewbox,
            "bounded": "0",
        }
        try:
            resp = await client.get(NOMINATIM_URL, params=params, headers=headers, timeout=18.0)
            resp.raise_for_status()
            items = resp.json() or []
            logger.info("[nearby-nominatim] keyword=%r results=%s", kw, len(items))
            for it in items:
                name = _nominatim_primary_name(it.get("display_name"))
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
                        "hours_live": {"state": "unknown", "closes_at": None, "opens_next": None},
                        "weekday_text": None,
                        "reviews": [],
                        "business_status": None,
                        "category": None,
                        "wheelchair": None,
                        "_osm_type": it.get("osm_type"),
                        "_osm_id": it.get("osm_id"),
                    }
                )
        except Exception as e:
            logger.warning("[nearby-nominatim] keyword failed %r: %s", kw, e)

    rows.sort(key=lambda x: x["distance_km"])
    rows = _limit_to_nearby_radius(rows)
    if enrich_opening_hours:
        await _enrich_nominatim_rows_opening_hours(client, rows)
    # else: keep _osm_type / _osm_id for _batch_enrich_opening_hours in _fetch_osm
    return rows


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

            if len(rows) < MERGE_NOMINATIM_IF_FEWER_THAN:
                try:
                    n_rows = await _fetch_nominatim_rows(
                        client,
                        lat,
                        lng,
                        enrich_opening_hours=False,
                        keywords=NOMINATIM_KEYWORDS,
                    )
                    seen_k = {_row_dedupe_key(r) for r in rows}
                    for r in n_rows:
                        k = _row_dedupe_key(r)
                        if k in seen_k:
                            continue
                        seen_k.add(k)
                        rows.append(r)
                    rows.sort(key=lambda x: x["distance_km"])
                    rows = _limit_to_nearby_radius(rows)
                    logger.info("[nearby-osm] merged nominatim; count=%s", len(rows))
                except Exception as e:
                    logger.warning("[nearby-osm] nominatim merge skipped: %s", e)

            if not rows:
                logger.warning("[nearby-osm] zero results near lat=%s lng=%s; trying nominatim fallback", lat, lng)
                n_rows = await _fetch_nominatim_rows(
                    client,
                    lat,
                    lng,
                    enrich_opening_hours=False,
                    keywords=NOMINATIM_KEYWORDS,
                )
                if n_rows:
                    await _batch_enrich_opening_hours(client, n_rows)
                    _strip_osm_internal_refs(n_rows)
                    logger.info("[nearby-nominatim] final_count=%s", len(n_rows))
                    return n_rows, "openstreetmap"
                return [], "error_zero_results"

            await _batch_enrich_opening_hours(client, rows)
            _strip_osm_internal_refs(rows)
            logger.info("[nearby-osm] final_count=%s", min(len(rows), MIN_RESULTS_TARGET))
            return rows[:MIN_RESULTS_TARGET], "openstreetmap"

    except Exception as e:
        logger.exception("[nearby-osm] API failure: %s", e)
        # Resilient fallback when Overpass is down/throttled.
        try:
            async with httpx.AsyncClient() as client:
                n_rows = await _fetch_nominatim_rows(
                    client,
                    lat,
                    lng,
                    enrich_opening_hours=False,
                    keywords=NOMINATIM_KEYWORDS,
                )
                if n_rows:
                    await _batch_enrich_opening_hours(client, n_rows)
                    _strip_osm_internal_refs(n_rows)
                    logger.info("[nearby-nominatim] fallback_count=%s", len(n_rows))
                    return n_rows, "openstreetmap"
        except Exception as ne:
            logger.warning("[nearby-nominatim] fallback failed: %s", ne)
        return [], "error_api"


def _nominatim_item_health_facility(it: Dict[str, Any]) -> bool:
    """Keep hospitals/clinics; drop bus stops, villages named Hospital, fire extinguishers, etc."""
    cls = str(it.get("class") or "").lower()
    typ = str(it.get("type") or "").lower()
    if cls == "amenity" and typ in ("hospital", "clinic", "doctors", "health_centre"):
        return True
    if cls == "healthcare" and typ in ("hospital", "clinic", "doctor"):
        return True
    if cls in ("highway", "place", "emergency", "military", "tourism"):
        return False
    name = str(it.get("name") or "").strip().lower()
    if not name:
        return False
    if "hospital" in name or "nursing home" in name:
        return True
    if name.endswith(" clinic") or name.endswith(" clinic centre") or name.endswith(" medical centre"):
        return True
    return False


async def _fetch_nominatim_hospitals_bounded(
    client: httpx.AsyncClient, lat: float, lng: float
) -> List[Dict[str, Any]]:
    """
    Local hospitals/clinics via Nominatim (bounded viewbox). Avoids flaky public Overpass mirrors.
    """
    margin = max(0.12, min(0.52, EXTENDED_RADIUS_KM / 82.0))
    viewbox = f"{lng-margin},{lat+margin},{lng+margin},{lat-margin}"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    rows: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for i, kw in enumerate(NOMINATIM_HOSPITAL_KEYWORDS):
        if i:
            await asyncio.sleep(1.1)
        params = {
            "q": kw,
            "format": "json",
            "limit": "50",
            "addressdetails": "1",
            "viewbox": viewbox,
            "bounded": "1",
        }
        try:
            resp = await client.get(NOMINATIM_URL, params=params, headers=headers, timeout=22.0)
            resp.raise_for_status()
            items = resp.json() or []
        except Exception as e:
            logger.warning("[nearby-hospitals] nominatim q=%r failed: %s", kw, e)
            continue

        for it in items:
            if not _nominatim_item_health_facility(it):
                continue
            name = (it.get("name") or "").strip()
            if not name:
                name = _nominatim_primary_name(it.get("display_name"))
            if not name:
                continue
            ilat, ilon = it.get("lat"), it.get("lon")
            if ilat is None or ilon is None:
                continue
            plat, plng = float(ilat), float(ilon)
            dist = round(haversine_km(lat, lng, plat, plng), 2)
            if dist > EXTENDED_RADIUS_KM:
                continue
            key = f"{name.lower()}|{round(plat, 4)}|{round(plng, 4)}"
            if key in seen:
                continue
            seen.add(key)
            typ = str(it.get("type") or "").lower()
            category_label = "Hospital" if typ == "hospital" else typ.replace("_", " ").title() or "Hospital"
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
                    "place_id": f"nominatim_{it.get('osm_type', 'x')}_{it.get('osm_id', '')}",
                    "provider": "openstreetmap",
                    "open_now": None,
                    "hours_live": {"state": "unknown", "closes_at": None, "opens_next": None},
                    "weekday_text": None,
                    "reviews": [],
                    "business_status": None,
                    "category": category_label,
                    "wheelchair": None,
                }
            )

    rows.sort(key=lambda x: x["distance_km"])
    return _limit_to_nearby_radius(rows)


async def fetch_nearby_hospitals(lat: float, lng: float) -> Tuple[List[Dict[str, Any]], str]:
    """
    Nearby hospitals/clinics: Nominatim bounded search first (reliable), Overpass optional enrichment.
    Returns (results, source) with source openstreetmap | error_api.
    """
    try:
        async with httpx.AsyncClient() as client:
            rows = await _fetch_nominatim_hospitals_bounded(client, lat, lng)
            if rows:
                _strip_osm_internal_refs(rows)
                logger.info("[nearby-hospitals] nominatim lat=%s lng=%s count=%s", lat, lng, len(rows))
                return rows, "openstreetmap"

            try:
                elements = await _fetch_overpass_hospitals(client, lat, lng)
            except Exception as oe:
                logger.warning("[nearby-hospitals] overpass fallback failed: %s", oe)
                return [], "error_api"

            seen: Set[str] = set()
            orows: List[Dict[str, Any]] = []
            for el in elements:
                row = _element_to_hospital_row(el, lat, lng)
                if not row:
                    continue
                key = f"{row['name'].lower()}|{round(row['lat'], 4)}|{round(row['lng'], 4)}"
                if key in seen:
                    continue
                seen.add(key)
                orows.append(row)

            orows.sort(key=lambda x: x["distance_km"])
            orows = _limit_to_nearby_radius(orows)
            if orows:
                await _batch_enrich_opening_hours(client, orows)
            _strip_osm_internal_refs(orows)
            logger.info("[nearby-hospitals] overpass lat=%s lng=%s count=%s", lat, lng, len(orows))
            if orows:
                return orows, "openstreetmap"
            return [], "error_zero_results"
    except Exception as e:
        logger.exception("[nearby-hospitals] failed: %s", e)
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
