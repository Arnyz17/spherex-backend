"""
SPHEREx 6-Band Spectral Analyzer and Molecular Ice Feature Extractor.

Specialized diagnostics for:
1. Water Ice (H2O): ~3.0 um in Band 4 (2.4 - 3.8 um, R=35)
2. Carbon Dioxide Ice (CO2): ~4.27 um in Band 5 (3.8 - 4.4 um, R=112)
3. Carbon Monoxide Ice (CO): ~4.67 um in Band 6 (4.4 - 5.0 um, R=128)
"""

import math
from typing import List, Dict, Optional, Tuple
import numpy as np
from backend.models.spherex import SPHERExBand, SPHEREX_BANDS_METADATA
from backend.models.candidates import SpectralPoint, IceAbsorptionFeature


class IceFeatureSpec:
    """Definition of known interstellar ice absorption profiles."""
    def __init__(
        self,
        molecule: str,
        target_band: SPHERExBand,
        center_um: float,
        feature_min_um: float,
        feature_max_um: float,
        continuum_blue_range: Tuple[float, float],
        continuum_red_range: Tuple[float, float],
    ):
        self.molecule = molecule
        self.target_band = target_band
        self.center_um = center_um
        self.feature_min_um = feature_min_um
        self.feature_max_um = feature_max_um
        self.continuum_blue_range = continuum_blue_range
        self.continuum_red_range = continuum_red_range


KNOWN_ICE_FEATURES: Dict[str, IceFeatureSpec] = {
    "H2O": IceFeatureSpec(
        molecule="H2O",
        target_band=SPHERExBand.BAND_4,
        center_um=3.05,
        feature_min_um=2.85,
        feature_max_um=3.25,
        continuum_blue_range=(2.50, 2.75),
        continuum_red_range=(3.50, 3.75),
    ),
    "CO2": IceFeatureSpec(
        molecule="CO2",
        target_band=SPHERExBand.BAND_5,
        center_um=4.27,
        feature_min_um=4.22,
        feature_max_um=4.32,
        continuum_blue_range=(3.95, 4.15),
        continuum_red_range=(4.35, 4.40),
    ),
    "CO": IceFeatureSpec(
        molecule="CO",
        target_band=SPHERExBand.BAND_6,
        center_um=4.67,
        feature_min_um=4.62,
        feature_max_um=4.72,
        continuum_blue_range=(4.48, 4.58),
        continuum_red_range=(4.78, 4.92),
    ),
}


