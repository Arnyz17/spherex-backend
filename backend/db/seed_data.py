"""
SPHEREx Seed Data Generator.

Generates realistic multi-epoch observations and candidates covering:
1. High proper motion nearby stars (astrometric displacement)
2. Photometric transients and pulsating variables (delta magnitude)
3. Interstellar H2O ice absorption sources (Band 4 at ~3.0 um)
4. Circumstellar CO2 ice absorption sources (Band 5 at ~4.27 um)
5. Dense core CO ice absorption sources (Band 6 at ~4.67 um)
6. Quiescent galaxies (stationary SED)
7. Detector artifacts / Cosmic ray spikes (quality bitmask flags)
"""

from datetime import datetime, timezone
from typing import List, Dict, Tuple
import numpy as np
from backend.models.spherex import (
    SPHERExBand,
    SPHEREX_BANDS_METADATA,
    ObservationRecord,
    WCSMetadata,
    SourceMeasurement,
    QualityFlagBitmask,
    decode_quality_flags,
)
from backend.models.candidates import (
    CandidateDetail,
    SpectralPoint,
    EpochMeasurement,
    ValidationStatus,
    ScientificCategory,
)
from backend.services.differencing import (
    compute_astrometric_displacement,
    compute_photometric_variability,
    flux_mjy_to_ab_mag,
)
from backend.services.spectral_ice import SpectralAnalyzer
from backend.services.classifier import ScientificClassifier
from backend.services.cutout_generator import CutoutGenerator


