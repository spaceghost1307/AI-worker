"""Florence-2 object detection for construction photos.

Florence-2 (Microsoft, 0.77B parameters, <2GB VRAM, MIT license) is a
task-specific detection engine that outputs structured bounding boxes,
dense region captions, and segmentation masks.

Used to identify and localize: fixtures, appliances, cabinets, tile areas,
countertops, and structural elements in construction photos.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Construction-relevant labels to keep from detection results
CONSTRUCTION_LABELS = {
    "sink", "toilet", "bathtub", "shower", "faucet", "cabinet", "counter",
    "countertop", "tile", "floor", "wall", "ceiling", "window", "door",
    "light", "mirror", "vanity", "oven", "stove", "refrigerator", "dishwasher",
    "microwave", "hood", "vent", "fan", "outlet", "switch", "pipe", "drain",
    "shelf", "drawer", "knob", "handle", "backsplash", "tub",
}


class ObjectDetector:
    """Florence-2 based object detector for construction elements."""

    def __init__(self, model_name: str = "microsoft/Florence-2-large-ft") -> None:
        self.model_name = model_name
        self.model = None
        self.processor = None
        self._loaded = False

    def _load_model(self) -> None:
        """Lazy-load Florence-2 model and processor from HuggingFace."""
        if self._loaded:
            return

        try:
            from transformers import AutoModelForCausalLM, AutoProcessor

            logger.info("Loading Florence-2 model: %s", self.model_name)
            self.processor = AutoProcessor.from_pretrained(
                self.model_name, trust_remote_code=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name, trust_remote_code=True
            )
            self._loaded = True
            logger.info("Florence-2 model loaded successfully")
        except Exception as exc:
            logger.error("Failed to load Florence-2 model: %s", exc)
            raise

    def _run_inference(self, photo_path: str, task: str) -> dict[str, Any]:
        """Run Florence-2 inference with a specific task prompt.

        Args:
            photo_path: Path to the image.
            task: Florence-2 task token (e.g., '<OD>', '<DENSE_REGION_CAPTION>').

        Returns:
            Parsed model output.
        """
        from PIL import Image

        self._load_model()

        image = Image.open(photo_path).convert("RGB")
        inputs = self.processor(text=task, images=image, return_tensors="pt")

        generated_ids = self.model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            num_beams=3,
        )
        generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        result = self.processor.post_process_generation(
            generated_text, task=task, image_size=image.size
        )
        return result

    def detect(self, photo_path: str) -> list[dict[str, Any]]:
        """Detect construction-relevant objects in a photo.

        Args:
            photo_path: Path to the construction photo.

        Returns:
            List of detections with bounding boxes, labels, and confidence.
            Each detection: {"label": str, "bbox": [x1, y1, x2, y2], "confidence": float}
        """
        try:
            result = self._run_inference(photo_path, "<OD>")
        except Exception as exc:
            logger.warning("Florence-2 detection failed: %s", exc)
            return []

        detections = []
        od_result = result.get("<OD>", {})
        bboxes = od_result.get("bboxes", [])
        labels = od_result.get("labels", [])

        for bbox, label in zip(bboxes, labels, strict=True):
            label_lower = label.lower().strip()
            is_relevant = any(term in label_lower for term in CONSTRUCTION_LABELS)
            detections.append({
                "label": label,
                "bbox": bbox,
                "confidence": 0.8 if is_relevant else 0.5,
                "construction_relevant": is_relevant,
            })

        return detections

    def detect_with_captions(self, photo_path: str) -> list[dict[str, Any]]:
        """Detect objects and generate detailed captions for each region.

        Args:
            photo_path: Path to the construction photo.

        Returns:
            Detections with labels, bounding boxes, confidence, and captions.
        """
        detections = self.detect(photo_path)

        try:
            caption_result = self._run_inference(photo_path, "<DENSE_REGION_CAPTION>")
        except Exception as exc:
            logger.warning("Florence-2 captioning failed: %s", exc)
            return detections

        drc = caption_result.get("<DENSE_REGION_CAPTION>", {})
        cap_bboxes = drc.get("bboxes", [])
        cap_labels = drc.get("labels", [])

        for bbox, caption in zip(cap_bboxes, cap_labels, strict=True):
            detections.append({
                "label": caption,
                "bbox": bbox,
                "confidence": 0.7,
                "is_caption": True,
            })

        return detections
