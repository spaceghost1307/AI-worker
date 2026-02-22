"""Image Analysis Agent — processes construction photos through a three-stage pipeline.

Pipeline stages:
1. Florence-2: Object detection (fixtures, appliances, materials)
2. Depth Anything V3: Metric depth estimation for room dimensions
3. Qwen2.5-VL: Detailed scene analysis with structured JSON output

The agent receives photo paths and returns structured assessments including
room type, materials, fixtures, dimensions, and condition notes.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from src.vision.pipeline import VisionPipeline


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
        # TODO: Run Florence-2 detection
        # TODO: Run Depth Anything V3 for dimensions
        # TODO: Run Qwen2.5-VL for detailed analysis
        # TODO: Merge results into RoomAssessment
        return RoomAssessment(
            room_type="unknown",
            dimensions_estimate={},
            materials=[],
            fixtures=[],
            surfaces=[],
            condition_notes=[],
            demolition_items=[],
            confidence=0.0,
        )

    def analyze_project_photos(self, photo_paths: list[str]) -> list[RoomAssessment]:
        """Analyze all photos for a project.

        Args:
            photo_paths: List of paths to project photos.

        Returns:
            List of room assessments, one per photo.
        """
        return [self.analyze_photo(path) for path in photo_paths]
