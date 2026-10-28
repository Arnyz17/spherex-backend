"""Scientific services package for SPHEREx backend."""

from backend.services.wcs_engine import WCSEngine
from backend.services.differencing import (
    compute_angular_separation_arcsec,
    compute_astrometric_displacement,
    compute_photometric_variability,
    flux_mjy_to_ab_mag,
    DisplacementResult,
    PhotometricDiffResult,
)
from backend.services.spectral_ice import (
    KNOWN_ICE_FEATURES,
    SpectralAnalyzer,
    IceFeatureSpec,
)
from backend.services.classifier import ScientificClassifier
from backend.services.cutout_generator import CutoutGenerator

__all__ = [
    "WCSEngine",
    "compute_angular_separation_arcsec",
    "compute_astrometric_displacement",
    "compute_photometric_variability",
    "flux_mjy_to_ab_mag",
    "DisplacementResult",
    "PhotometricDiffResult",
    "KNOWN_ICE_FEATURES",
    "SpectralAnalyzer",
    "IceFeatureSpec",
    "ScientificClassifier",
    "CutoutGenerator",
]
