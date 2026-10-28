"""
Candidate and Source Models for Frontend Presentation and Scientific Validation.

Maps all 9 frontend requirements:
1. Object or candidate ID
2. Sky coordinates
3. Observation dates / timestamps
4. Wavelength or spectral channel
5. Measured displacement or brightness change
6. Measurement uncertainty
7. Data-quality indicators
8. Scientific interpretation
9. Validation status
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from backend.models.spherex import SPHERExBand


class ValidationStatus(str, Enum):
    """Validation workflow statuses for triage and review."""
    PLAUSIBLE_CANDIDATE = "Plausible Candidate"
    CONFIRMED = "Confirmed"
    INCONCLUSIVE = "Inconclusive"
    LIKELY_ARTIFACT = "Likely Artifact"


class ScientificCategory(str, Enum):
    """Scientific classifications derived from multi-epoch astrometry, variability, and spectroscopy."""
    HIGH_PROPER_MOTION = "High Proper Motion Star"
    PHOTOMETRIC_TRANSIENT = "Photometric Transient / Variable Star"
    WATER_ICE_ABSORPTION = "Interstellar H2O Ice Feature"
    CO2_ICE_ABSORPTION = "Circumstellar CO2 Ice Feature"
    CO_ICE_ABSORPTION = "Dense Core CO Ice Feature"
    STATIONARY_GALAXY = "Quiescent Galaxy SED"
    SUSPECTED_ARTIFACT = "Detector Artifact / Spike"


class IceAbsorptionFeature(BaseModel):
    """Specific molecular ice absorption detection result."""
    molecule: str = Field(..., description="Molecular formula: H2O, CO2, or CO")
    central_wavelength_um: float = Field(..., description="Expected line center in microns (3.0, 4.27, or 4.67)")
    equivalent_width_um: float = Field(..., description="Integrated equivalent width in microns")
    equivalent_width_uncertainty_um: float = Field(..., description="1-sigma uncertainty")
    detection_significance_sigma: float = Field(..., description="Significance ratio W / sigma_W")
    band: SPHERExBand
    is_detected: bool = Field(..., description="True if detection significance >= 3.0 sigma")


class SpectralPoint(BaseModel):
    """A calibrated photometric measurement in the candidate's spectrum."""
    wavelength_um: float = Field(..., description="Wavelength in microns")
    flux_density_mjy: float = Field(..., description="Monochromatic flux density in milliJanskys")
    flux_error_mjy: float = Field(..., description="1-sigma measurement uncertainty")
    band: SPHERExBand
    resolving_power: int


class CandidateSummary(BaseModel):
    """
    Summary view designed specifically for frontend data tables and candidate feeds.
    Satisfies all 9 frontend requirements.
    """
    candidate_id: str = Field(..., description="Unique source or candidate identifier")
    ra: float = Field(..., description="Right Ascension in degrees (J2000)")
    dec: float = Field(..., description="Declination in degrees (J2000)")
    observation_dates: List[datetime] = Field(..., description="Chronological observation timestamps")
    bands_observed: List[SPHERExBand] = Field(..., description="Observed SPHEREx channels")
    
    # Measured displacement & uncertainty
    displacement_arcsec: float = Field(..., description="Net angular displacement between first and last epochs")
    displacement_uncertainty_arcsec: float = Field(..., description="1-sigma positional uncertainty in displacement")
    displacement_significance_sigma: float = Field(..., description="Astrometric shift significance")
    
    # Measured brightness change & uncertainty
    delta_brightness_mag: float = Field(..., description="Magnitude change across epochs (m_last - m_first)")
    delta_brightness_uncertainty_mag: float = Field(..., description="1-sigma photometric uncertainty")
    delta_brightness_significance_sigma: float = Field(..., description="Photometric variability significance")
    
    # Data quality
    quality_indicators: List[str] = Field(..., description="Data quality tags (e.g. ['nominal', 'clean'])")
    has_quality_warnings: bool = Field(default=False, description="True if unflagged artifacts or edge issues exist")
    
    # Scientific interpretation & Validation
    scientific_interpretation: ScientificCategory = Field(..., description="Evidence-backed scientific category")
    scientific_summary: str = Field(..., description="Human-readable explanation of the scientific evidence")
    validation_status: ValidationStatus = Field(..., description="Current triage / validation state")


class EpochMeasurement(BaseModel):
    """Detailed observation snapshot for a single epoch."""
    epoch_index: int
    observation_id: str
    timestamp_utc: datetime
    timestamp_mjd: float
    band: SPHERExBand
    ra: float
    dec: float
    flux_density_mjy: float
    flux_density_err_mjy: float
    magnitude: float
    magnitude_err: float
    quality_flags: List[str]


class CandidateDetail(CandidateSummary):
    """
    Full detail view for deep candidate inspection and interactive triage.
    Includes full 6-band spectrum, multi-epoch history, and ice feature measurements.
    """
    epochs: List[EpochMeasurement] = Field(default_factory=list, description="Per-epoch measurements")
    spectrum: List[SpectralPoint] = Field(default_factory=list, description="Extracted 6-band spectrum")
    ice_features: List[IceAbsorptionFeature] = Field(default_factory=list, description="Fitted molecular ice bands")
    cutout_thumbnails: Dict[str, str] = Field(
        default_factory=dict, 
        description="Base64 or URL thumbnail map: e.g. {'epoch_0': 'data:image/png;base64,...'}"
    )
    user_notes: str = Field(default="", description="Scientist verification notes and comments")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ValidationUpdateRequest(BaseModel):
    """Payload sent by the frontend to update a candidate's triage state."""
    validation_status: ValidationStatus
    user_notes: Optional[str] = None
