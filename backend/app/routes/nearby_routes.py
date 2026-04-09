"""
Nearby dermatology-related places (/api/nearby).

Uses Google Places when GOOGLE_PLACES_API_KEY is set; otherwise OpenStreetMap (Overpass).
"""
from fastapi import APIRouter, HTTPException, Query

from ..services.nearby_places_service import fetch_nearby_dermatologists
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Nearby Places"])


async def _nearby_response(lat: float, lng: float):
    results, source = await fetch_nearby_dermatologists(
        lat,
        lng,
        allow_mock_fallback=False,
        require_rich_details=True,
    )
    if source == "error_no_key":
        raise HTTPException(
            status_code=503,
            detail="Missing GOOGLE_PLACES_API_KEY. Add it in backend/.env, enable Places API + billing, then restart backend.",
        )
    if source == "error_google":
        raise HTTPException(
            status_code=502,
            detail="Google Places data unavailable for this request. Check API key restrictions, Places API enablement, and billing.",
        )
    if source == "error_api":
        logger.error("[api/nearby] Overpass/OSM request failed")
        raise HTTPException(
            status_code=502,
            detail="OpenStreetMap data service is temporarily unavailable. Try again in a moment.",
        )
    logger.info("[api/nearby] lat=%s lng=%s count=%s source=%s", lat, lng, len(results), source)
    return results


@router.get("/nearby")
async def get_nearby_places(lat: float = Query(..., description="Latitude"), lng: float = Query(..., description="Longitude")):
    """Nearby places: Google Places (if configured) else OSM."""
    return await _nearby_response(lat, lng)


@router.get("/nearby-dermatologists")
async def get_nearby_dermatologists_alias(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
):
    """Backward-compatible path; identical to GET /api/nearby."""
    return await _nearby_response(lat, lng)
