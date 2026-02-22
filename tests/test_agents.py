"""Tests for agent output schemas and basic functionality.

These tests verify structured output schemas without requiring live model
inference. They test the Pydantic models and data flow, not LLM quality.
"""

from src.agents.estimation import EstimateBreakdown, LineItem
from src.agents.image_analysis import RoomAssessment
from src.agents.scope import ScopeExtractionResult, ScopeItem


class TestScopeModels:
    """Test Scope Agent data models."""

    def test_scope_item_creation(self) -> None:
        item = ScopeItem(
            room="kitchen",
            category="countertop",
            description="Replace granite countertops with quartz",
            quantity_estimate=45.0,
            unit="sq_ft",
            material_selection="Cambria Ella",
        )
        assert item.room == "kitchen"
        assert item.quantity_estimate == 45.0

    def test_scope_extraction_result(self) -> None:
        result = ScopeExtractionResult(
            project_type="kitchen_remodel",
            rooms=["kitchen"],
            scope_items=[
                ScopeItem(
                    room="kitchen",
                    category="demolition",
                    description="Remove existing countertops and backsplash",
                ),
            ],
            missing_info=["Kitchen dimensions not specified"],
            assumptions=["Standard 8ft ceiling height"],
        )
        assert len(result.scope_items) == 1
        assert len(result.missing_info) == 1


class TestEstimationModels:
    """Test Estimation Agent data models."""

    def test_line_item(self) -> None:
        item = LineItem(
            description="Porcelain tile 12x24",
            category="material",
            quantity=110.0,
            unit="sq_ft",
            unit_cost=4.50,
            waste_factor=0.10,
            total=495.0,
        )
        assert item.total == 495.0

    def test_estimate_breakdown(self) -> None:
        breakdown = EstimateBreakdown(
            project_type="tile_floor",
            line_items=[
                LineItem(
                    description="Tile",
                    category="material",
                    quantity=100,
                    unit="sq_ft",
                    unit_cost=4.50,
                    total=450.0,
                ),
                LineItem(
                    description="Labor",
                    category="labor",
                    quantity=100,
                    unit="sq_ft",
                    unit_cost=8.00,
                    total=800.0,
                ),
            ],
            subtotal_materials=450.0,
            subtotal_labor=800.0,
            total=1250.0,
        )
        assert breakdown.total == 1250.0
        assert len(breakdown.line_items) == 2


class TestImageAnalysisModels:
    """Test Image Analysis Agent data models."""

    def test_room_assessment(self) -> None:
        assessment = RoomAssessment(
            room_type="bathroom",
            dimensions_estimate={"width_ft": 8.0, "length_ft": 10.0, "height_ft": 8.0},
            materials=[{"type": "tile", "material": "ceramic", "condition": "fair", "location": "floor"}],
            fixtures=[{"type": "toilet", "brand": "Kohler", "condition": "good"}],
            surfaces=[{"location": "floor", "material": "ceramic_tile", "condition": "fair"}],
            condition_notes=["Grout needs replacement", "Minor water staining near tub"],
            demolition_items=["Existing floor tile", "Vanity"],
            confidence=0.85,
        )
        assert assessment.room_type == "bathroom"
        assert assessment.confidence == 0.85
        assert len(assessment.materials) == 1
