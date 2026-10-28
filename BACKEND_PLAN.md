# SPHEREx Backend Architecture & Implementation Plan

## 1. Executive Summary & Scientific Purpose

The **SPHEREx** (Spectro-Photometer for the History of the Universe, Epoch of Reionization and Ices Explorer) observatory surveys the celestial sphere in near-infrared and optical regimes ($0.75 - 5.0\,\mu\text{m}$) across 6 dedicated spectral channels with resolving power $R = 35 - 128$.

This backend system addresses two critical analytical pillars:
1. **Time-Domain Astrometry & Photometry**: Using observation timestamps and World Coordinate System (WCS) metadata to calculate physical source displacement (proper motion) and brightness variations ($\Delta m$) across temporal baselines.
2. **6-Band Spectrophotometry & Ice Absorption**: Extracting continuous spectral energy distributions (SED) and quantifying absorption features for interstellar/circumstellar ices:
   - **$H_2O$ Ice**: $\approx 3.0\,\mu\text{m}$ (Band 4, $R=35$)
   - **$CO_2$ Ice**: $\approx 4.27\,\mu\text{m}$ (Band 5, $R=112$)
   - **$CO$ Ice**: $\approx 4.67\,\mu\text{m}$ (Band 6, $R=128$)

---

## 2. SPHEREx Spectral Band Configuration

| Band | Spectral Range | Nominal $R = \lambda/\Delta\lambda$ | Target Physics & Diagnostic Features |
| :--- | :--- | :--- | :--- |
| **Band 1** | $0.7 - 1.1\,\mu\text{m}$ | $R = 39$ | Optical-to-NIR continuum; stellar SED baseline; redshifted Lyman/Balmer emission |
| **Band 2** | $1.1 - 1.6\,\mu\text{m}$ | $R = 41$ | Stellar population characterization; galactic disk emission |
| **Band 3** | $1.6 - 2.4\,\mu\text{m}$ | $R = 41$ | Galaxy photometric redshifts ($z$ estimation); Cosmic Infrared Background (CIB) |
| **Band 4** | $2.4 - 3.8\,\mu\text{m}$ | $R = 35$ | **Broad Water Ice ($H_2O$) absorption band** centered at $\approx 3.0\,\mu\text{m}$ |
| **Band 5** | $3.8 - 4.4\,\mu\text{m}$ | $R = 112$ | **Narrow Carbon Dioxide ($CO_2$) ice absorption band** at $\approx 4.27\,\mu\text{m}$ |
| **Band 6** | $4.4 - 5.0\,\mu\text{m}$ | $R = 128$ | **High-resolution Carbon Monoxide ($CO$) ice band** at $\approx 4.67\,\mu\text{m}$ |

---

## 3. System Architecture & Processing Pipeline

```mermaid
flowchart TD
    subgraph INGESTION ["1. Ingestion & Preprocessing Layer"]
        FITS[SPHEREx FITS / IPAC Ingestion] --> WCS_MOD[WCS Astrometric Solver & Header Parser]
        FITS --> CALIB_MOD[Zero-Point & Photometric Calibration]
        FITS --> MASK_MOD[Data-Quality Flag Bitmasking]
    end

    subgraph SCI_PIPELINE ["2. Scientific Core Engine"]
        WCS_MOD --> SRC_CENTROID[Centroiding & Sky Coordinate Transform (RA/Dec)]
        CALIB_MOD --> APERTURE_PHOT[Aperture Photometry & Flux Extraction]
        
        SRC_CENTROID --> CROSS_EPOCH[Multi-Epoch Spatial Cross-Matcher]
        APERTURE_PHOT --> CROSS_EPOCH
        
        CROSS_EPOCH --> ASTRO_DIFF[Astrometric Displacement Engine (\Delta\theta, \sigma_{\Delta\theta})]
        CROSS_EPOCH --> PHOTO_DIFF[Photometric Differencing Engine (\Delta m, \sigma_{\Delta m})]
        CROSS_EPOCH --> SED_ICE[6-Band SED & Ice Equivalent Width Analyzer (W_\lambda)]
        
        ASTRO_DIFF --> CLASSIFIER[Automated Classifier & Triage Assigner]
        PHOTO_DIFF --> CLASSIFIER
        SED_ICE --> CLASSIFIER
        MASK_MOD --> CLASSIFIER
    end

    subgraph PERSISTENCE ["3. Storage & Spatial Indexing"]
        CLASSIFIER --> DB[(DuckDB / SQLite with Spatial Index)]
        FITS --> CUTOUT_CACHE[(FITS / PNG Cutout Generator & Cache)]
    end

    subgraph API_SERVICE ["4. FastAPI REST Endpoints"]
        DB --> EP_CANDIDATES["GET /api/v1/candidates (Filtering & Pagination)"]
        DB --> EP_DETAIL["GET /api/v1/candidates/{id} (Full Multi-Epoch Record)"]
        DB --> EP_SED["GET /api/v1/candidates/{id}/spectrum (6-Band + Ice Fit)"]
        CUTOUT_CACHE --> EP_CUTOUT["GET /api/v1/observations/{id}/cutout (FITS / PNG)"]
        EP_VALIDATE["POST /api/v1/candidates/{id}/validate (Frontend Triage Status)"] --> DB
    end
```

