"""Tests for agent output schemas and functionality.

These tests verify structured output schemas and agent logic without
requiring live model inference. They use mocked Ollama/Claude responses.
"""

from unittest.mock import MagicMock

from src.agents.communication import CommunicationAgent, Proposal
from src.agents.estimation import EstimateBreakdown, EstimationAgent, LineItem
from src.agents.image_analysis import RoomAssessment
from src.agents.scope import ScopeAgent, ScopeExtractionResult, ScopeItem


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

    def test_scope_item_defaults(self) -> None:
        item = ScopeItem(
            room="bathroom",
            category="tile_floor",
            description="Install new floor tile",
        )
        assert item.quantity_estimate is None
        assert item.unit is None
        assert item.material_selection is None
        assert item.special_conditions == []


class TestScopeAgent:
    """Test Scope Agent with mocked Ollama."""

    def test_extract_scope_with_mock(self) -> None:
        mock_response = {
            "message": {
                "content": '{"project_type":"kitchen_remodel","rooms":["kitchen"],'
                '"scope_items":[{"room":"kitchen","category":"countertop",'
                '"description":"Replace countertops with quartz",'
                '"quantity_estimate":40.0,"unit":"sq_ft",'
                '"material_selection":"quartz","special_conditions":[]}],'
                '"missing_info":["Exact dimensions needed"],'
                '"assumptions":["Standard ceiling height"]}'
            }
        }

        agent = ScopeAgent.__new__(ScopeAgent)
        agent.settings = None
        agent.model = "qwen3:8b"
        agent.ollama = MagicMock()
        agent.ollama.chat.return_value = mock_response

        result = agent.extract_scope("Replace kitchen countertops with quartz")
        assert result.project_type == "kitchen_remodel"
        assert len(result.scope_items) == 1
        assert result.scope_items[0].category == "countertop"
        assert result.scope_items[0].quantity_estimate == 40.0

    def test_extract_scope_handles_bad_json(self) -> None:
        agent = ScopeAgent.__new__(ScopeAgent)
        agent.settings = None
        agent.model = "qwen3:8b"
        agent.ollama = MagicMock()
        agent.ollama.chat.return_value = {"message": {"content": "not valid json"}}

        result = agent.extract_scope("Some description")
        assert result.project_type == "unknown"
        assert len(result.missing_info) == 1

    def test_extract_scope_strips_think_tags(self) -> None:
        mock_response = {
            "message": {
                "content": '<think>Let me analyze this...</think>'
                '{"project_type":"bathroom_remodel","rooms":["bathroom"],'
                '"scope_items":[],"missing_info":[],"assumptions":[]}'
            }
        }

        agent = ScopeAgent.__new__(ScopeAgent)
        agent.settings = None
        agent.model = "qwen3:8b"
        agent.ollama = MagicMock()
        agent.ollama.chat.return_value = mock_response

        result = agent.extract_scope("Bathroom remodel")
        assert result.project_type == "bathroom_remodel"


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