class SpectralAnalyzer:
    """Extracts continuum baselines, measures equivalent widths, and detects ice absorption signatures."""

    @staticmethod
    def measure_equivalent_width(
        spectrum: List[SpectralPoint],
        feature_spec: IceFeatureSpec,
    ) -> IceAbsorptionFeature:
        """
        Computes Equivalent Width (W_lambda) for a specified ice band.
        W_lambda = sum_k (1 - F_obs(lambda_k) / F_cont(lambda_k)) * d_lambda_k
        """
        sorted_spec = sorted(spectrum, key=lambda p: p.wavelength_um)
        wavelengths = np.array([p.wavelength_um for p in sorted_spec])
        fluxes = np.array([p.flux_density_mjy for p in sorted_spec])
        errors = np.array([p.flux_error_mjy for p in sorted_spec])

        # Find continuum points in blue and red anchor ranges
        blue_mask = (wavelengths >= feature_spec.continuum_blue_range[0]) & (wavelengths <= feature_spec.continuum_blue_range[1])
        red_mask = (wavelengths >= feature_spec.continuum_red_range[0]) & (wavelengths <= feature_spec.continuum_red_range[1])

        # If sparse points, estimate continuum using nearest neighbors
        if np.sum(blue_mask) == 0 or np.sum(red_mask) == 0:
            # Fallback local linear fit
            band_mask = np.array([p.band == feature_spec.target_band for p in sorted_spec])
            if np.sum(band_mask) < 2:
                return IceAbsorptionFeature(
                    molecule=feature_spec.molecule,
                    central_wavelength_um=feature_spec.center_um,
                    equivalent_width_um=0.0,
                    equivalent_width_uncertainty_um=0.05,
                    detection_significance_sigma=0.0,
                    band=feature_spec.target_band,
                    is_detected=False,
                )
            f_blue = np.mean(fluxes[band_mask][:2])
            w_blue = np.mean(wavelengths[band_mask][:2])
            f_red = np.mean(fluxes[band_mask][-2:])
            w_red = np.mean(wavelengths[band_mask][-2:])
        else:
            w_blue = float(np.mean(wavelengths[blue_mask]))
            f_blue = float(np.mean(fluxes[blue_mask]))
            w_red = float(np.mean(wavelengths[red_mask]))
            f_red = float(np.mean(fluxes[red_mask]))

        # Linear continuum model: F_cont(w) = slope * w + intercept
        dw = w_red - w_blue
        if abs(dw) < 1e-5:
            slope = 0.0
            intercept = f_blue
        else:
            slope = (f_red - f_blue) / dw
            intercept = f_blue - slope * w_blue

        # Feature absorption integration window
        feat_mask = (wavelengths >= feature_spec.feature_min_um) & (wavelengths <= feature_spec.feature_max_um)
        if np.sum(feat_mask) == 0:
            return IceAbsorptionFeature(
                molecule=feature_spec.molecule,
                central_wavelength_um=feature_spec.center_um,
                equivalent_width_um=0.0,
                equivalent_width_uncertainty_um=0.05,
                detection_significance_sigma=0.0,
                band=feature_spec.target_band,
                is_detected=False,
            )

        feat_w = wavelengths[feat_mask]
        feat_f = fluxes[feat_mask]
        feat_err = errors[feat_mask]

        eq_width = 0.0
        var_eq_width = 0.0

        for i in range(len(feat_w)):
            w_i = feat_w[i]
            f_i = feat_f[i]
            err_i = feat_err[i]
            f_cont_i = max(1e-4, slope * w_i + intercept)

            # Bin width calculation
            if len(feat_w) == 1:
                delta_w = feature_spec.feature_max_um - feature_spec.feature_min_um
            elif i == 0:
                delta_w = (feat_w[1] - feat_w[0])
            elif i == len(feat_w) - 1:
                delta_w = (feat_w[-1] - feat_w[-2])
            else:
                delta_w = (feat_w[i + 1] - feat_w[i - 1]) / 2.0

            depth = (1.0 - (f_i / f_cont_i))
            eq_width += depth * delta_w
            # Error propagation: sigma(W)^2 = sum ( (delta_w / F_cont)^2 * sigma_F^2 )
            var_eq_width += ((delta_w / f_cont_i) * err_i) ** 2

        sigma_w = math.sqrt(var_eq_width) if var_eq_width > 0 else 0.01
        significance = eq_width / sigma_w if sigma_w > 0 else 0.0

        is_detected = (significance >= 3.0) and (eq_width > 0.02)

        return IceAbsorptionFeature(
            molecule=feature_spec.molecule,
            central_wavelength_um=feature_spec.center_um,
            equivalent_width_um=round(float(eq_width), 4),
            equivalent_width_uncertainty_um=round(float(sigma_w), 4),
            detection_significance_sigma=round(float(significance), 2),
            band=feature_spec.target_band,
            is_detected=is_detected,
        )

    @classmethod
    def analyze_candidate_ices(cls, spectrum: List[SpectralPoint]) -> List[IceAbsorptionFeature]:
        """Runs full ice feature diagnostic suite (H2O, CO2, CO) on candidate spectrum."""
        results = []
        for molecule, spec in KNOWN_ICE_FEATURES.items():
            result = cls.measure_equivalent_width(spectrum, spec)
            results.append(result)
        return results