---

## 4. Backend Data Schema

### 4.1. Observation Record (Input Data Model)
Satisfies all 8 backend specifications:
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

class SPHERExBand(str, Enum):
    BAND_1 = "BAND_1"  # 0.7 - 1.1 um (R=39)
    BAND_2 = "BAND_2"  # 1.1 - 1.6 um (R=41)
    BAND_3 = "BAND_3"  # 1.6 - 2.4 um (R=41)
    BAND_4 = "BAND_4"  # 2.4 - 3.8 um (R=35, H2O Ice)
    BAND_5 = "BAND_5"  # 3.8 - 4.4 um (R=112, CO2 Ice)
    BAND_6 = "BAND_6"  # 4.4 - 5.0 um (R=128, CO Ice)

class QualityFlagBitmask(int):
    CLEAN = 0
    BAD_PIXEL = 1 << 0          # Bit 0: Dead/noisy pixel
    COSMIC_RAY = 1 << 1         # Bit 1: Cosmic ray hit
    SATURATED = 1 << 2          # Bit 2: Saturated pixel within PSF
    EDGE_PROXIMITY = 1 << 3     # Bit 3: Source < 15px from detector edge
    HIGH_JITTER = 1 << 4        # Bit 4: Pointing jitter exceeding tolerance

class ObservationRecord(BaseModel):
    observation_id: str = Field(..., description="Unique frame exposure identifier")
    timestamp_utc: datetime = Field(..., description="Timestamp when observation was taken")
    timestamp_mjd: float = Field(..., description="Modified Julian Date for temporal baseline math")
    band: SPHERExBand = Field(..., description="SPHEREx spectral band channel (1 to 6)")
    wavelength_center_um: float = Field(..., description="Band central wavelength in microns")
    exposure_time_sec: float = Field(..., description="Exposure duration in seconds")
    wcs_header: Dict[str, Any] = Field(..., description="FITS WCS keys: CRVAL1/2, CRPIX1/2, CDELT1/2, CTYPE")
    quality_flags: int = Field(default=0, description="Bitmask of detector data-quality indicators")
    zeropoint_mag: float = Field(..., description="Photometric zero-point for flux-to-magnitude conversion")
    background_rms: float = Field(..., description="Sky background noise level (mJy/sr or ADU)")
    image_uri: str = Field(..., description="Filesystem or object storage path to FITS file")
```

### 4.2. Candidate Output Model (Supplied to Frontend)
Satisfies all 9 frontend requirements:
```python
class ValidationStatus(str, Enum):
    PLAUSIBLE_CANDIDATE = "Plausible Candidate"
    CONFIRMED = "Confirmed"
    INCONCLUSIVE = "Inconclusive"
    LIKELY_ARTIFACT = "Likely Artifact"

class ScientificCategory(str, Enum):
    HIGH_PROPER_MOTION = "High Proper Motion Star"
    PHOTOMETRIC_TRANSIENT = "Photometric Transient / Variable Star"
    WATER_ICE_ABSORPTION = "Interstellar H2O Ice Feature"
    CO2_ICE_ABSORPTION = "Circumstellar CO2 Ice Feature"
    CO_ICE_ABSORPTION = "Dense Core CO Ice Feature"
    STATIONARY_GALAXY = "Quiescent Galaxy SED"
    SUSPECTED_ARTIFACT = "Detector Artifact / Spike"