class TestEstimationAgent:
    """Test Estimation Agent logic with real cost engine."""

    def test_estimate_from_scope_items(self) -> None:
        agent = EstimationAgent()
        scope_items = [
            {
                "room": "kitchen",
                "category": "tile_floor",
                "description": "Install porcelain tile floor",
                "quantity_estimate": 150.0,
                "unit": "sq_ft",
            },
        ]
        result = agent.estimate_from_scope(scope_items)
        assert result.project_type == "tile"
        assert result.total > 0
        assert len(result.line_items) > 0
        assert result.subtotal_materials > 0
        assert result.subtotal_labor > 0

    def test_estimate_with_countertop(self) -> None:
        agent = EstimationAgent()
        scope_items = [
            {
                "room": "kitchen",
                "category": "countertop",
                "description": "Replace with quartz",
                "quantity_estimate": 40.0,
                "unit": "sq_ft",
                "material_selection": "quartz",
            },
        ]
        result = agent.estimate_from_scope(scope_items)
        assert result.project_type == "countertop"
        assert result.total > 0

    def test_estimate_countertop_specialized(self) -> None:
        agent = EstimationAgent()
        result = agent.estimate_countertop(
            material="granite_mid",
            square_feet=35.0,
            edge_profile="ogee",
            cutouts=2,
            backsplash=True,
        )
        assert result.project_type == "countertop_fabrication"
        assert result.total > 0
        assert len(result.line_items) > 0
        assert any("ogee" in li.description.lower() for li in result.line_items)
        assert any("cutout" in li.description.lower() for li in result.line_items)
        assert any("backsplash" in li.description.lower() for li in result.line_items)

    def test_estimate_unmatched_category(self) -> None:
        agent = EstimationAgent()
        scope_items = [
            {
                "room": "kitchen",
                "category": "custom_millwork",
                "description": "Custom cabinets",
                "quantity_estimate": 1.0,
            },
        ]
        result = agent.estimate_from_scope(scope_items)
        assert any("Unmatched" in note for note in result.notes)

    def test_estimate_missing_quantity(self) -> None:
        agent = EstimationAgent()
        scope_items = [
            {
                "room": "kitchen",
                "category": "tile_floor",
                "description": "Tile floor",
            },
        ]
        result = agent.estimate_from_scope(scope_items)
        assert any("Quantity missing" in note or "placeholder" in note for note in result.notes)

    def test_countertop_quartz_vs_granite(self) -> None:
        agent = EstimationAgent()
        quartz = agent.estimate_countertop(material="quartz_premium", square_feet=30.0)
        granite_mid = agent.estimate_countertop(material="granite_mid", square_feet=30.0)
        assert quartz.total > granite_mid.total


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


class TestCommunicationAgent:
    """Test Communication Agent with fallback templates."""

    def test_proposal_without_claude(self) -> None:
        agent = CommunicationAgent()
        estimate = {
            "line_items": [
                {"description": "Tile", "quantity": 100, "unit": "sq_ft", "total": 450.0},
                {"description": "Labor", "quantity": 100, "unit": "sq_ft", "total": 800.0},
            ],
            "subtotal_materials": 450.0,
            "subtotal_labor": 800.0,
            "total": 1625.0,
            "overhead_pct": 0.10,
            "profit_pct": 0.10,
            "contingency_pct": 0.10,
            "notes": [],
        }
        proposal = agent.generate_proposal(estimate, "John Smith", "tile_floor")
        assert isinstance(proposal, Proposal)
        assert proposal.client_name == "John Smith"
        assert "$1,625.00" in proposal.full_text
        assert "Nelson Tile & Stone" in proposal.full_text

    def test_email_fallback(self) -> None:
        agent = CommunicationAgent()
        result = agent.generate_email(
            purpose="follow_up",
            context={"client_name": "Jane", "project_type": "kitchen_remodel"},
        )
        assert "Jane" in result
        assert "Nelson Tile & Stone" in result

    def test_change_order_fallback(self) -> None:
        agent = CommunicationAgent()
        result = agent.generate_change_order(
            original_estimate={"total": 5000.0},
            changes=[
                {"description": "Upgrade to premium tile", "cost_delta": 800.0},
                {"description": "Remove backsplash", "cost_delta": -300.0},
            ],
        )
        assert "$5,000.00" in result
        assert "$5,500.00" in result
        assert "premium tile" in result.lower()

    def test_pricing_table_format(self) -> None:
        agent = CommunicationAgent()
        estimate = {
            "line_items": [
                {"description": "Tile", "quantity": 100, "unit": "sq_ft", "total": 450.0},
            ],
            "subtotal_materials": 450.0,
            "subtotal_labor": 0.0,
            "total": 495.0,
            "overhead_pct": 0.10,
            "profit_pct": 0.10,
            "contingency_pct": 0.10,
        }
        table = agent._format_pricing_table(estimate)
        assert "Tile" in table
        assert "$450.00" in table
        assert "TOTAL" in table
