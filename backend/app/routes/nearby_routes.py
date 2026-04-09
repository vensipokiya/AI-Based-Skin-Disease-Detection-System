"""
Google Places–backed nearby dermatologists API (/api/nearby).
"""
from fastapi import APIRouter, HTTPException, Query

from ..services.nearby_places_service import fetch_nearby_dermatologists
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Nearby Places"])


async def _nearby_response(lat: float, lng: float):
    results, source = await fetch_nearby_dermatologists(lat, lng, allow_mock_fallback=False)
    if source == "error_no_key":
        logger.error("[api/nearby] GOOGLE_PLACES_API_KEY not configured")
        raise HTTPException(
            status_code=503,
            detail="Missing GOOGLE_PLACES_API_KEY. Add it to backend/.env and enable Places API + billing in Google Cloud.",
        )
    if source.startswith("error_"):
        logger.error("[api/nearby] upstream failure source=%s", source)
        raise HTTPException(
            status_code=502,
            detail="Google Places request failed. Check API key, Places API enablement, and billing.",
        )
    logger.info("[api/nearby] lat=%s lng=%s count=%s source=%s", lat, lng, len(results), source)
    return results


@router.get("/nearby")
async def get_nearby_places(lat: float = Query(..., description="Latitude"), lng: float = Query(..., description="Longitude")):
    """Real Google Places only — same contract as legacy /api/nearby-dermatologists."""
    return await _nearby_response(lat, lng)


@router.get("/nearby-dermatologists")
async def get_nearby_dermatologists_alias(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
):
    """Backward-compatible path; identical to GET /api/nearby."""
    return await _nearby_response(lat, lng)