class CandidateSummary(BaseModel):
    candidate_id: str = Field(..., description="Unique source or candidate ID")
    ra: float = Field(..., description="Right Ascension (degrees, J2000)")
    dec: float = Field(..., description="Declination (degrees, J2000)")
    observation_dates: List[datetime] = Field(..., description="List of timestamps when measurements occurred")
    bands_observed: List[SPHERExBand] = Field(..., description="SPHEREx bands covering this candidate")
    
    # Measured displacement & uncertainty
    displacement_arcsec: float = Field(..., description="Measured angular displacement between epochs")
    displacement_uncertainty_arcsec: float = Field(..., description="1-sigma positional uncertainty")
    displacement_significance_sigma: float = Field(..., description="Ratio of displacement to uncertainty")
    
    # Measured brightness change & uncertainty
    delta_brightness_mag: float = Field(..., description="Measured magnitude change between epochs (m2 - m1)")
    delta_brightness_uncertainty_mag: float = Field(..., description="1-sigma photometric uncertainty")
    
    # Data quality
    quality_indicators: List[str] = Field(..., description="Human-readable flags e.g. ['nominal', 'clean']")
    has_quality_warnings: bool
    
    # Science & Validation
    scientific_interpretation: ScientificCategory
    scientific_summary: str = Field(..., description="Evidence explanation (e.g. 4.2-sigma proper motion shift)")
    validation_status: ValidationStatus
```

### 4.3. Full Spectral Extraction Model (for SED & Ice Inspector)
```python
class SpectralPoint(BaseModel):
    wavelength_um: float
    flux_density_mjy: float
    flux_error_mjy: float
    band: SPHERExBand
    resolution_power: int

class CandidateDetail(CandidateSummary):
    spectrum: List[SpectralPoint] = Field(..., description="Full 6-band spectrum")
    ice_equivalent_widths: Dict[str, float] = Field(
        ..., 
        description="Calculated equivalent widths in microns: {'H2O_3.0um': 0.14, 'CO2_4.27um': 0.05, 'CO_4.67um': 0.02}"
    )
    cutout_urls: Dict[str, str] = Field(
        ..., 
        description="Map of (epoch_id, band) to direct image cutout URLs for visual blinking/inspection"
    )
    user_notes: Optional[str] = Field(default="", description="Scientist triage notes")
