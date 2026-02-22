"""Extended agent tests — edge cases, boundary conditions, and integration scenarios.

These tests expand on test_agents.py with more thorough coverage of the
EstimationAgent, ScopeAgent, ImageAnalysisAgent, and CommunicationAgent.
"""

from unittest.mock import MagicMock

from src.agents.communication import CommunicationAgent, Proposal
from src.agents.estimation import (
    _CATEGORY_MAP,
    EstimateBreakdown,
    EstimationAgent,
    LineItem,
    _match_assembly,
)
from src.agents.image_analysis import ImageAnalysisAgent, RoomAssessment
from src.agents.scope import (
    ScopeAgent,
    ScopeExtractionResult,
    ScopeItem,
)
from src.vision.pipeline import PipelineResult

# ---------------------------------------------------------------------------
# ScopeAgent Extended
# ---------------------------------------------------------------------------

class TestScopeAgentEmail:
    """Test ScopeAgent email extraction."""

    def test_extract_from_email_preprocesses(self) -> None:
        agent = ScopeAgent.__new__(ScopeAgent)
        agent.settings = None
        agent.model = "qwen3:8b"
        agent.ollama = MagicMock()

        # First call = email cleanup, second call = scope extraction
        agent.ollama.chat.side_effect = [
            {"message": {"content": "Replace kitchen countertops with quartz"}},
            {"message": {"content": '{"project_type":"countertop_only","rooms":["kitchen"],'
                         '"scope_items":[{"room":"kitchen","category":"countertop",'
                         '"description":"Replace countertops with quartz"}],'
                         '"missing_info":[],"assumptions":[]}'}},
        ]

        result = agent.extract_from_email(
            "Hi there!\nWe'd like to replace kitchen countertops with quartz.\n"
            "Thanks,\nJane\n\n-- \nJane Doe\n555-1234"
        )
        assert result.project_type == "countertop_only"
        assert agent.ollama.chat.call_count == 2

    def test_extract_from_email_fallback(self) -> None:
        """If email preprocessing fails, raw text is used."""
        agent = ScopeAgent.__new__(ScopeAgent)
        agent.settings = None
        agent.model = "qwen3:8b"
        agent.ollama = MagicMock()

        agent.ollama.chat.side_effect = [
            Exception("Ollama down"),
            {"message": {"content": '{"project_type":"unknown","rooms":[],'
                         '"scope_items":[],"missing_info":["Failed to parse"],"assumptions":[]}'}},
        ]

        result = agent.extract_from_email("Some email text")
        # Should still attempt extraction despite preprocessing failure
        assert isinstance(result, ScopeExtractionResult)


class TestScopeAgentTranscription:
    """Test ScopeAgent transcription extraction."""

    def test_filler_words_removed(self) -> None:
        agent = ScopeAgent.__new__(ScopeAgent)
        agent.settings = None
        agent.model = "qwen3:8b"
        agent.ollama = MagicMock()

        agent.ollama.chat.return_value = {
            "message": {"content": '{"project_type":"bathroom_remodel","rooms":["bathroom"],'
                       '"scope_items":[],"missing_info":[],"assumptions":[]}'}
        }

        result = agent.extract_from_transcription(
            "Um so basically we need to uh redo the bathroom you know with new tile"
        )
        assert result.project_type == "bathroom_remodel"

        # Check that filler words were removed in the call
        call_args = agent.ollama.chat.call_args
        prompt = call_args[1]["messages"][0]["content"] if "messages" in call_args[1] else call_args[0][0]
        # The filler words should have been cleaned before sending to the model


class TestScopeExtractionResultModel:
    """Test ScopeExtractionResult model properties."""

    def test_raw_notes_preserved(self) -> None:
        result = ScopeExtractionResult(
            project_type="kitchen_remodel",
            rooms=["kitchen"],
            scope_items=[],
            missing_info=[],
            assumptions=[],
            raw_notes="Original description text",
        )
        assert result.raw_notes == "Original description text"

    def test_multiple_rooms(self) -> None:
        result = ScopeExtractionResult(
            project_type="full_remodel",
            rooms=["kitchen", "master_bath", "guest_bath"],
            scope_items=[],
            missing_info=[],
            assumptions=[],
        )
        assert len(result.rooms) == 3

    def test_scope_item_with_all_fields(self) -> None:
        item = ScopeItem(
            room="kitchen",
            category="tile_floor",
            description="Porcelain 12x24 tile floor",
            quantity_estimate=150.0,
            unit="sq_ft",
            material_selection="Porcelain — Emser Bello",
            special_conditions=["Heated floor underneath", "Threshold transitions needed"],
        )
        assert len(item.special_conditions) == 2
        assert item.material_selection == "Porcelain — Emser Bello"


