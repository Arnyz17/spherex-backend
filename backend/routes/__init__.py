"""Routes package for SPHEREx API."""

from backend.routes.candidates import router as candidates_router
from backend.routes.observations import router as observations_router
from backend.routes.spectral import router as spectral_router

__all__ = ["candidates_router", "observations_router", "spectral_router"]
