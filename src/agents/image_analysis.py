"""Image Analysis Agent — processes construction photos through a three-stage pipeline.

Pipeline stages:
1. Florence-2: Object detection (fixtures, appliances, materials)
2. Depth Anything V3: Metric depth estimation for room dimensions
3. Qwen2.5-VL: Detailed scene analysis with structured JSON output

The agent receives photo paths and returns structured assessments including
room type, materials, fixtures, dimensions, and condition notes.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from src.vision.pipeline import VisionPipeline

logger = logging.getLogger(__name__)


class RoomAssessment(BaseModel):
    """Structured output from image analysis of a single room photo."""

    room_type: str  # kitchen, bathroom, laundry, etc.
    dimensions_estimate: dict[str, float]  # width_ft, length_ft, height_ft
    materials: list[dict[str, str]]  # type, material, condition, location
    fixtures: list[dict[str, str]]  # type, brand (if visible), condition
    surfaces: list[dict[str, str]]  # location (floor/wall/ceiling), material, condition
    condition_notes: list[str]
    demolition_items: list[str]
    confidence: float


class ImageAnalysisAgent:
    """CrewAI-compatible agent for construction photo analysis."""

    def __init__(self, vision_pipeline: VisionPipeline | None = None) -> None:
        self.pipeline = vision_pipeline or VisionPipeline()

    def analyze_photo(self, photo_path: str) -> RoomAssessment:
        """Run the full three-stage pipeline on a single photo.

        Args:
            photo_path: Path to the construction/remodeling photo.

        Returns:
            Structured room assessment with materials, fixtures, and dimensions.
        """
        try:
            result = self.pipeline.process(photo_path)
        except Exception as exc:
            logger.warning("Vision pipeline failed for %s: %s", photo_path, exc)
            return RoomAssessment(
                room_type="unknown",
                dimensions_estimate={},
                materials=[],
                fixtures=[],
                surfaces=[],
                condition_notes=[f"Analysis failed: {exc}"],
                demolition_items=[],
                confidence=0.0,
            )

        scene = result.scene_analysis

        # Merge depth dimensions with scene analysis dimensions
        dimensions: dict[str, float] = {}
        if result.depth_map and result.depth_map.get("confidence", 0) > 0:
            dimensions = {
                "width_ft": result.depth_map.get("width_ft", 0.0),
                "length_ft": result.depth_map.get("length_ft", 0.0),
                "height_ft": result.depth_map.get("height_ft", 8.0),
                "floor_area_sq_ft": result.depth_map.get("floor_area_sq_ft", 0.0),
            }
        # Override with scene analysis dimensions if available (vision model may be more accurate)
        scene_dims = scene.get("dimensions", {})
        if scene_dims:
            for key in ("width_ft", "length_ft", "height_ft"):
                val = scene_dims.get(key)
                if val and val > 0:
                    dimensions[key] = val
            if dimensions.get("width_ft", 0) > 0 and dimensions.get("length_ft", 0) > 0:
                dimensions["floor_area_sq_ft"] = dimensions["width_ft"] * dimensions["length_ft"]

        return RoomAssessment(
            room_type=scene.get("room_type", "unknown"),
            dimensions_estimate=dimensions,
            materials=scene.get("materials", []),
            fixtures=scene.get("fixtures", []),
            surfaces=scene.get("surfaces", []),
            condition_notes=scene.get("condition_notes", []),
            demolition_items=scene.get("demolition_items", []),
            confidence=result.confidence,
        )

    def analyze_project_photos(self, photo_paths: list[str]) -> list[RoomAssessment]:
        """Analyze all photos for a project.

        Args:
            photo_paths: List of paths to project photos.

        Returns:
            List of room assessments, one per photo.
        """
        return [self.analyze_photo(path) for path in photo_paths]
