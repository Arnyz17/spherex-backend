"""
In-Memory Spatial Data Repository for SPHEREx Observations and Candidates.

Provides thread-safe persistence, filtering, cone search, and triage status updates.
"""

import threading
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timezone
from backend.models.spherex import ObservationRecord, SPHERExBand
from backend.models.candidates import (
    CandidateDetail,
    CandidateSummary,
    ValidationStatus,
    ScientificCategory,
)
from backend.services.differencing import compute_angular_separation_arcsec
from backend.db.seed_data import generate_seed_catalog


class SPHERExRepository:
    """Thread-safe catalog repository with astronomical spatial filtering."""

    def __init__(self):
        self._lock = threading.RLock()
        self._observations: Dict[str, ObservationRecord] = {}
        self._candidates: Dict[str, CandidateDetail] = {}
        self._init_seed_data()

    def _init_seed_data(self):
        """Loads default high-fidelity SPHEREx observation and candidate catalog."""
        obs_list, cand_list = generate_seed_catalog()
        for obs in obs_list:
            self._observations[obs.observation_id] = obs
        for cand in cand_list:
            self._candidates[cand.candidate_id] = cand

    # -------------------------------------------------------------
    # Candidate Query & Mutation Operations
    # -------------------------------------------------------------
    def list_candidates(
        self,
        min_displacement_sigma: Optional[float] = None,
        min_delta_mag: Optional[float] = None,
        ice_molecule: Optional[str] = None,
        validation_status: Optional[ValidationStatus] = None,
        category: Optional[ScientificCategory] = None,
        ra_deg: Optional[float] = None,
        dec_deg: Optional[float] = None,
        radius_arcmin: Optional[float] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[CandidateSummary], int]:
        """
        Queries and filters candidate catalog with pagination.
        Returns:
            (filtered_candidate_summaries, total_count)
        """
        with self._lock:
            results: List[CandidateDetail] = list(self._candidates.values())

            # 1. Filter by astrometric displacement significance
            if min_displacement_sigma is not None:
                results = [c for c in results if c.displacement_significance_sigma >= min_displacement_sigma]

            # 2. Filter by minimum photometric variability
            if min_delta_mag is not None:
                results = [c for c in results if abs(c.delta_brightness_mag) >= min_delta_mag]

            # 3. Filter by molecular ice absorption feature (H2O, CO2, CO)
            if ice_molecule:
                target_mol = ice_molecule.upper().strip()
                results = [
                    c for c in results
                    if any(feat.molecule == target_mol and feat.is_detected for feat in c.ice_features)
                ]

            # 4. Filter by validation status
            if validation_status:
                results = [c for c in results if c.validation_status == validation_status]

            # 5. Filter by scientific category
            if category:
                results = [c for c in results if c.scientific_interpretation == category]

            # 6. Spatial cone search
            if ra_deg is not None and dec_deg is not None and radius_arcmin is not None:
                radius_arcsec = radius_arcmin * 60.0
                results = [
                    c for c in results
                    if compute_angular_separation_arcsec(ra_deg, dec_deg, c.ra, c.dec) <= radius_arcsec
                ]

            total_count = len(results)

            # Pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated = results[start_idx:end_idx]

            # Project to CandidateSummary for frontend efficiency
            summaries = [
                CandidateSummary(
                    candidate_id=c.candidate_id,
                    ra=c.ra,
                    dec=c.dec,
                    observation_dates=c.observation_dates,
                    bands_observed=c.bands_observed,
                    displacement_arcsec=c.displacement_arcsec,
                    displacement_uncertainty_arcsec=c.displacement_uncertainty_arcsec,
                    displacement_significance_sigma=c.displacement_significance_sigma,
                    delta_brightness_mag=c.delta_brightness_mag,
                    delta_brightness_uncertainty_mag=c.delta_brightness_uncertainty_mag,
                    delta_brightness_significance_sigma=c.delta_brightness_significance_sigma,
                    quality_indicators=c.quality_indicators,
                    has_quality_warnings=c.has_quality_warnings,
                    scientific_interpretation=c.scientific_interpretation,
                    scientific_summary=c.scientific_summary,
                    validation_status=c.validation_status,
                )
                for c in paginated
            ]

            return summaries, total_count

    def get_candidate(self, candidate_id: str) -> Optional[CandidateDetail]:
        """Retrieves full candidate detail including spectrum, cutouts, and history."""
        with self._lock:
            return self._candidates.get(candidate_id)

    def update_validation(
        self, candidate_id: str, new_status: ValidationStatus, notes: Optional[str] = None
    ) -> Optional[CandidateDetail]:
        """Updates triage status and scientist notes for a candidate."""
        with self._lock:
            cand = self._candidates.get(candidate_id)
            if not cand:
                return None
            cand.validation_status = new_status
            if notes is not None:
                cand.user_notes = notes
            cand.updated_at = datetime.now(timezone.utc)
            return cand

    # -------------------------------------------------------------
    # Observation Query & Ingestion Operations
    # -------------------------------------------------------------
    def list_observations(
        self,
        band: Optional[SPHERExBand] = None,
        min_timestamp: Optional[datetime] = None,
        max_timestamp: Optional[datetime] = None,
    ) -> List[ObservationRecord]:
        """Queries observations matching spectral band and temporal constraints."""
        with self._lock:
            obs = list(self._observations.values())
            if band:
                obs = [o for o in obs if o.band == band]
            if min_timestamp:
                obs = [o for o in obs if o.timestamp_utc >= min_timestamp]
            if max_timestamp:
                obs = [o for o in obs if o.timestamp_utc <= max_timestamp]
            return obs

    def get_observation(self, observation_id: str) -> Optional[ObservationRecord]:
        """Retrieves single observation record by ID."""
        with self._lock:
            return self._observations.get(observation_id)

    def add_observation(self, observation: ObservationRecord):
        """Ingests a new observation record into the repository."""
        with self._lock:
            self._observations[observation.observation_id] = observation


# Global repository singleton instance
repo = SPHERExRepository()
