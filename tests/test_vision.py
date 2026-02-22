"""Tests for the vision pipeline components.

Tests cover detection, depth estimation, scene analysis, and the full pipeline
using mocked models — no GPU or real model inference required.
"""

from unittest.mock import MagicMock

import numpy as np

from src.vision.analysis import SceneAnalyzer
from src.vision.depth import DEFAULT_CEILING_HEIGHT_FT, DepthEstimator
from src.vision.detection import CONSTRUCTION_LABELS, ObjectDetector
from src.vision.pipeline import PipelineResult, VisionPipeline

# ---------------------------------------------------------------------------
# ObjectDetector
# ---------------------------------------------------------------------------

class TestObjectDetectorInit:
    """Test ObjectDetector initialization."""

    def test_default_model_name(self) -> None:
        detector = ObjectDetector()
        assert detector.model_name == "microsoft/Florence-2-large-ft"
        assert detector._loaded is False

    def test_custom_model_name(self) -> None:
        detector = ObjectDetector(model_name="custom/model")
        assert detector.model_name == "custom/model"

    def test_model_not_loaded_initially(self) -> None:
        detector = ObjectDetector()
        assert detector.model is None
        assert detector.processor is None


class TestObjectDetectorDetect:
    """Test ObjectDetector.detect with mocked inference."""

    def test_detect_returns_detections(self) -> None:
        detector = ObjectDetector()
        detector._loaded = True
        detector.model = MagicMock()
        detector.processor = MagicMock()

        mock_result = {
            "<OD>": {
                "bboxes": [[10, 20, 100, 200], [50, 60, 150, 250]],
                "labels": ["sink", "chair"],
            }
        }
        detector._run_inference = MagicMock(return_value=mock_result)

        detections = detector.detect("photo.jpg")
        assert len(detections) == 2
        assert detections[0]["label"] == "sink"
        assert detections[0]["construction_relevant"] is True
        assert detections[0]["confidence"] == 0.8
        assert detections[1]["label"] == "chair"
        assert detections[1]["construction_relevant"] is False
        assert detections[1]["confidence"] == 0.5

    def test_detect_empty_on_failure(self) -> None:
        detector = ObjectDetector()
        detector._run_inference = MagicMock(side_effect=RuntimeError("Model not loaded"))

        detections = detector.detect("photo.jpg")
        assert detections == []

    def test_detect_empty_results(self) -> None:
        detector = ObjectDetector()
        detector._loaded = True
        detector._run_inference = MagicMock(return_value={"<OD>": {"bboxes": [], "labels": []}})

        detections = detector.detect("photo.jpg")
        assert detections == []

    def test_detect_multiple_construction_labels(self) -> None:
        detector = ObjectDetector()
        detector._loaded = True
        labels = ["toilet", "bathtub", "tile", "mirror", "faucet"]
        mock_result = {
            "<OD>": {
                "bboxes": [[i * 10, i * 10, i * 100, i * 100] for i in range(len(labels))],
                "labels": labels,
            }
        }
        detector._run_inference = MagicMock(return_value=mock_result)

        detections = detector.detect("bathroom.jpg")
        assert len(detections) == 5
        assert all(d["construction_relevant"] for d in detections)


class TestObjectDetectorCaptions:
    """Test ObjectDetector.detect_with_captions."""

    def test_captions_appended(self) -> None:
        detector = ObjectDetector()
        detector._loaded = True

        call_count = 0
        def mock_inference(path: str, task: str) -> dict:
            nonlocal call_count
            call_count += 1
            if task == "<OD>":
                return {"<OD>": {"bboxes": [[0, 0, 50, 50]], "labels": ["sink"]}}
            return {"<DENSE_REGION_CAPTION>": {"bboxes": [[0, 0, 100, 100]], "labels": ["White porcelain sink"]}}

        detector._run_inference = mock_inference
        detections = detector.detect_with_captions("photo.jpg")
        assert len(detections) == 2
        assert detections[0]["label"] == "sink"
        assert detections[1]["label"] == "White porcelain sink"
        assert detections[1].get("is_caption") is True

    def test_captions_fallback_on_error(self) -> None:
        detector = ObjectDetector()
        detector._loaded = True

        call_count = 0
        def mock_inference(path: str, task: str) -> dict:
            nonlocal call_count
            call_count += 1
            if task == "<OD>":
                return {"<OD>": {"bboxes": [[0, 0, 50, 50]], "labels": ["toilet"]}}
            raise RuntimeError("Caption failed")

        detector._run_inference = mock_inference
        detections = detector.detect_with_captions("photo.jpg")
        assert len(detections) == 1
        assert detections[0]["label"] == "toilet"


