"""
Nearby dermatology-related places (/api/nearby).

Uses Foursquare (if configured) with OpenStreetMap fallback.
"""
from fastapi import APIRouter, HTTPException, Query

from ..services.nearby_places_service import fetch_nearby_dermatologists, fetch_nearby_hospitals
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Nearby Places"])


async def _nearby_response(lat: float, lng: float):
    results, source = await fetch_nearby_dermatologists(
        lat,
        lng,
        allow_mock_fallback=False,
        require_rich_details=False,
    )
    if source == "error_api":
        logger.error("[api/nearby] Overpass/OSM request failed")
        raise HTTPException(
            status_code=502,
            detail="OpenStreetMap data service is temporarily unavailable. Try again in a moment.",
        )
    logger.info("[api/nearby] lat=%s lng=%s count=%s source=%s", lat, lng, len(results), source)
    return results


@router.get("/nearby/hospitals")
async def get_nearby_hospitals(lat: float = Query(..., description="Latitude"), lng: float = Query(..., description="Longitude")):
    """Nearby hospitals from OpenStreetMap (Overpass)."""
    results, source = await fetch_nearby_hospitals(lat, lng)
    if source == "error_api":
        logger.error("[api/nearby/hospitals] Overpass request failed")
        raise HTTPException(
            status_code=502,
            detail="OpenStreetMap data service is temporarily unavailable. Try again in a moment.",
        )
    logger.info("[api/nearby/hospitals] lat=%s lng=%s count=%s", lat, lng, len(results))
    return results


@router.get("/nearby")
async def get_nearby_places(lat: float = Query(..., description="Latitude"), lng: float = Query(..., description="Longitude")):
    """Nearby places from Foursquare (primary) / OpenStreetMap (fallback)."""
    return await _nearby_response(lat, lng)


@router.get("/nearby-dermatologists")
async def get_nearby_dermatologists_alias(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
):
    """Backward-compatible path; identical to GET /api/nearby."""
    return await _nearby_response(lat, lng)