def generate_seed_catalog() -> Tuple[List[ObservationRecord], List[CandidateDetail]]:
    """
    Constructs a scientifically rich catalog of SPHEREx observations and candidates.
    Returns:
        (observations_list, candidates_list)
    """
    candidates: List[CandidateDetail] = []
    observations: List[ObservationRecord] = []

    # Epoch 1: 2025-04-15 (Approx 1 month post-launch survey start)
    # Epoch 2: 2025-10-20 (~6 month baseline all-sky revisit)
    t1_dt = datetime(2025, 4, 15, 8, 30, 0, tzinfo=timezone.utc)
    t2_dt = datetime(2025, 10, 20, 14, 45, 0, tzinfo=timezone.utc)
    t1_mjd = 60780.354
    t2_mjd = 60968.615

    # -------------------------------------------------------------
    # 1. Candidate SPX-J1802-2341: High Proper Motion Nearby Star
    # -------------------------------------------------------------
    ra1_hpm = 270.54125
    dec1_hpm = -23.68910
    # True displacement ~0.48 arcsec over 0.516 years (mu ~ 0.93 arcsec/yr)
    d_ra_deg = (0.42 / 3600.0) / np.cos(np.radians(dec1_hpm))
    d_dec_deg = -0.23 / 3600.0
    ra2_hpm = ra1_hpm + d_ra_deg
    dec2_hpm = dec1_hpm + d_dec_deg

    hpm_flux1 = 45.2  # mJy
    hpm_flux2 = 44.8  # mJy
    pos_err = 0.05    # arcsec
    flux_err = 0.9    # mJy

    astro_hpm = compute_astrometric_displacement(
        ra1_hpm, dec1_hpm, pos_err, t1_mjd,
        ra2_hpm, dec2_hpm, pos_err, t2_mjd,
    )
    photo_hpm = compute_photometric_variability(hpm_flux1, flux_err, hpm_flux2, flux_err)

    # 6-Band SED (M-Dwarf continuum falling in longer NIR)
    hpm_spectrum = [
        SpectralPoint(wavelength_um=0.93, flux_density_mjy=42.0, flux_error_mjy=1.0, band=SPHERExBand.BAND_1, resolving_power=39),
        SpectralPoint(wavelength_um=1.38, flux_density_mjy=48.5, flux_error_mjy=1.1, band=SPHERExBand.BAND_2, resolving_power=41),
        SpectralPoint(wavelength_um=2.03, flux_density_mjy=45.2, flux_error_mjy=0.9, band=SPHERExBand.BAND_3, resolving_power=41),
        SpectralPoint(wavelength_um=3.12, flux_density_mjy=32.1, flux_error_mjy=0.8, band=SPHERExBand.BAND_4, resolving_power=35),
        SpectralPoint(wavelength_um=4.12, flux_density_mjy=24.5, flux_error_mjy=0.7, band=SPHERExBand.BAND_5, resolving_power=112),
        SpectralPoint(wavelength_um=4.71, flux_density_mjy=18.0, flux_error_mjy=0.6, band=SPHERExBand.BAND_6, resolving_power=128),
    ]
    hpm_ices = SpectralAnalyzer.analyze_candidate_ices(hpm_spectrum)
    cat_hpm, summ_hpm, val_hpm, warn_hpm = ScientificClassifier.classify(
        astro_hpm.displacement_arcsec, astro_hpm.significance_sigma,
        photo_hpm.delta_mag, photo_hpm.significance_sigma,
        hpm_ices, QualityFlagBitmask.CLEAN
    )

    cutout_e1 = CutoutGenerator.array_to_base64_png(CutoutGenerator.generate_point_source_array(center_offset_x=-2.0, center_offset_y=1.0, peak_flux=140))
    cutout_e2 = CutoutGenerator.array_to_base64_png(CutoutGenerator.generate_point_source_array(center_offset_x=2.2, center_offset_y=-1.2, peak_flux=138))

    cand_hpm = CandidateDetail(
        candidate_id="SPX-J1802-2341",
        ra=round(ra1_hpm, 5),
        dec=round(dec1_hpm, 5),
        observation_dates=[t1_dt, t2_dt],
        bands_observed=list(SPHERExBand),
        displacement_arcsec=astro_hpm.displacement_arcsec,
        displacement_uncertainty_arcsec=astro_hpm.uncertainty_arcsec,
        displacement_significance_sigma=astro_hpm.significance_sigma,
        delta_brightness_mag=photo_hpm.delta_mag,
        delta_brightness_uncertainty_mag=photo_hpm.delta_mag_uncertainty,
        delta_brightness_significance_sigma=photo_hpm.significance_sigma,
        quality_indicators=decode_quality_flags(QualityFlagBitmask.CLEAN),
        has_quality_warnings=warn_hpm,
        scientific_interpretation=cat_hpm,
        scientific_summary=summ_hpm,
        validation_status=val_hpm,
        epochs=[
            EpochMeasurement(
                epoch_index=0,
                observation_id="OBS-SPX-20250415-0012",
                timestamp_utc=t1_dt,
                timestamp_mjd=t1_mjd,
                band=SPHERExBand.BAND_3,
                ra=ra1_hpm,
                dec=dec1_hpm,
                flux_density_mjy=hpm_flux1,
                flux_density_err_mjy=flux_err,
                magnitude=photo_hpm.mag_initial,
                magnitude_err=0.02,
                quality_flags=["clean"],
            ),
            EpochMeasurement(
                epoch_index=1,
                observation_id="OBS-SPX-20251020-0089",
                timestamp_utc=t2_dt,
                timestamp_mjd=t2_mjd,
                band=SPHERExBand.BAND_3,
                ra=ra2_hpm,
                dec=dec2_hpm,
                flux_density_mjy=hpm_flux2,
                flux_density_err_mjy=flux_err,
                magnitude=photo_hpm.mag_final,
                magnitude_err=0.02,
                quality_flags=["clean"],
            ),
        ],
        spectrum=hpm_spectrum,
        ice_features=hpm_ices,
        cutout_thumbnails={"epoch_1": cutout_e1, "epoch_2": cutout_e2},
        user_notes="Astrometric trajectory verified. Matches high proper motion red dwarf in Southern sky.",
    )
    candidates.append(cand_hpm)

    # -------------------------------------------------------------
    # 2. Candidate SPX-J0439+2545: Interstellar Water-Ice (H2O) Cloud
    # -------------------------------------------------------------
    ra_ice = 69.82410
    dec_ice = 25.75330
    ice_flux = 22.0
    astro_ice = compute_astrometric_displacement(ra_ice, dec_ice, 0.06, t1_mjd, ra_ice + 0.000003, dec_ice - 0.000002, 0.06, t2_mjd)
    photo_ice = compute_photometric_variability(ice_flux, 0.5, ice_flux + 0.3, 0.5)

    # 6-Band Spectrum with deep 3.0 um H2O ice absorption dip
    # Continuum is rising toward longer wavelengths (typical embedded YSO), but Band 4 has a strong drop
    h2o_spectrum = [
        SpectralPoint(wavelength_um=0.93, flux_density_mjy=5.2, flux_error_mjy=0.4, band=SPHERExBand.BAND_1, resolving_power=39),
        SpectralPoint(wavelength_um=1.38, flux_density_mjy=9.8, flux_error_mjy=0.5, band=SPHERExBand.BAND_2, resolving_power=41),
        SpectralPoint(wavelength_um=2.03, flux_density_mjy=18.4, flux_error_mjy=0.6, band=SPHERExBand.BAND_3, resolving_power=41),
        # Continuum in Band 4 would be ~28 mJy, but deep H2O ice absorption brings it to 14.2 mJy
        SpectralPoint(wavelength_um=2.65, flux_density_mjy=26.0, flux_error_mjy=0.8, band=SPHERExBand.BAND_4, resolving_power=35),
        SpectralPoint(wavelength_um=3.05, flux_density_mjy=14.2, flux_error_mjy=0.6, band=SPHERExBand.BAND_4, resolving_power=35),
        SpectralPoint(wavelength_um=3.60, flux_density_mjy=31.5, flux_error_mjy=0.9, band=SPHERExBand.BAND_4, resolving_power=35),
        SpectralPoint(wavelength_um=4.12, flux_density_mjy=38.0, flux_error_mjy=1.0, band=SPHERExBand.BAND_5, resolving_power=112),
        SpectralPoint(wavelength_um=4.71, flux_density_mjy=44.2, flux_error_mjy=1.1, band=SPHERExBand.BAND_6, resolving_power=128),
    ]
    h2o_ices = SpectralAnalyzer.analyze_candidate_ices(h2o_spectrum)
    cat_ice, summ_ice, val_ice, warn_ice = ScientificClassifier.classify(
        astro_ice.displacement_arcsec, astro_ice.significance_sigma,
        photo_ice.delta_mag, photo_ice.significance_sigma,
        h2o_ices, QualityFlagBitmask.CLEAN
    )

    cutout_ice1 = CutoutGenerator.array_to_base64_png(CutoutGenerator.generate_point_source_array(center_offset_x=0.0, center_offset_y=0.0, peak_flux=110, fwhm_px=3.2))
    cutout_ice2 = CutoutGenerator.array_to_base64_png(CutoutGenerator.generate_point_source_array(center_offset_x=0.0, center_offset_y=0.0, peak_flux=112, fwhm_px=3.2))

    cand_ice = CandidateDetail(
        candidate_id="SPX-J0439+2545",
        ra=round(ra_ice, 5),
        dec=round(dec_ice, 5),
        observation_dates=[t1_dt, t2_dt],
        bands_observed=list(SPHERExBand),
        displacement_arcsec=astro_ice.displacement_arcsec,
        displacement_uncertainty_arcsec=astro_ice.uncertainty_arcsec,
        displacement_significance_sigma=astro_ice.significance_sigma,
        delta_brightness_mag=photo_ice.delta_mag,
        delta_brightness_uncertainty_mag=photo_ice.delta_mag_uncertainty,
        delta_brightness_significance_sigma=photo_ice.significance_sigma,
        quality_indicators=["nominal", "high_snr"],
        has_quality_warnings=warn_ice,
        scientific_interpretation=cat_ice,
        scientific_summary=summ_ice,
        validation_status=ValidationStatus.CONFIRMED,
        epochs=[
            EpochMeasurement(
                epoch_index=0,
                observation_id="OBS-SPX-20250415-0044",
                timestamp_utc=t1_dt,
                timestamp_mjd=t1_mjd,
                band=SPHERExBand.BAND_4,
                ra=ra_ice,
                dec=dec_ice,
                flux_density_mjy=ice_flux,
                flux_density_err_mjy=0.5,
                magnitude=photo_ice.mag_initial,
                magnitude_err=0.025,
                quality_flags=["clean"],
            ),
            EpochMeasurement(
                epoch_index=1,
                observation_id="OBS-SPX-20251020-0112",
                timestamp_utc=t2_dt,
                timestamp_mjd=t2_mjd,
                band=SPHERExBand.BAND_4,
                ra=ra_ice,
                dec=dec_ice,
                flux_density_mjy=ice_flux + 0.3,
                flux_density_err_mjy=0.5,
                magnitude=photo_ice.mag_final,
                magnitude_err=0.025,
                quality_flags=["clean"],
            ),
        ],
        spectrum=h2o_spectrum,
        ice_features=h2o_ices,
        cutout_thumbnails={"epoch_1": cutout_ice1, "epoch_2": cutout_ice2},
        user_notes="Exceptional water-ice absorption profile in Taurus dark cloud core.",
    )
    candidates.append(cand_ice)

    # -------------------------------------------------------------
    # 3. Candidate SPX-J1627-2430: Carbon Dioxide Ice (CO2) in Band 5
    # -------------------------------------------------------------
    ra_co2 = 246.81230
    dec_co2 = -24.50890
    astro_co2 = compute_astrometric_displacement(ra_co2, dec_co2, 0.05, t1_mjd, ra_co2, dec_co2, 0.05, t2_mjd)
    photo_co2 = compute_photometric_variability(15.0, 0.4, 15.1, 0.4)

    co2_spectrum = [
        SpectralPoint(wavelength_um=0.93, flux_density_mjy=2.1, flux_error_mjy=0.2, band=SPHERExBand.BAND_1, resolving_power=39),
        SpectralPoint(wavelength_um=1.38, flux_density_mjy=4.5, flux_error_mjy=0.3, band=SPHERExBand.BAND_2, resolving_power=41),
        SpectralPoint(wavelength_um=2.03, flux_density_mjy=8.9, flux_error_mjy=0.4, band=SPHERExBand.BAND_3, resolving_power=41),
        SpectralPoint(wavelength_um=3.12, flux_density_mjy=14.0, flux_error_mjy=0.5, band=SPHERExBand.BAND_4, resolving_power=35),
        # Band 5 has high resolution R=112: continuum is ~18 mJy, sharp drop at 4.27 um
        SpectralPoint(wavelength_um=4.05, flux_density_mjy=17.8, flux_error_mjy=0.5, band=SPHERExBand.BAND_5, resolving_power=112),
        SpectralPoint(wavelength_um=4.27, flux_density_mjy=10.2, flux_error_mjy=0.4, band=SPHERExBand.BAND_5, resolving_power=112),
        SpectralPoint(wavelength_um=4.38, flux_density_mjy=19.1, flux_error_mjy=0.5, band=SPHERExBand.BAND_5, resolving_power=112),
        SpectralPoint(wavelength_um=4.71, flux_density_mjy=21.4, flux_error_mjy=0.6, band=SPHERExBand.BAND_6, resolving_power=128),
    ]
    co2_ices = SpectralAnalyzer.analyze_candidate_ices(co2_spectrum)
    cat_co2, summ_co2, val_co2, warn_co2 = ScientificClassifier.classify(
        astro_co2.displacement_arcsec, astro_co2.significance_sigma,
        photo_co2.delta_mag, photo_co2.significance_sigma,
        co2_ices, QualityFlagBitmask.CLEAN
    )

    cutout_co2_1 = CutoutGenerator.array_to_base64_png(CutoutGenerator.generate_point_source_array(peak_flux=85))
    cutout_co2_2 = CutoutGenerator.array_to_base64_png(CutoutGenerator.generate_point_source_array(peak_flux=87))

    cand_co2 = CandidateDetail(
        candidate_id="SPX-J1627-2430",
        ra=round(ra_co2, 5),
        dec=round(dec_co2, 5),
        observation_dates=[t1_dt, t2_dt],
        bands_observed=list(SPHERExBand),
        displacement_arcsec=astro_co2.displacement_arcsec,
        displacement_uncertainty_arcsec=astro_co2.uncertainty_arcsec,
        displacement_significance_sigma=astro_co2.significance_sigma,
        delta_brightness_mag=photo_co2.delta_mag,
        delta_brightness_uncertainty_mag=photo_co2.delta_mag_uncertainty,
        delta_brightness_significance_sigma=photo_co2.significance_sigma,
        quality_indicators=["nominal"],
        has_quality_warnings=warn_co2,
        scientific_interpretation=cat_co2,
        scientific_summary=summ_co2,
        validation_status=val_co2,
        epochs=[],
        spectrum=co2_spectrum,
        ice_features=co2_ices,
        cutout_thumbnails={"epoch_1": cutout_co2_1, "epoch_2": cutout_co2_2},
        user_notes="Circumstellar disk target exhibiting sharp CO2 ice absorption at 4.27 um.",
    )
    candidates.append(cand_co2)

    # -------------------------------------------------------------
    # 4. Candidate SPX-J1215+3012: Photometric Transient / Supernova
    # -------------------------------------------------------------
    ra_trans = 183.92150
    dec_trans = 30.21440
    flux_trans1 = 2.1   # Pre-outburst faint state (mag ~ 17.2)
    flux_trans2 = 35.8  # Post-outburst bright transient (mag ~ 14.1, delta_mag ~ -3.1)
    astro_trans = compute_astrometric_displacement(ra_trans, dec_trans, 0.08, t1_mjd, ra_trans, dec_trans, 0.04, t2_mjd)
    photo_trans = compute_photometric_variability(flux_trans1, 0.3, flux_trans2, 0.8)

    trans_spectrum = [
        SpectralPoint(wavelength_um=0.93, flux_density_mjy=48.0, flux_error_mjy=1.2, band=SPHERExBand.BAND_1, resolving_power=39),
        SpectralPoint(wavelength_um=1.38, flux_density_mjy=42.0, flux_error_mjy=1.0, band=SPHERExBand.BAND_2, resolving_power=41),
        SpectralPoint(wavelength_um=2.03, flux_density_mjy=35.8, flux_error_mjy=0.8, band=SPHERExBand.BAND_3, resolving_power=41),
        SpectralPoint(wavelength_um=3.12, flux_density_mjy=26.4, flux_error_mjy=0.7, band=SPHERExBand.BAND_4, resolving_power=35),
        SpectralPoint(wavelength_um=4.12, flux_density_mjy=19.1, flux_error_mjy=0.6, band=SPHERExBand.BAND_5, resolving_power=112),
        SpectralPoint(wavelength_um=4.71, flux_density_mjy=14.5, flux_error_mjy=0.5, band=SPHERExBand.BAND_6, resolving_power=128),
    ]
    trans_ices = SpectralAnalyzer.analyze_candidate_ices(trans_spectrum)
    cat_trans, summ_trans, val_trans, warn_trans = ScientificClassifier.classify(
        astro_trans.displacement_arcsec, astro_trans.significance_sigma,
        photo_trans.delta_mag, photo_trans.significance_sigma,
        trans_ices, QualityFlagBitmask.CLEAN
    )

    cutout_tr1 = CutoutGenerator.array_to_base64_png(CutoutGenerator.generate_point_source_array(peak_flux=15, bg_sigma=2.5))
    cutout_tr2 = CutoutGenerator.array_to_base64_png(CutoutGenerator.generate_point_source_array(peak_flux=220, bg_sigma=2.5))

    cand_trans = CandidateDetail(
        candidate_id="SPX-J1215+3012",
        ra=round(ra_trans, 5),
        dec=round(dec_trans, 5),
        observation_dates=[t1_dt, t2_dt],
        bands_observed=list(SPHERExBand),
        displacement_arcsec=astro_trans.displacement_arcsec,
        displacement_uncertainty_arcsec=astro_trans.uncertainty_arcsec,
        displacement_significance_sigma=astro_trans.significance_sigma,
        delta_brightness_mag=photo_trans.delta_mag,
        delta_brightness_uncertainty_mag=photo_trans.delta_mag_uncertainty,
        delta_brightness_significance_sigma=photo_trans.significance_sigma,
        quality_indicators=["nominal", "high_variability"],
        has_quality_warnings=warn_trans,
        scientific_interpretation=cat_trans,
        scientific_summary=summ_trans,
        validation_status=ValidationStatus.CONFIRMED,
        epochs=[],
        spectrum=trans_spectrum,
        ice_features=trans_ices,
        cutout_thumbnails={"epoch_1": cutout_tr1, "epoch_2": cutout_tr2},
        user_notes="Spectacular 3.08-magnitude brightening between April and October 2025. Host galaxy visible in background.",
    )
    candidates.append(cand_trans)

    # -------------------------------------------------------------
    # 5. Candidate SPX-J2140-1502: Carbon Monoxide Ice (CO) in Band 6
    # -------------------------------------------------------------
    ra_co = 325.04500
    dec_co = -15.03450
    astro_co = compute_astrometric_displacement(ra_co, dec_co, 0.04, t1_mjd, ra_co, dec_co, 0.04, t2_mjd)
    photo_co = compute_photometric_variability(12.5, 0.3, 12.6, 0.3)

    co_spectrum = [
        SpectralPoint(wavelength_um=0.93, flux_density_mjy=1.5, flux_error_mjy=0.2, band=SPHERExBand.BAND_1, resolving_power=39),
        SpectralPoint(wavelength_um=1.38, flux_density_mjy=3.2, flux_error_mjy=0.2, band=SPHERExBand.BAND_2, resolving_power=41),
        SpectralPoint(wavelength_um=2.03, flux_density_mjy=6.4, flux_error_mjy=0.3, band=SPHERExBand.BAND_3, resolving_power=41),
        SpectralPoint(wavelength_um=3.12, flux_density_mjy=9.8, flux_error_mjy=0.4, band=SPHERExBand.BAND_4, resolving_power=35),
        SpectralPoint(wavelength_um=4.12, flux_density_mjy=14.2, flux_error_mjy=0.4, band=SPHERExBand.BAND_5, resolving_power=112),
        # Band 6 has highest nominal resolving power R=128: narrow CO feature at 4.67 um
        SpectralPoint(wavelength_um=4.52, flux_density_mjy=17.5, flux_error_mjy=0.4, band=SPHERExBand.BAND_6, resolving_power=128),
        SpectralPoint(wavelength_um=4.67, flux_density_mjy=11.8, flux_error_mjy=0.3, band=SPHERExBand.BAND_6, resolving_power=128),
        SpectralPoint(wavelength_um=4.82, flux_density_mjy=18.4, flux_error_mjy=0.4, band=SPHERExBand.BAND_6, resolving_power=128),
    ]
    co_ices = SpectralAnalyzer.analyze_candidate_ices(co_spectrum)
    cat_co, summ_co, val_co, warn_co = ScientificClassifier.classify(
        astro_co.displacement_arcsec, astro_co.significance_sigma,
        photo_co.delta_mag, photo_co.significance_sigma,
        co_ices, QualityFlagBitmask.CLEAN
    )

    cand_co = CandidateDetail(
        candidate_id="SPX-J2140-1502",
        ra=round(ra_co, 5),
        dec=round(dec_co, 5),
        observation_dates=[t1_dt, t2_dt],
        bands_observed=list(SPHERExBand),
        displacement_arcsec=astro_co.displacement_arcsec,
        displacement_uncertainty_arcsec=astro_co.uncertainty_arcsec,
        displacement_significance_sigma=astro_co.significance_sigma,
        delta_brightness_mag=photo_co.delta_mag,
        delta_brightness_uncertainty_mag=photo_co.delta_mag_uncertainty,
        delta_brightness_significance_sigma=photo_co.significance_sigma,
        quality_indicators=["nominal"],
        has_quality_warnings=warn_co,
        scientific_interpretation=cat_co,
        scientific_summary=summ_co,
        validation_status=val_co,
        epochs=[],
        spectrum=co_spectrum,
        ice_features=co_ices,
        cutout_thumbnails={
            "epoch_1": CutoutGenerator.array_to_base64_png(CutoutGenerator.generate_point_source_array(peak_flux=70)),
            "epoch_2": CutoutGenerator.array_to_base64_png(CutoutGenerator.generate_point_source_array(peak_flux=71)),
        },
        user_notes="Dense molecular cloud core candidate showing clean CO ice band at 4.67 um (R=128 channel).",
    )
    candidates.append(cand_co)

    # -------------------------------------------------------------
    # 6. Candidate SPX-J0911+4511: Detector Artifact / Cosmic Ray
    # -------------------------------------------------------------
    ra_art = 137.89200
    dec_art = 45.19500
    astro_art = compute_astrometric_displacement(ra_art, dec_art, 0.20, t1_mjd, ra_art + 0.0003, dec_art - 0.0004, 0.20, t2_mjd)
    photo_art = compute_photometric_variability(95.0, 5.0, 0.4, 0.5)

    art_spectrum = [
        SpectralPoint(wavelength_um=0.93, flux_density_mjy=0.4, flux_error_mjy=0.2, band=SPHERExBand.BAND_1, resolving_power=39),
        SpectralPoint(wavelength_um=1.38, flux_density_mjy=95.0, flux_error_mjy=5.0, band=SPHERExBand.BAND_2, resolving_power=41),
        SpectralPoint(wavelength_um=2.03, flux_density_mjy=0.3, flux_error_mjy=0.2, band=SPHERExBand.BAND_3, resolving_power=41),
        SpectralPoint(wavelength_um=3.12, flux_density_mjy=0.2, flux_error_mjy=0.2, band=SPHERExBand.BAND_4, resolving_power=35),
        SpectralPoint(wavelength_um=4.12, flux_density_mjy=0.1, flux_error_mjy=0.2, band=SPHERExBand.BAND_5, resolving_power=112),
        SpectralPoint(wavelength_um=4.71, flux_density_mjy=0.2, flux_error_mjy=0.2, band=SPHERExBand.BAND_6, resolving_power=128),
    ]
    art_ices = SpectralAnalyzer.analyze_candidate_ices(art_spectrum)
    cat_art, summ_art, val_art, warn_art = ScientificClassifier.classify(
        astro_art.displacement_arcsec, astro_art.significance_sigma,
        photo_art.delta_mag, photo_art.significance_sigma,
        art_ices, QualityFlagBitmask.COSMIC_RAY | QualityFlagBitmask.BAD_PIXEL
    )

    cand_art = CandidateDetail(
        candidate_id="SPX-J0911+4511",
        ra=round(ra_art, 5),
        dec=round(dec_art, 5),
        observation_dates=[t1_dt, t2_dt],
        bands_observed=[SPHERExBand.BAND_2],
        displacement_arcsec=astro_art.displacement_arcsec,
        displacement_uncertainty_arcsec=astro_art.uncertainty_arcsec,
        displacement_significance_sigma=astro_art.significance_sigma,
        delta_brightness_mag=photo_art.delta_mag,
        delta_brightness_uncertainty_mag=photo_art.delta_mag_uncertainty,
        delta_brightness_significance_sigma=photo_art.significance_sigma,
        quality_indicators=decode_quality_flags(QualityFlagBitmask.COSMIC_RAY | QualityFlagBitmask.BAD_PIXEL),
        has_quality_warnings=True,
        scientific_interpretation=cat_art,
        scientific_summary=summ_art,
        validation_status=val_art,
        epochs=[],
        spectrum=art_spectrum,
        ice_features=art_ices,
        cutout_thumbnails={
            "epoch_1": CutoutGenerator.array_to_base64_png(CutoutGenerator.generate_point_source_array(peak_flux=180, cosmic_ray=True)),
            "epoch_2": CutoutGenerator.array_to_base64_png(CutoutGenerator.generate_point_source_array(peak_flux=0, bg_sigma=2.0)),
        },
        user_notes="Single-frame cosmic ray strike flagged by detector centroid sharpness filter.",
    )
    candidates.append(cand_art)

    # -------------------------------------------------------------
    # 7. Candidate SPX-J0332-2748: Quiescent Distant Galaxy SED
    # -------------------------------------------------------------
    ra_gal = 53.11670
    dec_gal = -27.80800
    astro_gal = compute_astrometric_displacement(ra_gal, dec_gal, 0.05, t1_mjd, ra_gal, dec_gal, 0.05, t2_mjd)
    photo_gal = compute_photometric_variability(8.5, 0.3, 8.6, 0.3)

    gal_spectrum = [
        SpectralPoint(wavelength_um=0.93, flux_density_mjy=4.1, flux_error_mjy=0.2, band=SPHERExBand.BAND_1, resolving_power=39),
        SpectralPoint(wavelength_um=1.38, flux_density_mjy=6.5, flux_error_mjy=0.3, band=SPHERExBand.BAND_2, resolving_power=41),
        SpectralPoint(wavelength_um=2.03, flux_density_mjy=8.5, flux_error_mjy=0.3, band=SPHERExBand.BAND_3, resolving_power=41),
        SpectralPoint(wavelength_um=3.12, flux_density_mjy=7.8, flux_error_mjy=0.3, band=SPHERExBand.BAND_4, resolving_power=35),
        SpectralPoint(wavelength_um=4.12, flux_density_mjy=6.2, flux_error_mjy=0.3, band=SPHERExBand.BAND_5, resolving_power=112),
        SpectralPoint(wavelength_um=4.71, flux_density_mjy=5.4, flux_error_mjy=0.3, band=SPHERExBand.BAND_6, resolving_power=128),
    ]
    gal_ices = SpectralAnalyzer.analyze_candidate_ices(gal_spectrum)
    cat_gal, summ_gal, val_gal, warn_gal = ScientificClassifier.classify(
        astro_gal.displacement_arcsec, astro_gal.significance_sigma,
        photo_gal.delta_mag, photo_gal.significance_sigma,
        gal_ices, QualityFlagBitmask.CLEAN
    )

    cand_gal = CandidateDetail(
        candidate_id="SPX-J0332-2748",
        ra=round(ra_gal, 5),
        dec=round(dec_gal, 5),
        observation_dates=[t1_dt, t2_dt],
        bands_observed=list(SPHERExBand),
        displacement_arcsec=astro_gal.displacement_arcsec,
        displacement_uncertainty_arcsec=astro_gal.uncertainty_arcsec,
        displacement_significance_sigma=astro_gal.significance_sigma,
        delta_brightness_mag=photo_gal.delta_mag,
        delta_brightness_uncertainty_mag=photo_gal.delta_mag_uncertainty,
        delta_brightness_significance_sigma=photo_gal.significance_sigma,
        quality_indicators=["nominal", "clean"],
        has_quality_warnings=warn_gal,
        scientific_interpretation=cat_gal,
        scientific_summary=summ_gal,
        validation_status=val_gal,
        epochs=[],
        spectrum=gal_spectrum,
        ice_features=gal_ices,
        cutout_thumbnails={
            "epoch_1": CutoutGenerator.array_to_base64_png(CutoutGenerator.generate_point_source_array(peak_flux=45, fwhm_px=4.5)),
            "epoch_2": CutoutGenerator.array_to_base64_png(CutoutGenerator.generate_point_source_array(peak_flux=46, fwhm_px=4.5)),
        },
        user_notes="Extended galaxy in Chandra Deep Field South. Stable photometric reference baseline.",
    )
    candidates.append(cand_gal)

    # -------------------------------------------------------------
    # Build Observation Records for Ingestion Layer
    # -------------------------------------------------------------
    for cand in candidates:
        obs1 = ObservationRecord(
            observation_id=f"OBS-SPX-E1-{cand.candidate_id}",
            timestamp_utc=t1_dt,
            timestamp_mjd=t1_mjd,
            band=cand.bands_observed[0] if cand.bands_observed else SPHERExBand.BAND_1,
            wavelength_center_um=SPHEREX_BANDS_METADATA[cand.bands_observed[0]].wavelength_center_um if cand.bands_observed else 1.0,
            exposure_time_sec=120.0,
            wcs=WCSMetadata(
                crval1=cand.ra,
                crval2=cand.dec,
                crpix1=1024.0,
                crpix2=1024.0,
                cdelt1=-0.00172,  # ~6.2 arcsec/pixel
                cdelt2=0.00172,
            ),
            quality_flags=QualityFlagBitmask.CLEAN if not cand.has_quality_warnings else QualityFlagBitmask.COSMIC_RAY,
            zeropoint_mag=24.5,
            background_rms=0.15,
            sources=[
                SourceMeasurement(
                    source_id=f"SRC-E1-{cand.candidate_id}",
                    pixel_x=1024.0,
                    pixel_y=1024.0,
                    ra_deg=cand.ra,
                    dec_deg=cand.dec,
                    positional_uncertainty_arcsec=cand.displacement_uncertainty_arcsec,
                    flux_density_mjy=cand.spectrum[0].flux_density_mjy if cand.spectrum else 10.0,
                    flux_uncertainty_mjy=0.5,
                    snr=25.0,
                    quality_flags=0,
                )
            ],
            image_uri=f"fits://spherex/level2/20250415/{cand.candidate_id}_e1.fits",
        )
        observations.append(obs1)

    return observations, candidates
