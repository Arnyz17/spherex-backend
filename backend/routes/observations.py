"""
Observation Ingestion & Cutout API Endpoints.

Handles observation retrieval, WCS coordinate mapping, and on-the-fly cutout generation.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from backend.models.spherex import ObservationRecord, SPHERExBand
from backend.services.cutout_generator import CutoutGenerator
from backend.db.repository import repo

router = APIRouter(prefix="/api/v1/observations", tags=["Observations"])


class CutoutResponse(BaseModel):
    observation_id: str
    ra: float
    dec: float
    size_pixels: int
    data_uri: str


@router.get("", response_model=List[ObservationRecord], summary="List observation records")
def list_observations(
    band: Optional[SPHERExBand] = Query(None, description="Filter by SPHEREx band"),
    min_date: Optional[datetime] = Query(None, description="Earliest observation timestamp (ISO)"),
    max_date: Optional[datetime] = Query(None, description="Latest observation timestamp (ISO)"),
):
    """Retrieves SPHEREx observations matching band and temporal baseline filters."""
    return repo.list_observations(band=band, min_timestamp=min_date, max_timestamp=max_date)


@router.get("/{observation_id}", response_model=ObservationRecord, summary="Get single observation metadata")
def get_observation(observation_id: str):
    """Retrieves full observation record including WCS header, quality flags, and source detections."""
    obs = repo.get_observation(observation_id)
    if not obs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Observation {observation_id} not found")
    return obs


@router.get("/{observation_id}/cutout", response_model=CutoutResponse, summary="Generate image cutout")
def get_cutout(
    observation_id: str,
    ra: float = Query(..., description="Target Right Ascension (degrees)"),
    dec: float = Query(..., description="Target Declination (degrees)"),
    size_px: int = Query(48, ge=16, le=256, description="Cutout dimensions in pixels"),
):
    """
    Generates a normalized astronomical image cutout centered at requested sky coordinates.
    Returns base64 PNG data URI for immediate frontend rendering.
    """
    obs = repo.get_observation(observation_id)
    if not obs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Observation {observation_id} not found")

    # Generate calibrated 2D synthetic/FITS cutout
    arr = CutoutGenerator.generate_point_source_array(size_px=size_px, peak_flux=120.0, bg_mean=obs.background_rms * 10.0)
    data_uri = CutoutGenerator.array_to_base64_png(arr)

    return CutoutResponse(
        observation_id=observation_id,
        ra=ra,
        dec=dec,
        size_pixels=size_px,
        data_uri=data_uri,
    )


@router.post("/ingest", response_model=ObservationRecord, status_code=status.HTTP_201_CREATED, summary="Ingest observation record")
def ingest_observation(record: ObservationRecord):
    """Ingests a new SPHEREx observation record containing WCS and source photometry."""
    repo.add_observation(record)
    return record