```

---

## 5. Core Mathematical & Scientific Algorithms

### 5.1. Astrometric Projection & Displacement Engine
1. **WCS Projection**:
   $$\begin{pmatrix} x \\ y \end{pmatrix} \xrightarrow{\text{WCS}(\text{CRVAL}, \text{CD})} \begin{pmatrix} \alpha \\ \delta \end{pmatrix}$$
2. **Angular Separation ($\Delta\theta$)**:
   $$\Delta\theta = 2 \arcsin \sqrt{ \sin^2\left(\frac{\delta_2 - \delta_1}{2}\right) + \cos\delta_1 \cos\delta_2 \sin^2\left(\frac{\alpha_2 - \alpha_1}{2}\right) }$$
3. **Displacement Significance**:
   $$\sigma_{\Delta\theta} = \sqrt{\sigma_{\text{pos}, 1}^2 + \sigma_{\text{pos}, 2}^2}, \quad S_{\text{astro}} = \frac{\Delta\theta}{\sigma_{\Delta\theta}}$$
   - If $S_{\text{astro}} \ge 3.0$ and Quality Flag is clean $\to$ **High Proper Motion Candidate**.

### 5.2. Photometric Differencing & Variability Engine
1. **Calibrated Magnitude**:
   $$m_i = -2.5 \log_{10}(F_i) + \text{ZP}_i, \quad \sigma_{m, i} \approx \frac{2.5}{\ln 10} \frac{\sigma_{F, i}}{F_i}$$
2. **Delta Magnitude ($\Delta m$)**:
   $$\Delta m = m(t_2) - m(t_1), \quad \sigma_{\Delta m} = \sqrt{\sigma_{m, 1}^2 + \sigma_{m, 2}^2}, \quad S_{\text{photo}} = \frac{|\Delta m|}{\sigma_{\Delta m}}$$
   - If $S_{\text{photo}} \ge 3.5 \to$ **Photometric Transient / Variable Candidate**.

### 5.3. Ice Absorption Continuum Fitting & Equivalent Width ($W_\lambda$)
For Bands 4, 5, and 6:
1. Estimate local continuum $F_{\text{cont}}(\lambda)$ by linear interpolation across anchor windows:
   - $H_2O$ window: $[2.5, 2.7]\,\mu\text{m}$ and $[3.6, 3.8]\,\mu\text{m}$
   - $CO_2$ window: $[4.0, 4.15]\,\mu\text{m}$ and $[4.35, 4.45]\,\mu\text{m}$
   - $CO$ window: $[4.5, 4.6]\,\mu\text{m}$ and $[4.75, 4.85]\,\mu\text{m}$
2. Compute Equivalent Width:
   $$W_\lambda = \sum_{k} \left(1 - \frac{F_{\text{obs}}(\lambda_k)}{F_{\text{cont}}(\lambda_k)}\right) \Delta \lambda_k$$
   - If $W_\lambda \ge 3\sigma_W \to$ **Molecular Ice Absorption Feature Confirmed**.

---

## 6. REST API Endpoint Specifications

### `GET /api/v1/candidates`
**Query Parameters**:
- `min_displacement_sigma` (float, default: `0.0`): Filter by proper motion significance
- `min_delta_mag` (float, optional): Filter by minimum brightness variation
- `ice_feature` (string, optional: `H2O`, `CO2`, `CO`): Filter sources exhibiting specific ices
- `validation_status` (string, optional): Filter by validation triage state
- `band` (string, optional): Filter by SPHEREx band
- `page` / `page_size`: Pagination controls

**Response**:
```json
{
  "total": 450,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "candidate_id": "SPX-J1802-2341",
      "ra": 270.5412,
      "dec": -23.6891,
      "observation_dates": ["2025-04-12T04:22:10Z", "2025-10-18T14:15:00Z"],
      "bands_observed": ["BAND_4", "BAND_5", "BAND_6"],
      "displacement_arcsec": 0.42,
      "displacement_uncertainty_arcsec": 0.08,
      "displacement_significance_sigma": 5.25,
      "delta_brightness_mag": 0.12,
      "delta_brightness_uncertainty_mag": 0.03,
      "quality_indicators": ["nominal", "high_snr"],
      "has_quality_warnings": false,
      "scientific_interpretation": "High Proper Motion Star",
      "scientific_summary": "5.25-sigma astrometric shift detected over 6-month baseline.",
      "validation_status": "Plausible Candidate"
    }
  ]
}
```

### `GET /api/v1/candidates/{id}`
Returns the complete Candidate detail, including multi-epoch timeline, full 6-band spectrum, calculated ice equivalent widths, and image cutout thumbnails.

### `POST /api/v1/candidates/{id}/validate`
**Payload**:
```json
{
  "validation_status": "Confirmed",
  "notes": "Verified against 2MASS and Gaia DR3 astrometry. Confirmed high-proper-motion M-dwarf."
}
```
**Response**: Updated Candidate detail object.

### `GET /api/v1/observations/{id}/cutout`
Generates normalized PNG or FITS image cutout centered at requested `ra` and `dec` with specified `size_arcsec`.

---

## 7. Recommended Implementation Steps

| Step | Component | Files to Create | Output |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Data Schemas & Band Constants | `models/spherex.py`, `models/candidates.py` | Complete Pydantic schemas |
| **Phase 2** | Astrometric & Photometric Differencing | `services/differencing.py`, `services/wcs.py` | Displacement & $\Delta m$ calculations |
| **Phase 3** | 6-Band Spectral & Ice Extractor | `services/spectral_ice.py` | Equivalent width fits for $H_2O, CO_2, CO$ |
| **Phase 4** | In-Memory / SQLite Spatial Repository | `db/repository.py`, `db/seed_data.py` | Realistic SPHEREx catalog generator |
| **Phase 5** | FastAPI REST Application | `main.py`, `routes/candidates.py`, `routes/observations.py` | Live Swagger UI / OpenAPI docs |
