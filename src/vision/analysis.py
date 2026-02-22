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

import json
import logging
import re
from typing import Any

from src.utils.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

SCENE_ANALYSIS_PROMPT = """\
You are a construction photo analyst for Nelson Tile & Stone in Bend, Oregon.

Analyze this construction/remodeling photo and provide a detailed structured assessment.

{detection_context}

{depth_context}

Provide your analysis as JSON with exactly this format:
{{
  "room_type": "kitchen" or "bathroom" or "laundry" or "living_room" or "bedroom" or "hallway" or "other",
  "materials": [
    {{"type": "tile/stone/wood/laminate/other", "location": "floor/wall/counter/backsplash", "condition": "new/good/fair/poor/damaged", "details": "description"}}
  ],
  "fixtures": [
    {{"type": "sink/toilet/tub/shower/faucet/vanity/cabinet/appliance", "brand": "if visible or unknown", "condition": "new/good/fair/poor"}}
  ],
  "surfaces": [
    {{"location": "floor/wall/ceiling/counter", "material": "specific material", "condition": "new/good/fair/poor/damaged"}}
  ],
  "condition_notes": ["notable conditions, damage, or issues"],
  "demolition_items": ["items that need removal for remodeling"],
  "dimensions": {{"width_ft": estimated_number, "length_ft": estimated_number, "height_ft": estimated_number}},
  "confidence": 0.0 to 1.0
}}

Respond with ONLY the JSON, no other text.
"""


class SceneAnalyzer:
    """Qwen2.5-VL based detailed scene analyzer for construction photos."""

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model: str = "qwen2.5vl:7b",
    ) -> None:
        self.ollama_host = ollama_host
        self.model = model
        self.ollama = OllamaClient(host=ollama_host)

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
            Structured analysis with room_type, materials, fixtures, surfaces,
            condition_notes, dimensions, and confidence.
        """
        detection_context = ""
        if detections:
            relevant = [d for d in detections if d.get("construction_relevant", True)]
            if relevant:
                labels = [d["label"] for d in relevant[:20]]
                detection_context = (
                    f"Objects detected in the photo: {', '.join(labels)}\n"
                    "Use these detections to help identify fixtures and materials."
                )

        depth_context = ""
        if depth_data and depth_data.get("confidence", 0) > 0:
            depth_context = (
                f"Estimated room dimensions from depth analysis: "
                f"width ~{depth_data.get('width_ft', 0)}ft, "
                f"length ~{depth_data.get('length_ft', 0)}ft, "
                f"height ~{depth_data.get('height_ft', 8)}ft. "
                f"Use these as a starting point for your dimension estimates."
            )

        prompt = SCENE_ANALYSIS_PROMPT.format(
            detection_context=detection_context,
            depth_context=depth_context,
        )

        try:
            response = self.ollama.chat_with_images(
                model=self.model,
                prompt=prompt,
                image_paths=[photo_path],
                format="json",
            )
            content = response.get("message", {}).get("content", "")
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            parsed = json.loads(content)
        except (json.JSONDecodeError, KeyError, Exception) as exc:
            logger.warning("Scene analysis failed: %s", exc)
            return {
                "room_type": "unknown",
                "materials": [],
                "fixtures": [],
                "surfaces": [],
                "condition_notes": [],
                "demolition_items": [],
                "dimensions": {},
                "confidence": 0.0,
            }

        return {
            "room_type": parsed.get("room_type", "unknown"),
            "materials": parsed.get("materials", []),
            "fixtures": parsed.get("fixtures", []),
            "surfaces": parsed.get("surfaces", []),
            "condition_notes": parsed.get("condition_notes", []),
            "demolition_items": parsed.get("demolition_items", []),
            "dimensions": parsed.get("dimensions", {}),
            "confidence": parsed.get("confidence", 0.0),
        }