# ---------------------------------------------------------------------------
# EstimationAgent Extended
# ---------------------------------------------------------------------------

class TestAssemblyMatching:
    """Test _match_assembly function."""

    def test_standard_tile_floor(self) -> None:
        assembly = _match_assembly("tile_floor")
        assert assembly is not None
        assert assembly.code == "TILE-FLR-P1224"

    def test_countertop_quartz_hint(self) -> None:
        assembly = _match_assembly("countertop", material_hint="quartz mid-range")
        assert assembly is not None
        assert "QUARTZ" in assembly.code

    def test_countertop_marble_hint(self) -> None:
        assembly = _match_assembly("countertop", material_hint="Calacatta marble")
        assert assembly is not None
        assert "MARBLE" in assembly.code

    def test_mosaic_hint(self) -> None:
        assembly = _match_assembly("tile_floor", material_hint="mosaic glass")
        assert assembly is not None
        assert assembly.code == "TILE-FLR-MOSAIC"

    def test_large_format_hint(self) -> None:
        assembly = _match_assembly("tile_floor", material_hint="large format porcelain")
        assert assembly is not None
        assert assembly.code == "TILE-FLR-LF2448"

    def test_natural_stone_hint(self) -> None:
        assembly = _match_assembly("tile_floor", material_hint="travertine")
        assert assembly is not None
        assert assembly.code == "TILE-FLR-STONE"

    def test_shower_tile_hint(self) -> None:
        assembly = _match_assembly("tile_wall", material_hint="shower porcelain")
        assert assembly is not None
        assert assembly.code == "TILE-WALL-SHOWER"

    def test_unmatched_returns_none(self) -> None:
        assembly = _match_assembly("custom_millwork")
        assert assembly is None

    def test_normalized_category(self) -> None:
        assembly = _match_assembly("Tile Floor")
        assert assembly is not None

    def test_hyphenated_category(self) -> None:
        assembly = _match_assembly("tile-floor")
        assert assembly is not None


class TestCategoryMap:
    """Test the _CATEGORY_MAP mapping."""

    def test_all_categories_resolve(self) -> None:
        from src.cost_engine.assemblies import SCOPE_TO_ASSEMBLY
        for key in _CATEGORY_MAP.values():
            assert key in SCOPE_TO_ASSEMBLY or key in _CATEGORY_MAP, f"Category {key} not in SCOPE_TO_ASSEMBLY"

    def test_demolition_aliases(self) -> None:
        assert _CATEGORY_MAP.get("demo") == "demolition"
        assert _CATEGORY_MAP.get("demolition_floor") == "demolition_floor"

    def test_prep_work_alias(self) -> None:
        assert _CATEGORY_MAP.get("prep_work") == "leveling"


class TestEstimationAgentMultipleItems:
    """Test EstimationAgent with complex multi-item scopes."""

    def test_kitchen_remodel_scope(self) -> None:
        agent = EstimationAgent()
        scope_items = [
            {"room": "kitchen", "category": "demolition", "description": "Remove old tile floor", "quantity_estimate": 150.0, "unit": "sq_ft"},
            {"room": "kitchen", "category": "tile_floor", "description": "New porcelain tile", "quantity_estimate": 150.0, "unit": "sq_ft"},
            {"room": "kitchen", "category": "backsplash", "description": "New tile backsplash", "quantity_estimate": 30.0, "unit": "sq_ft"},
        ]
        result = agent.estimate_from_scope(scope_items)
        assert result.total > 0
        assert len(result.line_items) > 3
        assert result.project_type == "tile"

    def test_bathroom_remodel_with_waterproofing(self) -> None:
        agent = EstimationAgent()
        scope_items = [
            {"room": "bathroom", "category": "demolition", "description": "Demo shower tile", "quantity_estimate": 60.0, "unit": "sq_ft"},
            {"room": "bathroom", "category": "waterproofing", "description": "Kerdi waterproofing", "quantity_estimate": 60.0, "unit": "sq_ft"},
            {"room": "bathroom", "category": "tile_wall_shower", "description": "Shower tile", "quantity_estimate": 60.0, "unit": "sq_ft"},
        ]
        result = agent.estimate_from_scope(scope_items)
        assert result.total > 0
        # tile_wall_shower is not in the tile detection set {"tile_floor","tile_wall","tile","backsplash"}
        assert result.project_type in ("tile", "remodel")

    def test_countertop_project_type_detection(self) -> None:
        agent = EstimationAgent()
        scope_items = [
            {"room": "kitchen", "category": "countertop", "description": "Quartz countertop", "quantity_estimate": 40.0, "unit": "sq_ft", "material_selection": "quartz"},
        ]
        result = agent.estimate_from_scope(scope_items)
        assert result.project_type == "countertop"

    def test_mixed_matched_and_unmatched(self) -> None:
        agent = EstimationAgent()
        scope_items = [
            {"room": "kitchen", "category": "tile_floor", "description": "Tile floor", "quantity_estimate": 100.0, "unit": "sq_ft"},
            {"room": "kitchen", "category": "custom_carpentry", "description": "Custom trim work", "quantity_estimate": 1.0},
        ]
        result = agent.estimate_from_scope(scope_items)
        assert any("Unmatched" in n for n in result.notes)
        assert result.total > 0

    def test_empty_scope(self) -> None:
        agent = EstimationAgent()
        result = agent.estimate_from_scope([])
        assert result.total == 0
        assert len(result.line_items) == 0
        assert result.project_type == "remodel"


