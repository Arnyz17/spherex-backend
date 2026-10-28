"""Unit tests for SPHEREx 6-Band Spectral and Molecular Ice Analyzer."""

import pytest
from backend.models.spherex import SPHERExBand
from backend.models.candidates import SpectralPoint
from backend.services.spectral_ice import SpectralAnalyzer, KNOWN_ICE_FEATURES


def test_ice_absorption_detection():
    # Construct a synthetic spectrum with an artificial 3.0 um H2O ice absorption trough in Band 4
    spectrum = [
        SpectralPoint(wavelength_um=0.93, flux_density_mjy=10.0, flux_error_mjy=0.2, band=SPHERExBand.BAND_1, resolving_power=39),
        SpectralPoint(wavelength_um=1.38, flux_density_mjy=15.0, flux_error_mjy=0.2, band=SPHERExBand.BAND_2, resolving_power=41),
        SpectralPoint(wavelength_um=2.03, flux_density_mjy=20.0, flux_error_mjy=0.3, band=SPHERExBand.BAND_3, resolving_power=41),
        # Continuum in Band 4: ~25 mJy. At 3.05 um: drop to 10 mJy
        SpectralPoint(wavelength_um=2.60, flux_density_mjy=24.0, flux_error_mjy=0.3, band=SPHERExBand.BAND_4, resolving_power=35),
        SpectralPoint(wavelength_um=3.05, flux_density_mjy=10.0, flux_error_mjy=0.3, band=SPHERExBand.BAND_4, resolving_power=35),
        SpectralPoint(wavelength_um=3.65, flux_density_mjy=26.0, flux_error_mjy=0.4, band=SPHERExBand.BAND_4, resolving_power=35),
        SpectralPoint(wavelength_um=4.12, flux_density_mjy=30.0, flux_error_mjy=0.4, band=SPHERExBand.BAND_5, resolving_power=112),
        SpectralPoint(wavelength_um=4.71, flux_density_mjy=35.0, flux_error_mjy=0.5, band=SPHERExBand.BAND_6, resolving_power=128),
    ]

    h2o_spec = KNOWN_ICE_FEATURES["H2O"]
    feat = SpectralAnalyzer.measure_equivalent_width(spectrum, h2o_spec)

    assert feat.molecule == "H2O"
    assert feat.is_detected is True
    assert feat.detection_significance_sigma >= 3.0
    assert feat.equivalent_width_um > 0.05


def test_ice_flat_continuum_not_detected():
    # Perfectly flat spectrum (no absorption)
    spectrum = [
        SpectralPoint(wavelength_um=0.93, flux_density_mjy=20.0, flux_error_mjy=0.2, band=SPHERExBand.BAND_1, resolving_power=39),
        SpectralPoint(wavelength_um=1.38, flux_density_mjy=20.0, flux_error_mjy=0.2, band=SPHERExBand.BAND_2, resolving_power=41),
        SpectralPoint(wavelength_um=2.03, flux_density_mjy=20.0, flux_error_mjy=0.2, band=SPHERExBand.BAND_3, resolving_power=41),
        SpectralPoint(wavelength_um=2.60, flux_density_mjy=20.0, flux_error_mjy=0.2, band=SPHERExBand.BAND_4, resolving_power=35),
        SpectralPoint(wavelength_um=3.05, flux_density_mjy=20.0, flux_error_mjy=0.2, band=SPHERExBand.BAND_4, resolving_power=35),
        SpectralPoint(wavelength_um=3.65, flux_density_mjy=20.0, flux_error_mjy=0.2, band=SPHERExBand.BAND_4, resolving_power=35),
        SpectralPoint(wavelength_um=4.12, flux_density_mjy=20.0, flux_error_mjy=0.2, band=SPHERExBand.BAND_5, resolving_power=112),
        SpectralPoint(wavelength_um=4.71, flux_density_mjy=20.0, flux_error_mjy=0.2, band=SPHERExBand.BAND_6, resolving_power=128),
    ]

    features = SpectralAnalyzer.analyze_candidate_ices(spectrum)
    for feat in features:
        assert feat.is_detected is False