class TestConstructionLabels:
    """Test the CONSTRUCTION_LABELS set."""

    def test_labels_are_lowercase(self) -> None:
        for label in CONSTRUCTION_LABELS:
            assert label == label.lower()

    def test_key_fixture_labels_present(self) -> None:
        expected = {"sink", "toilet", "bathtub", "shower", "faucet", "cabinet"}
        assert expected.issubset(CONSTRUCTION_LABELS)

    def test_key_material_labels_present(self) -> None:
        expected = {"tile", "countertop", "backsplash"}
        assert expected.issubset(CONSTRUCTION_LABELS)


# ---------------------------------------------------------------------------
# DepthEstimator
# ---------------------------------------------------------------------------

class TestDepthEstimatorInit:
    """Test DepthEstimator initialization."""

    def test_default_model(self) -> None:
        estimator = DepthEstimator()
        assert estimator.model_name == "depth-anything-v3"
        assert estimator._loaded is False

    def test_custom_model(self) -> None:
        estimator = DepthEstimator(model_name="custom-depth")
        assert estimator.model_name == "custom-depth"


class TestDepthToDimensions:
    """Test depth map to dimensions conversion."""

    def test_flat_depth_map(self) -> None:
        estimator = DepthEstimator()
        flat = np.ones((480, 640), dtype=np.float32)
        result = estimator._depth_to_dimensions(flat)
        assert result["confidence"] == 0.1
        assert result["width_ft"] == 0.0
        assert result["length_ft"] == 0.0
        assert result["height_ft"] == DEFAULT_CEILING_HEIGHT_FT

    def test_varying_depth_map(self) -> None:
        estimator = DepthEstimator()
        depth = np.random.rand(480, 640).astype(np.float32) * 10.0
        result = estimator._depth_to_dimensions(depth)
        assert result["width_ft"] > 0
        assert result["length_ft"] > 0
        assert result["height_ft"] == DEFAULT_CEILING_HEIGHT_FT
        assert result["floor_area_sq_ft"] > 0
        assert 0 < result["confidence"] <= 0.7

    def test_dimensions_within_bounds(self) -> None:
        estimator = DepthEstimator()
        depth = np.random.rand(480, 640).astype(np.float32) * 100.0
        result = estimator._depth_to_dimensions(depth)
        assert 3.0 <= result["width_ft"] <= 40.0
        assert 3.0 <= result["length_ft"] <= 40.0

    def test_depth_map_shape_returned(self) -> None:
        estimator = DepthEstimator()
        depth = np.random.rand(100, 200).astype(np.float32) * 5.0
        result = estimator._depth_to_dimensions(depth)
        assert result["depth_map_shape"] == [100, 200]

    def test_small_depth_map(self) -> None:
        estimator = DepthEstimator()
        depth = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        result = estimator._depth_to_dimensions(depth)
        assert "width_ft" in result
        assert "length_ft" in result

    def test_gradient_depth_map(self) -> None:
        """A gradient depth map should produce meaningful dimensions."""
        estimator = DepthEstimator()
        # Simulate looking down a room: depth increases with row index
        depth = np.zeros((480, 640), dtype=np.float32)
        for i in range(480):
            depth[i, :] = i * 0.02  # 0 to ~9.6 meters
        result = estimator._depth_to_dimensions(depth)
        assert result["length_ft"] > 6.0
        assert result["confidence"] > 0.1