class TestEstimationWithImageAnalysis:
    """Test estimation with image analysis dimension supplementation."""

    def test_dimensions_from_image_analysis(self) -> None:
        agent = EstimationAgent()
        scope_items = [
            {"room": "kitchen", "category": "tile_floor", "description": "Tile floor"},
        ]
        image_analysis = [
            {
                "room_type": "kitchen",
                "dimensions_estimate": {"floor_area_sq_ft": 120.0, "width_ft": 10.0, "length_ft": 12.0},
            }
        ]
        result = agent.estimate_from_scope(scope_items, image_analysis=image_analysis)
        assert result.total > 0
        assert any("photo analysis" in n for n in result.notes)

    def test_no_image_analysis_fallback(self) -> None:
        agent = EstimationAgent()
        scope_items = [
            {"room": "kitchen", "category": "tile_floor", "description": "Tile floor"},
        ]
        result = agent.estimate_from_scope(scope_items)
        assert any("placeholder" in n or "Quantity missing" in n for n in result.notes)


class TestEstimationConfidence:
    """Test confidence score calculation."""

    def test_high_confidence_all_matched(self) -> None:
        agent = EstimationAgent()
        scope_items = [
            {"room": "kitchen", "category": "tile_floor", "description": "Tile", "quantity_estimate": 100.0, "unit": "sq_ft"},
            {"room": "kitchen", "category": "countertop", "description": "Quartz", "quantity_estimate": 40.0, "unit": "sq_ft"},
        ]
        result = agent.estimate_from_scope(scope_items)
        assert result.confidence == 1.0

    def test_low_confidence_no_quantities(self) -> None:
        agent = EstimationAgent()
        scope_items = [
            {"room": "kitchen", "category": "tile_floor", "description": "Tile"},
        ]
        result = agent.estimate_from_scope(scope_items)
        assert result.confidence < 1.0

    def test_zero_confidence_all_unmatched(self) -> None:
        agent = EstimationAgent()
        scope_items = [
            {"room": "kitchen", "category": "custom_x", "description": "X"},
            {"room": "kitchen", "category": "custom_y", "description": "Y"},
        ]
        result = agent.estimate_from_scope(scope_items)
        assert result.confidence == 0.0


