"""
SPHEREx Spectral Configuration and Ice Diagnostic API Endpoints.
"""

from typing import Dict, List
from fastapi import APIRouter
from pydantic import BaseModel
from backend.models.spherex import SPHERExBand, SPHEREX_BANDS_METADATA, BandConfig
from backend.services.spectral_ice import KNOWN_ICE_FEATURES

router = APIRouter(prefix="/api/v1/spectral", tags=["Spectral & Ices"])


class IceFeatureInfo(BaseModel):
    molecule: str
    target_band: SPHERExBand
    center_um: float
    feature_range_um: List[float]
    scientific_significance: str


@router.get("/bands", response_model=Dict[SPHERExBand, BandConfig], summary="Get SPHEREx 6-band configuration")
def get_bands():
    """Returns wavelength boundaries, resolving powers R, and scientific targets for Bands 1 to 6."""
    return SPHEREX_BANDS_METADATA


@router.get("/ice-diagnostics", response_model=List[IceFeatureInfo], summary="Get molecular ice absorption diagnostics")
def get_ice_diagnostics():
    """
    Returns reference molecular ice features investigated by SPHEREx:
    - H2O Ice (~3.0 um in Band 4, R=35)
    - CO2 Ice (~4.27 um in Band 5, R=112)
    - CO Ice (~4.67 um in Band 6, R=128)
    """
    diagnostics = [
        IceFeatureInfo(
            molecule="H2O",
            target_band=SPHERExBand.BAND_4,
            center_um=3.05,
            feature_range_um=[2.85, 3.25],
            scientific_significance="Interstellar and circumstellar water-ice in molecular clouds and protoplanetary disks.",
        ),
        IceFeatureInfo(
            molecule="CO2",
            target_band=SPHERExBand.BAND_5,
            center_um=4.27,
            feature_range_um=[4.22, 4.32],
            scientific_significance="Solid carbon dioxide ice, tracing thermal processing in protostellar envelopes.",
        ),
        IceFeatureInfo(
            molecule="CO",
            target_band=SPHERExBand.BAND_6,
            center_um=4.67,
            feature_range_um=[4.62, 4.72],
            scientific_significance="Volatile carbon monoxide ice freezing out in cold (<20 K) dense cores.",
        ),
    ]
    return diagnostics
