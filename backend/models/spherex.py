"""
SPHEREx Spectral Band Constants and Observation Data Models.

Defines the 6 spectral channels of the SPHEREx mission, resolving power specifications,
data-quality bitmasks, and raw/calibrated observation records.
"""

from datetime import datetime
from enum import Enum, IntFlag
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SPHERExBand(str, Enum):
    """The six discrete spectral channels of the SPHEREx all-sky survey."""
    BAND_1 = "BAND_1"  # 0.75 - 1.11 um (R = 39)
    BAND_2 = "BAND_2"  # 1.11 - 1.64 um (R = 41)
    BAND_3 = "BAND_3"  # 1.64 - 2.42 um (R = 41)
    BAND_4 = "BAND_4"  # 2.42 - 3.82 um (R = 35) - H2O Ice absorption at ~3.0 um
    BAND_5 = "BAND_5"  # 3.82 - 4.42 um (R = 112) - CO2 Ice absorption at ~4.27 um
    BAND_6 = "BAND_6"  # 4.42 - 5.00 um (R = 128) - CO Ice absorption at ~4.67 um


class BandConfig(BaseModel):
    """Detailed specifications for each SPHEREx band."""
    band: SPHERExBand
    wavelength_min_um: float
    wavelength_max_um: float
    wavelength_center_um: float
    resolving_power: int
    primary_diagnostic: str


SPHEREX_BANDS_METADATA: Dict[SPHERExBand, BandConfig] = {
    SPHERExBand.BAND_1: BandConfig(
        band=SPHERExBand.BAND_1,
        wavelength_min_um=0.75,
        wavelength_max_um=1.11,
        wavelength_center_um=0.93,
        resolving_power=39,
        primary_diagnostic="Visible & NIR stellar and galaxy light; redshifted rest-frame visible emission",
    ),
    SPHERExBand.BAND_2: BandConfig(
        band=SPHERExBand.BAND_2,
        wavelength_min_um=1.11,
        wavelength_max_um=1.64,
        wavelength_center_um=1.375,
        resolving_power=41,
        primary_diagnostic="Stellar SED continuum characterization and Milky Way galactic structure",
    ),
    SPHERExBand.BAND_3: BandConfig(
        band=SPHERExBand.BAND_3,
        wavelength_min_um=1.64,
        wavelength_max_um=2.42,
        wavelength_center_um=2.03,
        resolving_power=41,
        primary_diagnostic="Cosmic Infrared Background (CIB) fluctuations and galaxy photometric redshifts",
    ),
    SPHERExBand.BAND_4: BandConfig(
        band=SPHERExBand.BAND_4,
        wavelength_min_um=2.42,
        wavelength_max_um=3.82,
        wavelength_center_um=3.12,
        resolving_power=35,
        primary_diagnostic="Molecular and interstellar water-ice (H2O) broad absorption feature near 3.0 um",
    ),
    SPHERExBand.BAND_5: BandConfig(
        band=SPHERExBand.BAND_5,
        wavelength_min_um=3.82,
        wavelength_max_um=4.42,
        wavelength_center_um=4.12,
        resolving_power=112,
        primary_diagnostic="High-detail carbon dioxide (CO2) ice absorption feature near 4.27 um",
    ),
    SPHERExBand.BAND_6: BandConfig(
        band=SPHERExBand.BAND_6,
        wavelength_min_um=4.42,
        wavelength_max_um=5.00,
        wavelength_center_um=4.71,
        resolving_power=128,
        primary_diagnostic="Maximum resolution carbon monoxide (CO) ice absorption feature near 4.67 um",
    ),
}


class QualityFlagBitmask(IntFlag):
    """Bitmask for detector and observation quality indicators."""
    CLEAN = 0
    BAD_PIXEL = 1 << 0          # Bit 0: Dead or hot detector pixel
    COSMIC_RAY = 1 << 1         # Bit 1: Cosmic ray hit detected
    SATURATED = 1 << 2          # Bit 2: Saturated pixel within PSF core
    EDGE_PROXIMITY = 1 << 3     # Bit 3: Source < 15px from detector boundary
    HIGH_JITTER = 1 << 4        # Bit 4: Spacecraft pointing jitter exceeded tolerance
    STRAY_LIGHT = 1 << 5        # Bit 5: Earth limb or solar stray light contamination


def decode_quality_flags(flags: int) -> List[str]:
    """Converts a bitmask integer into human-readable indicator strings."""
    if flags == 0:
        return ["nominal", "clean"]
    indicators = []
    if flags & QualityFlagBitmask.BAD_PIXEL:
        indicators.append("bad_pixel")
    if flags & QualityFlagBitmask.COSMIC_RAY:
        indicators.append("cosmic_ray")
    if flags & QualityFlagBitmask.SATURATED:
        indicators.append("saturated")
    if flags & QualityFlagBitmask.EDGE_PROXIMITY:
        indicators.append("edge_proximity")
    if flags & QualityFlagBitmask.HIGH_JITTER:
        indicators.append("high_jitter")
    if flags & QualityFlagBitmask.STRAY_LIGHT:
        indicators.append("stray_light")
    return indicators


class WCSMetadata(BaseModel):
    """World Coordinate System parameters for projecting detector pixels to celestial coordinates."""
    crval1: float = Field(..., description="Reference Right Ascension in degrees")
    crval2: float = Field(..., description="Reference Declination in degrees")
    crpix1: float = Field(..., description="Reference pixel X index")
    crpix2: float = Field(..., description="Reference pixel Y index")
    cdelt1: float = Field(..., description="Pixel scale RA (deg/pix)")
    cdelt2: float = Field(..., description="Pixel scale Dec (deg/pix)")
    ctype1: str = Field(default="RA---TAN", description="Coordinate projection type RA")
    ctype2: str = Field(default="DEC--TAN", description="Coordinate projection type Dec")


class SourceMeasurement(BaseModel):
    """A single source detection within an observation."""
    source_id: str
    pixel_x: float
    pixel_y: float
    ra_deg: float
    dec_deg: float
    positional_uncertainty_arcsec: float
    flux_density_mjy: float
    flux_uncertainty_mjy: float
    snr: float
    quality_flags: int = 0


class ObservationRecord(BaseModel):
    """
    Complete observation record conforming to SPHEREx backend requirements:
    - Observation image reference
    - Observation timestamp (UTC & MJD)
    - WCS metadata
    - Wavelength information (band, central wavelength)
    - Source coordinates & uncertainties
    - Data quality flags
    - Calibration & metadata
    """
    observation_id: str = Field(..., description="Unique frame exposure identifier")
    timestamp_utc: datetime = Field(..., description="UTC timestamp of the observation")
    timestamp_mjd: float = Field(..., description="Modified Julian Date (JD - 2400000.5)")
    band: SPHERExBand = Field(..., description="SPHEREx spectral channel")
    wavelength_center_um: float = Field(..., description="Nominal center wavelength in microns")
    exposure_time_sec: float = Field(..., description="Exposure duration in seconds")
    wcs: WCSMetadata = Field(..., description="World Coordinate System metadata")
    quality_flags: int = Field(default=0, description="Observation-level quality flag bitmask")
    zeropoint_mag: float = Field(..., description="Photometric zero-point calibration")
    background_rms: float = Field(..., description="Sky background noise RMS in mJy/sr")
    sources: List[SourceMeasurement] = Field(default_factory=list, description="Extracted sources in frame")
    image_uri: Optional[str] = Field(default=None, description="Path or URI to observation image array")