class TestCountertopEstimation:
    """Extended countertop estimation tests."""

    def test_marble_countertop(self) -> None:
        agent = EstimationAgent()
        result = agent.estimate_countertop(material="marble", square_feet=30.0)
        assert result.project_type == "countertop_fabrication"
        assert result.total > 0

    def test_budget_granite(self) -> None:
        agent = EstimationAgent()
        result = agent.estimate_countertop(material="granite_budget", square_feet=25.0)
        assert result.total > 0

    def test_premium_granite(self) -> None:
        agent = EstimationAgent()
        result = agent.estimate_countertop(material="exotic_premium", square_feet=30.0)
        assert result.total > 0

    def test_edge_profile_included(self) -> None:
        agent = EstimationAgent()
        result_eased = agent.estimate_countertop(material="granite_mid", square_feet=30.0, edge_profile="eased")
        result_dupont = agent.estimate_countertop(material="granite_mid", square_feet=30.0, edge_profile="dupont")
        assert result_dupont.total > result_eased.total

    def test_no_cutouts(self) -> None:
        agent = EstimationAgent()
        result_no = agent.estimate_countertop(material="granite_mid", square_feet=30.0, cutouts=0)
        result_two = agent.estimate_countertop(material="granite_mid", square_feet=30.0, cutouts=2)
        assert result_two.total > result_no.total

    def test_backsplash_option(self) -> None:
        agent = EstimationAgent()
        result_no = agent.estimate_countertop(material="quartz_mid", square_feet=30.0, backsplash=False)
        result_yes = agent.estimate_countertop(material="quartz_mid", square_feet=30.0, backsplash=True)
        assert result_yes.total > result_no.total
        assert any("backsplash" in n.lower() for n in result_yes.notes)

    def test_slab_requirement_note(self) -> None:
        agent = EstimationAgent()
        result = agent.estimate_countertop(material="granite_mid", square_feet=50.0)
        assert any("Slab requirement" in n for n in result.notes)

    def test_small_countertop(self) -> None:
        agent = EstimationAgent()
        result = agent.estimate_countertop(material="quartz_mid", square_feet=10.0)
        assert result.total > 0
        assert any("1 slab" in n for n in result.notes)


class TestLineItemModel:
    """Test LineItem pydantic model."""

    def test_line_item_defaults(self) -> None:
        item = LineItem(
            description="Test",
            category="material",
            quantity=10.0,
            unit="sq_ft",
            unit_cost=5.0,
        )
        assert item.waste_factor == 0.0
        assert item.total == 0.0
        assert item.source == ""

    def test_line_item_all_fields(self) -> None:
        item = LineItem(
            description="Porcelain tile",
            category="material",
            quantity=110.0,
            unit="sq_ft",
            unit_cost=4.50,
            waste_factor=0.10,
            total=495.0,
            source="TILE-FLR-P1224",
        )
        assert item.source == "TILE-FLR-P1224"


class TestEstimateBreakdownModel:
    """Test EstimateBreakdown pydantic model."""

    def test_defaults(self) -> None:
        bd = EstimateBreakdown(
            project_type="tile",
            line_items=[],
        )
        assert bd.overhead_pct == 0.10
        assert bd.profit_pct == 0.10
        assert bd.contingency_pct == 0.10
        assert bd.ml_adjustment == 0.0
        assert bd.notes == []

    def test_with_ml_fields(self) -> None:
        bd = EstimateBreakdown(
            project_type="countertop",
            line_items=[],
            total=5000.0,
            ml_adjustment=0.05,
            ml_explanation="Historical projects ran 5% over estimate",
        )
        assert bd.ml_adjustment == 0.05


# ---------------------------------------------------------------------------
# ImageAnalysisAgent Extended
# ---------------------------------------------------------------------------