class TestCalibrateDepth:
    """Test the _calibrate_dimension static method."""

    def test_zero_median(self) -> None:
        result = DepthEstimator._calibrate_dimension(1.0, 0.0, 5.0, 20.0)
        assert result == 12.5  # midpoint

    def test_normal_calibration(self) -> None:
        result = DepthEstimator._calibrate_dimension(1.0, 2.0, 5.0, 20.0)
        assert 5.0 <= result <= 20.0

    def test_clamped_high(self) -> None:
        result = DepthEstimator._calibrate_dimension(100.0, 1.0, 5.0, 20.0)
        assert result == 20.0

    def test_clamped_low(self) -> None:
        result = DepthEstimator._calibrate_dimension(0.001, 10.0, 5.0, 20.0)
        assert abs(result - 5.0) < 0.01  # Very close to minimum


class TestDepthEstimatorEstimate:
    """Test DepthEstimator.estimate with failure fallback."""

    def test_estimate_returns_defaults_on_error(self) -> None:
        estimator = DepthEstimator()
        # Don't actually load the model — it'll fail and return defaults
        result = estimator.estimate("nonexistent.jpg")
        assert result["width_ft"] == 0.0
        assert result["confidence"] == 0.0


# ---------------------------------------------------------------------------
# SceneAnalyzer
# ---------------------------------------------------------------------------

class TestSceneAnalyzerInit:
    """Test SceneAnalyzer initialization."""

    def test_default_model(self) -> None:
        analyzer = SceneAnalyzer()
        assert analyzer.model == "qwen2.5vl:7b"

    def test_custom_model(self) -> None:
        analyzer = SceneAnalyzer(model="custom-vl:4b")
        assert analyzer.model == "custom-vl:4b"


class TestSceneAnalyzerAnalyze:
    """Test SceneAnalyzer.analyze with mocked Ollama."""

    def test_successful_analysis(self) -> None:
        analyzer = SceneAnalyzer()
        mock_response = {
            "message": {
                "content": '{"room_type":"kitchen","materials":[{"type":"tile","location":"floor"}],'
                '"fixtures":[{"type":"sink"}],"surfaces":[],"condition_notes":[],'
                '"demolition_items":[],"dimensions":{"width_ft":12,"length_ft":15},'
                '"confidence":0.85}'
            }
        }
        analyzer.ollama = MagicMock()
        analyzer.ollama.chat_with_images.return_value = mock_response

        result = analyzer.analyze("kitchen.jpg")
        assert result["room_type"] == "kitchen"
        assert result["confidence"] == 0.85
        assert len(result["materials"]) == 1

    def test_analysis_with_think_tags(self) -> None:
        analyzer = SceneAnalyzer()
        mock_response = {
            "message": {
                "content": '<think>Let me analyze this carefully...</think>'
                '{"room_type":"bathroom","materials":[],"fixtures":[],"surfaces":[],'
                '"condition_notes":[],"demolition_items":[],"dimensions":{},"confidence":0.7}'
            }
        }
        analyzer.ollama = MagicMock()
        analyzer.ollama.chat_with_images.return_value = mock_response

        result = analyzer.analyze("bathroom.jpg")
        assert result["room_type"] == "bathroom"

    def test_analysis_with_detections_context(self) -> None:
        analyzer = SceneAnalyzer()
        mock_response = {
            "message": {
                "content": '{"room_type":"bathroom","materials":[],"fixtures":[],"surfaces":[],'
                '"condition_notes":[],"demolition_items":[],"dimensions":{},"confidence":0.6}'
            }
        }
        analyzer.ollama = MagicMock()
        analyzer.ollama.chat_with_images.return_value = mock_response

        detections = [
            {"label": "toilet", "construction_relevant": True},
            {"label": "sink", "construction_relevant": True},
        ]
        result = analyzer.analyze("bath.jpg", detections=detections)
        assert result["room_type"] == "bathroom"

    def test_analysis_with_depth_context(self) -> None:
        analyzer = SceneAnalyzer()
        mock_response = {
            "message": {
                "content": '{"room_type":"kitchen","materials":[],"fixtures":[],"surfaces":[],'
                '"condition_notes":[],"demolition_items":[],"dimensions":{},"confidence":0.8}'
            }
        }
        analyzer.ollama = MagicMock()
        analyzer.ollama.chat_with_images.return_value = mock_response

        depth_data = {"width_ft": 10.0, "length_ft": 12.0, "height_ft": 8.0, "confidence": 0.5}
        result = analyzer.analyze("kitchen.jpg", depth_data=depth_data)
        assert result["room_type"] == "kitchen"

    def test_analysis_failure_returns_defaults(self) -> None:
        analyzer = SceneAnalyzer()
        analyzer.ollama = MagicMock()
        analyzer.ollama.chat_with_images.side_effect = Exception("Connection refused")

        result = analyzer.analyze("photo.jpg")
        assert result["room_type"] == "unknown"
        assert result["confidence"] == 0.0
        assert result["materials"] == []

    def test_analysis_bad_json(self) -> None:
        analyzer = SceneAnalyzer()
        analyzer.ollama = MagicMock()
        analyzer.ollama.chat_with_images.return_value = {
            "message": {"content": "not valid json at all"}
        }

        result = analyzer.analyze("photo.jpg")
        assert result["room_type"] == "unknown"
        assert result["confidence"] == 0.0


