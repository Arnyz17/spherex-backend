"""
World Coordinate System (WCS) and Celestial Transformation Engine.

Converts image pixel coordinates (x, y) into celestial coordinates (RA, Dec)
using Astropy WCS and tangent projection geometry.
"""

import math
from typing import Tuple, Dict, Any, Optional
from astropy.wcs import WCS
import numpy as np
from backend.models.spherex import WCSMetadata


class WCSEngine:
    """Manages coordinate transformations between SPHEREx detector pixels and celestial sky coordinates."""

    def __init__(self, wcs_metadata: Optional[WCSMetadata] = None, fits_header: Optional[Dict[str, Any]] = None):
        self.metadata = wcs_metadata
        self.fits_header = fits_header
        self._astropy_wcs: Optional[WCS] = None
        self._init_wcs()

    def _init_wcs(self):
        """Initializes Astropy WCS from header dictionary or metadata model."""
        if self.fits_header:
            try:
                self._astropy_wcs = WCS(self.fits_header)
                return
            except Exception:
                pass
        
        if self.metadata:
            header_dict = {
                "CRVAL1": self.metadata.crval1,
                "CRVAL2": self.metadata.crval2,
                "CRPIX1": self.metadata.crpix1,
                "CRPIX2": self.metadata.crpix2,
                "CDELT1": self.metadata.cdelt1,
                "CDELT2": self.metadata.cdelt2,
                "CTYPE1": self.metadata.ctype1,
                "CTYPE2": self.metadata.ctype2,
            }
            try:
                self._astropy_wcs = WCS(header_dict)
            except Exception:
                self._astropy_wcs = None

    def pixel_to_sky(self, x: float, y: float) -> Tuple[float, float]:
        """
        Converts pixel coordinates (1-indexed FITS standard) to (RA, Dec) in degrees.
        Returns:
            (ra_deg, dec_deg)
        """
        if self._astropy_wcs is not None:
            sky = self._astropy_wcs.pixel_to_world(x - 1, y - 1)
            return float(sky.ra.deg), float(sky.dec.deg)

        # Fallback to analytical Tangent projection (Gnomonic)
        if self.metadata is None:
            raise ValueError("WCS metadata is required for coordinate transformation.")
        
        dx = (x - self.metadata.crpix1) * self.metadata.cdelt1
        dy = (y - self.metadata.crpix2) * self.metadata.cdelt2
        
        ra0_rad = math.radians(self.metadata.crval1)
        dec0_rad = math.radians(self.metadata.crval2)
        xi = math.radians(dx)
        eta = math.radians(dy)
        
        denom = math.cos(dec0_rad) - eta * math.sin(dec0_rad)
        ra_rad = ra0_rad + math.atan2(xi, denom)
        dec_rad = math.atan2(
            math.sin(dec0_rad) + eta * math.cos(dec0_rad),
            math.sqrt(denom**2 + xi**2)
        )
        
        ra_deg = (math.degrees(ra_rad)) % 360.0
        dec_deg = math.degrees(dec_rad)
        return float(ra_deg), float(dec_deg)

    def sky_to_pixel(self, ra_deg: float, dec_deg: float) -> Tuple[float, float]:
        """
        Converts (RA, Dec) in degrees to detector pixel coordinates (1-indexed).
        Returns:
            (pixel_x, pixel_y)
        """
        if self._astropy_wcs is not None:
            px, py = self._astropy_wcs.world_to_pixel_values(ra_deg, dec_deg)
            return float(px + 1), float(py + 1)

        if self.metadata is None:
            raise ValueError("WCS metadata is required for coordinate transformation.")

        ra_rad = math.radians(ra_deg)
        dec_rad = math.radians(dec_deg)
        ra0_rad = math.radians(self.metadata.crval1)
        dec0_rad = math.radians(self.metadata.crval2)

        cos_c = math.sin(dec0_rad) * math.sin(dec_rad) + math.cos(dec0_rad) * math.cos(dec_rad) * math.cos(ra_rad - ra0_rad)
        if cos_c <= 0:
            raise ValueError("Source is located behind the projection plane.")

        xi = (math.cos(dec_rad) * math.sin(ra_rad - ra0_rad)) / cos_c
        eta = (math.cos(dec0_rad) * math.sin(dec_rad) - math.sin(dec0_rad) * math.cos(dec_rad) * math.cos(ra_rad - ra0_rad)) / cos_c

        dx = math.degrees(xi)
        dy = math.degrees(eta)

        pixel_x = self.metadata.crpix1 + (dx / self.metadata.cdelt1)
        pixel_y = self.metadata.crpix2 + (dy / self.metadata.cdelt2)
        return float(pixel_x), float(pixel_y)

    def is_in_footprint(self, ra_deg: float, dec_deg: float, width_px: int = 2048, height_px: int = 2048, margin_px: int = 15) -> bool:
        """Determines if a celestial coordinate falls within valid detector active area (excluding edge margin)."""
        try:
            px, py = self.sky_to_pixel(ra_deg, dec_deg)
            return (margin_px <= px <= width_px - margin_px) and (margin_px <= py <= height_px - margin_px)
        except Exception:
            return False
