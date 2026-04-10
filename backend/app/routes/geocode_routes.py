"""
Server-side Nominatim proxy — browsers cannot call nominatim.openstreetmap.org (no CORS).
"""
from fastapi import APIRouter, HTTPException, Query
import httpx

from ..utils.logger import get_logger

logger = get_logger(__name__)

NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "DermaCareAI/2.0 (geocode proxy; student project)"
_HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en"}

router = APIRouter(tags=["Geocode"])


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
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(NOMINATIM_REVERSE, params=params, headers=_HEADERS)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        logger.warning("[geocode/reverse] Nominatim HTTP %s", e.response.status_code)
        raise HTTPException(status_code=502, detail="Geocoding service error") from e
    except Exception as e:
        logger.exception("[geocode/reverse] failed: %s", e)
        raise HTTPException(status_code=502, detail="Geocoding unavailable") from e


@router.get("/geocode/search")
async def geocode_search(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(6, ge=1, le=15),
):
    params = {"q": q, "format": "json", "limit": limit, "addressdetails": 1}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(NOMINATIM_SEARCH, params=params, headers=_HEADERS)
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else []
    except httpx.HTTPStatusError as e:
        logger.warning("[geocode/search] Nominatim HTTP %s", e.response.status_code)
        raise HTTPException(status_code=502, detail="Geocoding service error") from e
    except Exception as e:
        logger.exception("[geocode/search] failed: %s", e)
        raise HTTPException(status_code=502, detail="Geocoding unavailable") from e
