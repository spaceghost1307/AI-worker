"""Depth Anything V3 room measurement from single photos.

Produces metric depth maps from single photos, enabling approximate room
dimension estimation without laser measurement. Handles monocular,
multi-view, and metric depth in a single architecture.

For construction: estimates wall lengths, ceiling heights, and floor areas
from walkthrough photos. Not survey-grade, but sufficient for preliminary
estimation.

Alternative: Apple's Depth Pro (sharp metric depth in <1 second).
Both run comfortably on 16GB VRAM (~2-4GB).
"""

from __future__ import annotations

from typing import Any


class DepthEstimator:
    """Estimates room dimensions from single photos using depth models."""

    def __init__(self, model_name: str = "depth-anything-v3") -> None:
        self.model_name = model_name
        self.model = None
        # TODO: Load Depth Anything V3 model

    def estimate(self, photo_path: str) -> dict[str, Any]:
        """Generate a metric depth map and estimate room dimensions.

        Args:
            photo_path: Path to the construction photo.

        Returns:
            Estimated dimensions and depth data:
            {
                "width_ft": float,
                "length_ft": float,
                "height_ft": float,
                "floor_area_sq_ft": float,
                "depth_map_shape": [H, W],
                "confidence": float,
            }
        """
        # TODO: Load image
        # TODO: Run depth estimation model
        # TODO: Convert depth map to metric measurements
        # TODO: Estimate room dimensions from depth data
        # TODO: Return structured dimension estimates
        return {
            "width_ft": 0.0,
            "length_ft": 0.0,
            "height_ft": 0.0,
            "floor_area_sq_ft": 0.0,
            "confidence": 0.0,
        }
