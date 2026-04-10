"""
Server-side Nominatim proxy — browsers cannot call nominatim.openstreetmap.org (no CORS).

502 from this app means the upstream Nominatim request failed (403/429/5xx, timeout, TLS, etc.).
Public Nominatim is strict: use a descriptive User-Agent with contact (set NOMINATIM_CONTACT_EMAIL in .env).
On failure we still return a safe JSON shape so optional features (e.g. saving a city name) degrade gracefully.
"""
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import httpx

from ..config.settings import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
USER_AGENT_BASE = "DermaCareAI/2.0 (geocode proxy; student project)"

router = APIRouter(tags=["Geocode"])


def _nominatim_headers() -> dict:
    contact = (getattr(settings, "NOMINATIM_CONTACT_EMAIL", None) or "").strip()
    ua = USER_AGENT_BASE
    if contact and "@" in contact:
        ua = f"{USER_AGENT_BASE} (contact: {contact})"
    return {
        "User-Agent": ua,
        "Accept-Language": "en",
        "Accept": "application/json",
    }


@router.get("/geocode/reverse")
async def geocode_reverse(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    zoom: int = Query(14, ge=1, le=18),
    response_format: str = Query("json", alias="format"),
):
    fmt = response_format if response_format in ("json", "jsonv2") else "json"
    params = {
        "format": fmt,
        "lat": lat,
        "lon": lon,
        "zoom": zoom,
        "addressdetails": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            r = await client.get(NOMINATIM_REVERSE, params=params, headers=_nominatim_headers())
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        logger.warning(
            "[geocode/reverse] Nominatim HTTP %s — set NOMINATIM_CONTACT_EMAIL in .env if you see 403",
            e.response.status_code,
        )
        # Same shape clients expect; empty address avoids crashes when saving location label.
        return JSONResponse(
            status_code=200,
            content={
                "address": {},
                "display_name": "",
                "lat": str(lat),
                "lon": str(lon),
                "error": "geocode_unavailable",
            },
        )
    except Exception as e:
        logger.warning("[geocode/reverse] failed: %s", e)
        return JSONResponse(
            status_code=200,
            content={
                "address": {},
                "display_name": "",
                "lat": str(lat),
                "lon": str(lon),
                "error": "geocode_unavailable",
            },
        )


@router.get("/geocode/search")
async def geocode_search(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(6, ge=1, le=15),
):
    params = {"q": q, "format": "json", "limit": limit, "addressdetails": 1}
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            r = await client.get(NOMINATIM_SEARCH, params=params, headers=_nominatim_headers())
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else []
    except httpx.HTTPStatusError as e:
        logger.warning(
            "[geocode/search] Nominatim HTTP %s — set NOMINATIM_CONTACT_EMAIL in .env if you see 403",
            e.response.status_code,
        )
        return []
    except Exception as e:
        logger.warning("[geocode/search] failed: %s", e)
        return []