# ---------------------------------------------------------------------------
# VisionPipeline
# ---------------------------------------------------------------------------

class TestPipelineResult:
    """Test PipelineResult model."""

    def test_create_result(self) -> None:
        result = PipelineResult(
            photo_path="test.jpg",
            detections=[],
            depth_map={},
            scene_analysis={"room_type": "kitchen"},
            confidence=0.8,
        )
        assert result.photo_path == "test.jpg"
        assert result.confidence == 0.8


class TestVisionPipeline:
    """Test VisionPipeline orchestration with mocked components."""

    def test_full_pipeline(self) -> None:
        mock_detector = MagicMock()
        mock_detector.detect.return_value = [
            {"label": "sink", "bbox": [0, 0, 50, 50], "confidence": 0.8, "construction_relevant": True},
        ]

        mock_depth = MagicMock()
        mock_depth.estimate.return_value = {
            "width_ft": 10.0,
            "length_ft": 12.0,
            "height_ft": 8.0,
            "floor_area_sq_ft": 120.0,
            "confidence": 0.5,
        }

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "room_type": "kitchen",
            "materials": [],
            "fixtures": [{"type": "sink"}],
            "surfaces": [],
            "condition_notes": [],
            "demolition_items": [],
            "dimensions": {},
            "confidence": 0.85,
        }

        pipeline = VisionPipeline(
            detector=mock_detector,
            depth_estimator=mock_depth,
            scene_analyzer=mock_analyzer,
        )
        result = pipeline.process("kitchen.jpg")

        assert isinstance(result, PipelineResult)
        assert result.photo_path == "kitchen.jpg"
        assert len(result.detections) == 1
        assert result.depth_map["width_ft"] == 10.0
        assert result.scene_analysis["room_type"] == "kitchen"
        assert result.confidence == 0.85

        mock_detector.detect.assert_called_once_with("kitchen.jpg")
        mock_depth.estimate.assert_called_once_with("kitchen.jpg")
        mock_analyzer.analyze.assert_called_once()

    def test_pipeline_skip_depth(self) -> None:
        mock_detector = MagicMock()
        mock_detector.detect.return_value = []

        mock_depth = MagicMock()

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "room_type": "unknown",
            "confidence": 0.0,
        }

        pipeline = VisionPipeline(
            detector=mock_detector,
            depth_estimator=mock_depth,
            scene_analyzer=mock_analyzer,
        )
        result = pipeline.process("photo.jpg", skip_depth=True)

        mock_depth.estimate.assert_not_called()
        assert result.depth_map == {}

    def test_pipeline_path_conversion(self) -> None:
        from pathlib import Path

        mock_detector = MagicMock()
        mock_detector.detect.return_value = []
        mock_depth = MagicMock()
        mock_depth.estimate.return_value = {}
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {"confidence": 0.0}

        pipeline = VisionPipeline(
            detector=mock_detector,
            depth_estimator=mock_depth,
            scene_analyzer=mock_analyzer,
        )
        result = pipeline.process(Path("/tmp/photo.jpg"))
        assert result.photo_path == "/tmp/photo.jpg"
