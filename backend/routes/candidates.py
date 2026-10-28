"""
Candidate Inspection & Triage API Endpoints.

Provides filtering, retrieval, and validation triage actions for frontend developers.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from backend.models.candidates import (
    CandidateSummary,
    CandidateDetail,
    ValidationStatus,
    ScientificCategory,
    ValidationUpdateRequest,
)
from backend.db.repository import repo

router = APIRouter(prefix="/api/v1/candidates", tags=["Candidates"])


class CandidateListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CandidateSummary]


@router.get("", response_model=CandidateListResponse, summary="Query and filter detected candidates")
def list_candidates(
    min_displacement_sigma: Optional[float] = Query(None, description="Minimum proper motion significance in sigma"),
    min_delta_mag: Optional[float] = Query(None, description="Minimum absolute magnitude difference |Delta m|"),
    ice_molecule: Optional[str] = Query(None, description="Filter by molecular ice absorption: H2O, CO2, or CO"),
    validation_status: Optional[ValidationStatus] = Query(None, description="Filter by triage status"),
    category: Optional[ScientificCategory] = Query(None, description="Filter by scientific category"),
    ra: Optional[float] = Query(None, ge=0.0, le=360.0, description="Cone search center RA (deg)"),
    dec: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Cone search center Dec (deg)"),
    radius_arcmin: Optional[float] = Query(None, gt=0.0, description="Cone search radius in arcminutes"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    Returns paginated candidate summaries satisfying the 9 frontend developer fields:
    - Object/candidate ID
    - Sky coordinates (RA/Dec)
    - Observation dates
    - Observed spectral channels
    - Measured displacement & brightness change
    - Uncertainties (astrometric & photometric)
    - Quality indicators
    - Scientific interpretation
    - Validation status
    """
    items, total = repo.list_candidates(
        min_displacement_sigma=min_displacement_sigma,
        min_delta_mag=min_delta_mag,
        ice_molecule=ice_molecule,
        validation_status=validation_status,
        category=category,
        ra_deg=ra,
        dec_deg=dec,
        radius_arcmin=radius_arcmin,
        page=page,
        page_size=page_size,
    )
    return CandidateListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/{candidate_id}", response_model=CandidateDetail, summary="Get complete candidate detail")
def get_candidate(candidate_id: str):
    """
    Returns full candidate detail including:
    - Multi-epoch astrometry timeline
    - Calibrated 6-band spectrum
    - Measured ice absorption equivalent widths (H2O, CO2, CO)
    - Thumbnail image cutouts for visual verification
    """
    cand = repo.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate {candidate_id} not found")
    return cand


@router.post("/{candidate_id}/validate", response_model=CandidateDetail, summary="Update candidate validation status")
def update_validation(candidate_id: str, request: ValidationUpdateRequest):
    """
    Frontend triage endpoint: updates validation status (Plausible Candidate, Confirmed,
    Inconclusive, Likely Artifact) and adds scientist verification notes.
    """
    updated = repo.update_validation(candidate_id, request.validation_status, request.user_notes)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate {candidate_id} not found")
    return updated
