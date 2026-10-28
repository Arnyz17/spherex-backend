"""
Astronomical Cutout Generator.

Generates normalized FITS image cutouts and high-contrast base64 PNG thumbnails
for visual source inspection and multi-epoch blinking.
"""

import base64
import io
import math
from typing import Optional, Tuple
import numpy as np
from PIL import Image


class CutoutGenerator:
    """Creates synthetic or real FITS astronomical image cutouts for visual candidate validation."""

    @staticmethod
    def generate_point_source_array(
        size_px: int = 48,
        center_offset_x: float = 0.0,
        center_offset_y: float = 0.0,
        peak_flux: float = 100.0,
        fwhm_px: float = 2.5,
        bg_mean: float = 10.0,
        bg_sigma: float = 2.0,
        cosmic_ray: bool = False,
    ) -> np.ndarray:
        """
        Synthesizes a 2D astronomical image cutout with a 2D Gaussian PSF and Poisson-like noise.
        """
        y, x = np.mgrid[0:size_px, 0:size_px]
        center = size_px / 2.0
        x0 = center + center_offset_x
        y0 = center + center_offset_y

        # 2D Gaussian PSF: sigma = FWHM / (2 * sqrt(2 * ln(2)))
        sigma_psf = fwhm_px / (2.0 * math.sqrt(2.0 * math.log(2.0)))
        gaussian_profile = peak_flux * np.exp(-((x - x0)**2 + (y - y0)**2) / (2.0 * sigma_psf**2))

        # Add sky background and Gaussian noise
        noise = np.random.normal(bg_mean, bg_sigma, (size_px, size_px))
        img = gaussian_profile + noise

        # Inject simulated cosmic ray artifact if requested
        if cosmic_ray:
            cr_x = int(center + 2)
            cr_y = int(center + 1)
            img[cr_y:cr_y+3, cr_x:cr_x+2] = peak_flux * 4.0

        return np.clip(img, 0, None)

    @staticmethod
    def array_to_base64_png(
        array: np.ndarray,
        colormap: str = "inferno",
        stretch_percentiles: Tuple[float, float] = (1.0, 99.5),
    ) -> str:
        """
        Converts 2D astronomical numpy array into a base64 encoded PNG data URI.
        Applies astronomical asinh / percentile contrast stretching.
        """
        vmin = np.percentile(array, stretch_percentiles[0])
        vmax = np.percentile(array, stretch_percentiles[1])
        if vmax <= vmin:
            vmax = vmin + 1.0

        # Linear / asinh stretch
        normalized = np.clip((array - vmin) / (vmax - vmin), 0.0, 1.0)
        uint8_img = (normalized * 255.0).astype(np.uint8)

        # Apply astronomical pseudocolor (custom warm infrared / inferno map)
        if colormap == "inferno":
            # Map grayscale to warm infrared gradient (black -> purple -> orange -> bright yellow/white)
            lut = np.zeros((256, 3), dtype=np.uint8)
            for i in range(256):
                t = i / 255.0
                lut[i, 0] = int(min(255, max(0, 255 * (t ** 0.8) * 1.2)))         # Red
                lut[i, 1] = int(min(255, max(0, 255 * (t ** 1.8) * 1.1)))         # Green
                lut[i, 2] = int(min(255, max(0, 255 * math.sin(t * math.pi))))    # Blue
            rgb_data = lut[uint8_img]
            pil_img = Image.fromarray(rgb_data, mode="RGB")
        else:
            pil_img = Image.fromarray(uint8_img, mode="L")

        # Resize smoothly for web preview (e.g. 128x128)
        pil_img = pil_img.resize((128, 128), Image.Resampling.NEAREST)

        buffer = io.BytesIO()
        pil_img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"
