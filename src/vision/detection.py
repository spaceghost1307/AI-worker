"""Florence-2 object detection for construction photos.

Florence-2 (Microsoft, 0.77B parameters, <2GB VRAM, MIT license) is a
task-specific detection engine that outputs structured bounding boxes,
dense region captions, and segmentation masks.

Used to identify and localize: fixtures, appliances, cabinets, tile areas,
countertops, and structural elements in construction photos.
"""

from __future__ import annotations

from typing import Any


class ObjectDetector:
    """Florence-2 based object detector for construction elements."""

    def __init__(self, model_name: str = "microsoft/Florence-2-large-ft") -> None:
        self.model_name = model_name
        self.model = None
        self.processor = None
        # TODO: Load Florence-2 model and processor from HuggingFace

    def detect(self, photo_path: str) -> list[dict[str, Any]]:
        """Detect construction-relevant objects in a photo.

        Args:
            photo_path: Path to the construction photo.

        Returns:
            List of detections with bounding boxes, labels, and confidence.
            Each detection: {"label": str, "bbox": [x1, y1, x2, y2], "confidence": float}
        """
        # TODO: Load image
        # TODO: Run Florence-2 with <OD> (object detection) task
        # TODO: Run Florence-2 with <DENSE_REGION_CAPTION> for detailed descriptions
        # TODO: Filter and merge results for construction-relevant objects
        # TODO: Return structured detection list
        return []

    def detect_with_captions(self, photo_path: str) -> list[dict[str, Any]]:
        """Detect objects and generate detailed captions for each region.

        Args:
            photo_path: Path to the construction photo.

        Returns:
            Detections with labels, bounding boxes, confidence, and captions.
        """
        # TODO: Run detection + dense region captioning
        return []
