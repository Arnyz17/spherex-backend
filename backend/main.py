"""
SPHEREx Mission Data Analysis & Candidate Explorer Backend Service.

FastAPI Application providing REST endpoints for:
- Multi-epoch astrometric displacement & photometric variability analysis
- 6-band spectrophotometry and interstellar ice absorption detection (H2O, CO2, CO)
- WCS celestial coordinates and astronomical image cutouts
- Candidate validation triage workflows
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.candidates import router as candidates_router
from backend.routes.observations import router as observations_router
from backend.routes.spectral import router as spectral_router
from backend.db.repository import repo

app = FastAPI(
    title="SPHEREx Mission Explorer API",
    description=(
        "Backend service for the NASA SPHEREx (Spectro-Photometer for the History of the Universe, "
        "Epoch of Reionization and Ices Explorer) all-sky spectral survey.\n\n"
        "Provides time-domain astrometric displacement differencing, photometric variability tracking, "
        "and 6-band spectrophotometric ice absorption diagnostics (H2O at 3.0 um, CO2 at 4.27 um, CO at 4.67 um)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include scientific route modules
app.include_router(candidates_router)
app.include_router(observations_router)
app.include_router(spectral_router)


@app.get("/", tags=["Health & Status"])
def root_status():
    """Returns mission overview, service status, and catalog statistics."""
    candidates, total_candidates = repo.list_candidates(page=1, page_size=100)
    observations = repo.list_observations()
    return {
        "mission": "SPHEREx (Spectro-Photometer for the History of the Universe, Epoch of Reionization and Ices Explorer)",
        "launch_date": "March 11, 2025",
        "objective": "Survey the sky in optical as well as near-infrared light (0.75 - 5.0 um)",
        "status": "operational",
        "bands_count": 6,
        "indexed_candidates_count": total_candidates,
        "indexed_observations_count": len(observations),
        "docs_url": "/docs",
    }


@app.get("/api/v1/health", tags=["Health & Status"])
def health_check():
    """Health check endpoint for container probes and monitoring."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