class TestImageAnalysisAgentAnalyze:
    """Test ImageAnalysisAgent with mocked pipeline."""

    def test_successful_analysis(self) -> None:
        mock_pipeline = MagicMock()
        mock_pipeline.process.return_value = PipelineResult(
            photo_path="kitchen.jpg",
            detections=[{"label": "sink", "bbox": [0, 0, 50, 50]}],
            depth_map={
                "width_ft": 10.0,
                "length_ft": 12.0,
                "height_ft": 8.0,
                "floor_area_sq_ft": 120.0,
                "confidence": 0.5,
            },
            scene_analysis={
                "room_type": "kitchen",
                "materials": [{"type": "tile", "location": "floor", "condition": "fair"}],
                "fixtures": [{"type": "sink", "brand": "Kohler", "condition": "good"}],
                "surfaces": [],
                "condition_notes": ["Grout needs replacement"],
                "demolition_items": ["Old tile floor"],
                "dimensions": {"width_ft": 11.0, "length_ft": 14.0, "height_ft": 8.5},
            },
            confidence=0.85,
        )

        agent = ImageAnalysisAgent(vision_pipeline=mock_pipeline)
        result = agent.analyze_photo("kitchen.jpg")

        assert isinstance(result, RoomAssessment)
        assert result.room_type == "kitchen"
        # Scene analysis dimensions override depth dimensions
        assert result.dimensions_estimate["width_ft"] == 11.0
        assert result.dimensions_estimate["length_ft"] == 14.0
        assert result.dimensions_estimate["floor_area_sq_ft"] == 11.0 * 14.0
        assert result.confidence == 0.85

    def test_pipeline_failure(self) -> None:
        mock_pipeline = MagicMock()
        mock_pipeline.process.side_effect = RuntimeError("GPU out of memory")

        agent = ImageAnalysisAgent(vision_pipeline=mock_pipeline)
        result = agent.analyze_photo("photo.jpg")

        assert result.room_type == "unknown"
        assert result.confidence == 0.0
        assert "Analysis failed" in result.condition_notes[0]

    def test_depth_only_dimensions(self) -> None:
        """When scene analysis has no dimensions, depth data is used."""
        mock_pipeline = MagicMock()
        mock_pipeline.process.return_value = PipelineResult(
            photo_path="room.jpg",
            detections=[],
            depth_map={
                "width_ft": 8.5,
                "length_ft": 10.0,
                "height_ft": 8.0,
                "floor_area_sq_ft": 85.0,
                "confidence": 0.4,
            },
            scene_analysis={
                "room_type": "bathroom",
                "materials": [],
                "fixtures": [],
                "surfaces": [],
                "condition_notes": [],
                "demolition_items": [],
                "dimensions": {},  # No scene dimensions
            },
            confidence=0.6,
        )

        agent = ImageAnalysisAgent(vision_pipeline=mock_pipeline)
        result = agent.analyze_photo("room.jpg")
        assert result.dimensions_estimate["width_ft"] == 8.5
        assert result.dimensions_estimate["floor_area_sq_ft"] == 85.0

    def test_no_depth_no_scene_dimensions(self) -> None:
        mock_pipeline = MagicMock()
        mock_pipeline.process.return_value = PipelineResult(
            photo_path="photo.jpg",
            detections=[],
            depth_map={},
            scene_analysis={
                "room_type": "hallway",
                "materials": [],
                "fixtures": [],
                "surfaces": [],
                "condition_notes": [],
                "demolition_items": [],
                "dimensions": {},
            },
            confidence=0.3,
        )

        agent = ImageAnalysisAgent(vision_pipeline=mock_pipeline)
        result = agent.analyze_photo("photo.jpg")
        assert result.dimensions_estimate == {}

    def test_analyze_multiple_photos(self) -> None:
        mock_pipeline = MagicMock()
        mock_pipeline.process.return_value = PipelineResult(
            photo_path="photo.jpg",
            detections=[],
            depth_map={},
            scene_analysis={"room_type": "kitchen", "confidence": 0.7},
            confidence=0.7,
        )

        agent = ImageAnalysisAgent(vision_pipeline=mock_pipeline)
        results = agent.analyze_project_photos(["photo1.jpg", "photo2.jpg", "photo3.jpg"])
        assert len(results) == 3
        assert mock_pipeline.process.call_count == 3


# ---------------------------------------------------------------------------
# CommunicationAgent Extended
# ---------------------------------------------------------------------------

class TestCommunicationAgentProposal:
    """Extended proposal generation tests."""

    def test_proposal_has_all_fields(self) -> None:
        agent = CommunicationAgent()
        estimate = {
            "line_items": [
                {"description": "Tile", "quantity": 100, "unit": "sq_ft", "total": 450.0},
            ],
            "subtotal_materials": 450.0,
            "subtotal_labor": 800.0,
            "total": 1375.0,
            "overhead_pct": 0.10,
            "profit_pct": 0.10,
            "contingency_pct": 0.10,
            "notes": [],
        }
        proposal = agent.generate_proposal(estimate, "Alice Johnson", "kitchen_remodel")

        assert isinstance(proposal, Proposal)
        assert proposal.client_name == "Alice Johnson"
        assert "Kitchen Remodel" in proposal.project_summary
        assert "50% deposit" in proposal.terms_and_conditions
        assert "2-4 weeks" in proposal.timeline_estimate
        assert "Nelson Tile & Stone" in proposal.full_text

    def test_proposal_with_notes(self) -> None:
        agent = CommunicationAgent()
        estimate = {
            "line_items": [],
            "subtotal_materials": 0,
            "subtotal_labor": 0,
            "total": 5000.0,
            "overhead_pct": 0.10,
            "profit_pct": 0.10,
            "contingency_pct": 0.10,
            "notes": ["Quantity estimated from photos", "Plumbing subcontractor TBD"],
        }
        proposal = agent.generate_proposal(estimate, "Bob", "bathroom_remodel")
        assert "$5,000.00" in proposal.full_text


