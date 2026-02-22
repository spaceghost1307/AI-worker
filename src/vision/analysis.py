"""Qwen2.5-VL scene analysis for detailed construction photo interpretation.

Qwen2.5-VL 7B natively outputs structured JSON with bounding box coordinates,
has strong OCR for reading labels and specifications, and outperforms
GPT-4o-mini on many visual tasks at the 7B scale.

Receives the photo along with detection results from Florence-2 and produces:
- Room type identification
- Material/surface recognition
- Condition assessment
- Fixture inventory
- JSON-formatted construction data
"""

from __future__ import annotations

from typing import Any

import httpx


class SceneAnalyzer:
    """Qwen2.5-VL based detailed scene analyzer for construction photos."""

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model: str = "qwen2.5vl:7b",
    ) -> None:
        self.ollama_host = ollama_host
        self.model = model
        self._client = httpx.Client(timeout=120.0)

    def analyze(
        self,
        photo_path: str,
        detections: list[dict[str, Any]] | None = None,
        depth_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform detailed scene analysis on a construction photo.

        Args:
            photo_path: Path to the photo.
            detections: Florence-2 detection results to provide as context.
            depth_data: Depth estimation results to provide as context.

        Returns:
            Structured analysis:
            {
                "room_type": str,
                "materials": [{"type": str, "location": str, "condition": str}],
                "fixtures": [{"type": str, "brand": str, "condition": str}],
                "surfaces": [{"location": str, "material": str, "condition": str}],
                "condition_notes": [str],
                "dimensions": {"width_ft": float, "length_ft": float, "height_ft": float},
                "confidence": float,
            }
        """
        # TODO: Build structured prompt with detection context
        # TODO: Encode image for Ollama vision API
        # TODO: Send to Qwen2.5-VL via Ollama
        # TODO: Parse structured JSON response
        return {
            "room_type": "unknown",
            "materials": [],
            "fixtures": [],
            "surfaces": [],
            "condition_notes": [],
            "dimensions": {},
            "confidence": 0.0,
        }
