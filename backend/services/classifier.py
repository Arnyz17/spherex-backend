"""
Scientific Classification and Validation Triage Engine.

Synthesizes astrometric displacement, photometric variability, molecular ice features,
and detector quality bitmasks into clear scientific interpretations.
"""

from typing import List, Tuple
from backend.models.candidates import (
    ScientificCategory,
    ValidationStatus,
    IceAbsorptionFeature,
)
from backend.models.spherex import QualityFlagBitmask


class ScientificClassifier:
    """Classifies astronomical sources into scientific diagnostic categories."""

    @staticmethod
    def classify(
        displacement_arcsec: float,
        displacement_sigma: float,
        delta_mag: float,
        delta_mag_sigma: float,
        ice_features: List[IceAbsorptionFeature],
        quality_flags_int: int,
    ) -> Tuple[ScientificCategory, str, ValidationStatus, bool]:
        """
        Determines scientific category, natural language reasoning summary,
        validation status, and warning flags.
        """
        has_warnings = False
        reasons = []

        # 1. Quality & Artifact Screening
        if quality_flags_int & (QualityFlagBitmask.COSMIC_RAY | QualityFlagBitmask.BAD_PIXEL):
            return (
                ScientificCategory.SUSPECTED_ARTIFACT,
                "Detector anomaly detected: measurement contaminated by cosmic ray or hot/dead pixel.",
                ValidationStatus.LIKELY_ARTIFACT,
                True,
            )

        if quality_flags_int & QualityFlagBitmask.EDGE_PROXIMITY:
            has_warnings = True
            reasons.append("Proximity to detector edge (<15px) may introduce systematic PSF distortion.")

        if quality_flags_int & QualityFlagBitmask.SATURATED:
            has_warnings = True
            reasons.append("Core saturation present; centroid and photometry uncertainties elevated.")

        # 2. Molecular Ice Features
        detected_ices = [f for f in ice_features if f.is_detected]
        if detected_ices:
            primary_ice = max(detected_ices, key=lambda f: f.detection_significance_sigma)
            if primary_ice.molecule == "H2O":
                summary = (
                    f"Strong water-ice (H2O) absorption at ~3.0 um detected in Band 4 "
                    f"({primary_ice.detection_significance_sigma} sigma, W_lambda={primary_ice.equivalent_width_um} um)."
                )
                return (
                    ScientificCategory.WATER_ICE_ABSORPTION,
                    summary,
                    ValidationStatus.PLAUSIBLE_CANDIDATE,
                    has_warnings,
                )
            elif primary_ice.molecule == "CO2":
                summary = (
                    f"Prominent carbon dioxide (CO2) ice absorption at 4.27 um detected in Band 5 "
                    f"({primary_ice.detection_significance_sigma} sigma, W_lambda={primary_ice.equivalent_width_um} um)."
                )
                return (
                    ScientificCategory.CO2_ICE_ABSORPTION,
                    summary,
                    ValidationStatus.PLAUSIBLE_CANDIDATE,
                    has_warnings,
                )
            elif primary_ice.molecule == "CO":
                summary = (
                    f"High-resolution carbon monoxide (CO) ice absorption at 4.67 um detected in Band 6 "
                    f"({primary_ice.detection_significance_sigma} sigma, W_lambda={primary_ice.equivalent_width_um} um)."
                )
                return (
                    ScientificCategory.CO_ICE_ABSORPTION,
                    summary,
                    ValidationStatus.PLAUSIBLE_CANDIDATE,
                    has_warnings,
                )

        # 3. High Proper Motion Stars
        if displacement_sigma >= 3.0 and displacement_arcsec >= 0.10:
            summary = (
                f"Significant astrometric displacement of {displacement_arcsec}\" "
                f"({displacement_sigma:.1f} sigma) observed across temporal epochs; consistent with nearby high proper motion star."
            )
            return (
                ScientificCategory.HIGH_PROPER_MOTION,
                summary,
                ValidationStatus.PLAUSIBLE_CANDIDATE,
                has_warnings,
            )

        # 4. Photometric Transients & Variables
        if delta_mag_sigma >= 3.5 and abs(delta_mag) >= 0.25:
            summary = (
                f"Photometric brightness shift of {delta_mag:+.2f} mag "
                f"({delta_mag_sigma:.1f} sigma) detected; candidate optical/NIR transient or pulsating variable."
            )
            return (
                ScientificCategory.PHOTOMETRIC_TRANSIENT,
                summary,
                ValidationStatus.PLAUSIBLE_CANDIDATE,
                has_warnings,
            )

        # 5. Quiescent Galaxy or Stationary Stellar Baseline
        summary = "No statistically significant motion or variability detected; matches stationary galactic or extragalactic SED."
        return (
            ScientificCategory.STATIONARY_GALAXY,
            summary,
            ValidationStatus.PLAUSIBLE_CANDIDATE if not has_warnings else ValidationStatus.INCONCLUSIVE,
            has_warnings,
        )
