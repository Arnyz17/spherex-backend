"""Unit tests for Astrometric and Photometric Differencing Engine."""

import math
import pytest
from backend.services.differencing import (
    compute_angular_separation_arcsec,
    compute_astrometric_displacement,
    compute_photometric_variability,
    flux_mjy_to_ab_mag,
)


def test_angular_separation_zero():
    sep = compute_angular_separation_arcsec(180.0, 45.0, 180.0, 45.0)
    assert sep == 0.0


def test_angular_separation_known():
    # 1 degree in Dec is exactly 3600 arcseconds
    sep = compute_angular_separation_arcsec(0.0, 0.0, 0.0, 1.0)
    assert abs(sep - 3600.0) < 0.1


def test_astrometric_displacement_significance():
    # 0.5 arcsec shift with 0.05 arcsec errors -> sqrt(0.05^2 + 0.05^2) = 0.0707 -> sigma ~ 7.07
    result = compute_astrometric_displacement(
        ra1_deg=100.0,
        dec1_deg=20.0,
        pos_err1_arcsec=0.05,
        time1_mjd=60000.0,
        ra2_deg=100.0 + (0.5 / 3600.0) / math.cos(math.radians(20.0)),
        dec2_deg=20.0,
        pos_err2_arcsec=0.05,
        time2_mjd=60365.25,
    )
    assert result.displacement_arcsec > 0.45
    assert result.significance_sigma >= 6.5
    assert result.proper_motion_arcsec_per_year > 0.45


def test_photometric_variability():
    # Factor of 2.512 brightness decrease is ~1.0 magnitude fainter
    res = compute_photometric_variability(
        flux1_mjy=10.0,
        flux_err1_mjy=0.2,
        flux2_mjy=3.98,
        flux_err2_mjy=0.2,
    )
    assert abs(res.delta_mag - 1.0) < 0.05
    assert res.significance_sigma > 10.0