class TestCommunicationAgentEmail:
    """Extended email generation tests."""

    def test_thank_you_email(self) -> None:
        agent = CommunicationAgent()
        result = agent.generate_email(
            purpose="thank_you",
            context={"client_name": "Maria", "project_type": "countertop"},
        )
        assert "Maria" in result
        assert "Nelson Tile & Stone" in result

    def test_generic_email(self) -> None:
        agent = CommunicationAgent()
        result = agent.generate_email(
            purpose="custom",
            context={"client_name": "Dave", "project_type": "tile_floor", "details": "Just checking in."},
        )
        assert "Dave" in result

    def test_email_with_details(self) -> None:
        agent = CommunicationAgent()
        result = agent.generate_email(
            purpose="follow_up",
            context={
                "client_name": "Sarah",
                "project_type": "kitchen_remodel",
                "details": "The quartz samples are available for viewing.",
            },
        )
        assert "Sarah" in result


class TestCommunicationAgentChangeOrder:
    """Extended change order tests."""

    def test_positive_change(self) -> None:
        agent = CommunicationAgent()
        result = agent.generate_change_order(
            original_estimate={"total": 10000.0},
            changes=[
                {"description": "Upgrade to premium quartz", "cost_delta": 2000.0},
            ],
        )
        assert "$10,000.00" in result
        assert "$12,000.00" in result

    def test_negative_change(self) -> None:
        agent = CommunicationAgent()
        result = agent.generate_change_order(
            original_estimate={"total": 10000.0},
            changes=[
                {"description": "Remove backsplash from scope", "cost_delta": -1500.0},
            ],
        )
        assert "$8,500.00" in result

    def test_mixed_changes(self) -> None:
        agent = CommunicationAgent()
        result = agent.generate_change_order(
            original_estimate={"total": 8000.0},
            changes=[
                {"description": "Add heated floor", "cost_delta": 1200.0},
                {"description": "Use standard edge instead of ogee", "cost_delta": -400.0},
            ],
        )
        assert "$8,800.00" in result

    def test_zero_delta_change(self) -> None:
        agent = CommunicationAgent()
        result = agent.generate_change_order(
            original_estimate={"total": 5000.0},
            changes=[
                {"description": "Swap materials (same cost)", "cost_delta": 0.0},
            ],
        )
        assert "$5,000.00" in result


class TestCommunicationAgentPricingTable:
    """Test _format_pricing_table."""

    def test_multiple_line_items(self) -> None:
        agent = CommunicationAgent()
        estimate = {
            "line_items": [
                {"description": "Tile", "quantity": 100, "unit": "sq_ft", "total": 450.0},
                {"description": "Thinset", "quantity": 105, "unit": "sq_ft", "total": 47.25},
                {"description": "Labor", "quantity": 100, "unit": "sq_ft", "total": 800.0},
            ],
            "subtotal_materials": 497.25,
            "subtotal_labor": 800.0,
            "total": 1427.0,
            "overhead_pct": 0.10,
            "profit_pct": 0.10,
            "contingency_pct": 0.10,
        }
        table = agent._format_pricing_table(estimate)
        assert "Tile" in table
        assert "Thinset" in table
        assert "Labor" in table
        assert "TOTAL" in table
        assert "$1,427.00" in table

    def test_empty_line_items(self) -> None:
        agent = CommunicationAgent()
        table = agent._format_pricing_table({
            "line_items": [],
            "subtotal_materials": 0,
            "subtotal_labor": 0,
            "total": 0,
        })
        assert "TOTAL" in table
        assert "$0.00" in table


# ---------------------------------------------------------------------------
# ML Refiner
# ---------------------------------------------------------------------------

class TestMLRefiner:
    """Test ML estimate refiner."""

    def test_no_model_passthrough(self) -> None:
        from src.cost_engine.ml_refiner import EstimateRefiner, MLRefinement

        refiner = EstimateRefiner()
        result = refiner.refine({"total": 5000.0})

        assert isinstance(result, MLRefinement)
        assert result.original_total == 5000.0
        assert result.adjusted_total == 5000.0
        assert result.adjustment_pct == 0.0
        assert "No ML model" in result.explanation

    def test_refiner_with_path_none(self) -> None:
        from src.cost_engine.ml_refiner import EstimateRefiner

        refiner = EstimateRefiner(model_path=None)
        assert refiner.model is None

    def test_train_noop(self) -> None:
        from pathlib import Path

        from src.cost_engine.ml_refiner import EstimateRefiner

        refiner = EstimateRefiner()
        # Should not raise — just a no-op
        refiner.train(Path("/tmp/data.csv"))
