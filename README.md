# SPHEREx Mission Data Analysis & Candidate Explorer Backend

Backend service for the **SPHEREx** (Spectro-Photometer for the History of the Universe, Epoch of Reionization and Ices Explorer) all-sky spectral survey mission (launched March 11, 2025).

## Key Features

- **Multi-Epoch Astrometric Differencing**: Computes angular displacements ($\Delta\theta$), statistical significance ($\sigma_{\Delta\theta}$), and annualized proper motion across multi-epoch observation baselines.
- **Photometric Variability Engine**: Calculates calibrated AB magnitude shifts ($\Delta m$) and variability significance.
- **6-Band Spectrophotometry**:
  - **Band 1**: $0.75 - 1.11\,\mu\text{m}$ ($R=39$) — Optical/NIR stellar & galaxy light
  - **Band 2**: $1.11 - 1.64\,\mu\text{m}$ ($R=41$) — NIR SED stellar populations
  - **Band 3**: $1.64 - 2.42\,\mu\text{m}$ ($R=41$) — Galaxy photometric redshifts & CIB
  - **Band 4**: $2.42 - 3.82\,\mu\text{m}$ ($R=35$) — **Water-ice ($H_2O$) absorption** at $\approx 3.0\,\mu\text{m}$
  - **Band 5**: $3.82 - 4.42\,\mu\text{m}$ ($R=112$) — **Carbon dioxide ($CO_2$) ice** at $\approx 4.27\,\mu\text{m}$
  - **Band 6**: $4.42 - 5.00\,\mu\text{m}$ ($R=128$) — **Carbon monoxide ($CO$) ice** at $\approx 4.67\,\mu\text{m}$
- **Automated Scientific Triage**: Classifies sources into High Proper Motion Stars, Transients/Variables, Molecular Ice Features, Stationary Galaxies, and Detector Artifacts.
- **Cutout Generator**: Produces astronomical image cutouts and base64 PNG previews for frontend rendering.
- **FastAPI REST Service**: Interactive Swagger API docs (`/docs`) and ReDoc (`/redoc`).

## Quickstart

### Prerequisites
- Python 3.10+

### Setup & Run
```bash
# Clone the repository
git clone <repo-url>
cd NASA

# Start the server (automatically sets up venv and installs dependencies)
./run_backend.sh
```

Or manually:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

### Running Tests
```bash
source venv/bin/activate
PYTHONPATH=. pytest backend/tests/ -v
```
