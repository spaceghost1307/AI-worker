"""Three-stage vision pipeline orchestration.

Stage 1: Florence-2 → Object detection (fixtures, appliances, materials)
Stage 2: Depth Anything V3 → Metric depth estimation for room dimensions
Stage 3: Qwen2.5-VL → Detailed scene analysis with structured JSON output

Each stage can run independently or be skipped. All outputs are structured
JSON with bounding boxes and confidence scores.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.vision.analysis import SceneAnalyzer
from src.vision.depth import DepthEstimator
from src.vision.detection import ObjectDetector


class PipelineResult(BaseModel):
    """Combined result from all three vision pipeline stages."""

    photo_path: str
    detections: list[dict[str, Any]]  # Florence-2 bounding boxes + labels
    depth_map: dict[str, Any]  # Estimated dimensions from depth
    scene_analysis: dict[str, Any]  # Qwen2.5-VL structured analysis
    confidence: float


class VisionPipeline:
    """Orchestrates the three-stage vision pipeline for construction photos."""

    def __init__(
        self,
        detector: ObjectDetector | None = None,
        depth_estimator: DepthEstimator | None = None,
        scene_analyzer: SceneAnalyzer | None = None,
    ) -> None:
        self.detector = detector or ObjectDetector()
        self.depth_estimator = depth_estimator or DepthEstimator()
        self.scene_analyzer = scene_analyzer or SceneAnalyzer()

    def process(
        self,
        photo_path: str | Path,
        skip_depth: bool = False,
    ) -> PipelineResult:
        """Run the full pipeline on a single construction photo.

        Args:
            photo_path: Path to the photo file.
            skip_depth: Skip depth estimation (faster, no dimension data).

        Returns:
            Combined results from all pipeline stages.
        """
        photo_path = str(photo_path)

        # Stage 1: Object detection
        detections = self.detector.detect(photo_path)

        # Stage 2: Depth estimation (optional)
        depth_map: dict[str, Any] = {}
        if not skip_depth:
            depth_map = self.depth_estimator.estimate(photo_path)

        # Stage 3: Scene analysis with context from stages 1-2
        scene_analysis = self.scene_analyzer.analyze(
            photo_path,
            detections=detections,
            depth_data=depth_map,
        )

        return PipelineResult(
            photo_path=photo_path,
            detections=detections,
            depth_map=depth_map,
            scene_analysis=scene_analysis,
            confidence=scene_analysis.get("confidence", 0.0),
        )
