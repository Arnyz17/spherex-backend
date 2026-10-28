"""
Temporal Differencing Engine for Astrometry and Photometry.

Computes:
1. Great-circle angular displacement (arcseconds) between multi-epoch observations.
2. Positional uncertainty propagation and statistical significance (sigma).
3. Calibrated magnitude differences and variability significance.
4. Annualized proper motion rates (arcsec/year).
"""

import math
from typing import Tuple, NamedTuple


class DisplacementResult(NamedTuple):
    displacement_arcsec: float
    uncertainty_arcsec: float
    significance_sigma: float
    proper_motion_arcsec_per_year: float
    baseline_days: float


class PhotometricDiffResult(NamedTuple):
    mag_initial: float
    mag_final: float
    delta_mag: float
    delta_mag_uncertainty: float
    significance_sigma: float
    flux_ratio: float


def compute_angular_separation_arcsec(ra1_deg: float, dec1_deg: float, ra2_deg: float, dec2_deg: float) -> float:
    """
    Computes great-circle angular distance between two celestial points using the Haversine formula.
    Returns separation in arcseconds.
    """
    ra1_rad = math.radians(ra1_deg)
    dec1_rad = math.radians(dec1_deg)
    ra2_rad = math.radians(ra2_deg)
    dec2_rad = math.radians(dec2_deg)

    d_ra = ra2_rad - ra1_rad
    d_dec = dec2_rad - dec1_rad

    a = math.sin(d_dec / 2.0) ** 2 + math.cos(dec1_rad) * math.cos(dec2_rad) * math.sin(d_ra / 2.0) ** 2
    # Guard against float numerical overflow beyond 1.0
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.asin(math.sqrt(a))
    
    separation_deg = math.degrees(c)
    return separation_deg * 3600.0


def compute_astrometric_displacement(
    ra1_deg: float,
    dec1_deg: float,
    pos_err1_arcsec: float,
    time1_mjd: float,
    ra2_deg: float,
    dec2_deg: float,
    pos_err2_arcsec: float,
    time2_mjd: float,
) -> DisplacementResult:
    """
    Calculates net angular displacement, propagated uncertainty, significance,
    and annualized proper motion between two observation timestamps.
    """
    displacement_arcsec = compute_angular_separation_arcsec(ra1_deg, dec1_deg, ra2_deg, dec2_deg)
    uncertainty_arcsec = math.sqrt(pos_err1_arcsec**2 + pos_err2_arcsec**2)
    
    if uncertainty_arcsec > 0:
        significance_sigma = displacement_arcsec / uncertainty_arcsec
    else:
        significance_sigma = 0.0

    baseline_days = abs(time2_mjd - time1_mjd)
    if baseline_days > 0.001:
        years = baseline_days / 365.25
        proper_motion_arcsec_per_year = displacement_arcsec / years
    else:
        proper_motion_arcsec_per_year = 0.0

    return DisplacementResult(
        displacement_arcsec=round(displacement_arcsec, 4),
        uncertainty_arcsec=round(uncertainty_arcsec, 4),
        significance_sigma=round(significance_sigma, 2),
        proper_motion_arcsec_per_year=round(proper_motion_arcsec_per_year, 4),
        baseline_days=round(baseline_days, 2),
    )


def flux_mjy_to_ab_mag(flux_mjy: float, flux_err_mjy: float) -> Tuple[float, float]:
    """
    Converts monochromatic flux density in mJy to AB magnitude:
    m_AB = -2.5 * log10(flux_Jy) + 8.90 = -2.5 * log10(flux_mJy) + 16.40
    Uncertainty: sigma_m = (2.5 / ln(10)) * (sigma_F / F) = 1.0857 * (sigma_F / F)
    """
    if flux_mjy <= 0:
        return 99.0, 99.0
    
    mag = -2.5 * math.log10(flux_mjy) + 16.40
    mag_err = 1.08574 * (flux_err_mjy / flux_mjy) if flux_mjy > 0 else 99.0
    return round(mag, 3), round(mag_err, 3)


def compute_photometric_variability(
    flux1_mjy: float,
    flux_err1_mjy: float,
    flux2_mjy: float,
    flux_err2_mjy: float,
) -> PhotometricDiffResult:
    """
    Computes brightness difference (delta magnitude) and statistical variability significance.
    """
    mag1, mag_err1 = flux_mjy_to_ab_mag(flux1_mjy, flux_err1_mjy)
    mag2, mag_err2 = flux_mjy_to_ab_mag(flux2_mjy, flux_err2_mjy)

    delta_mag = mag2 - mag1
    delta_mag_err = math.sqrt(mag_err1**2 + mag_err2**2)
    
    if delta_mag_err > 0:
        significance_sigma = abs(delta_mag) / delta_mag_err
    else:
        significance_sigma = 0.0

    flux_ratio = flux2_mjy / flux1_mjy if flux1_mjy > 0 else 0.0

    return PhotometricDiffResult(
        mag_initial=mag1,
        mag_final=mag2,
        delta_mag=round(delta_mag, 3),
        delta_mag_uncertainty=round(delta_mag_err, 3),
        significance_sigma=round(significance_sigma, 2),
        flux_ratio=round(flux_ratio, 3),
    )
