"""Tests for the assembly-based cost engine."""

from src.cost_engine.assemblies import (
    COUNTERTOP_GRANITE_MID,
    TILE_FLOOR_PORCELAIN_12X24,
    Assembly,
    AssemblyComponent,
    CostCategory,
)
from src.cost_engine.regional import (
    BEND_OR,
    apply_regional_adjustment,
    get_regional_factors,
)


class TestAssemblyCalculation:
    """Test assembly-based cost calculations against known reference values."""

    def test_tile_floor_100_sqft(self) -> None:
        result = TILE_FLOOR_PORCELAIN_12X24.calculate(100.0)
        assert result["quantity"] == 100.0
        assert result["unit"] == "sq_ft"
        # Materials: tile (4.50 * 110) + thinset (0.45 * 105) + grout (0.25 * 105)
        assert result["material"] > 0
        # Labor: 8.00 * 100
        assert result["labor"] == 800.0
        assert result["total"] > 0
        assert result["total"] == result["material"] + result["labor"]

    def test_countertop_granite_30_sqft(self) -> None:
        result = COUNTERTOP_GRANITE_MID.calculate(30.0)
        assert result["quantity"] == 30.0
        assert result["material"] > 0
        assert result["labor"] > 0
        assert result["total"] > 0

    def test_zero_quantity(self) -> None:
        result = TILE_FLOOR_PORCELAIN_12X24.calculate(0.0)
        assert result["total"] == 0.0

    def test_custom_assembly(self) -> None:
        assembly = Assembly(
            name="Test Assembly",
            code="TEST-001",
            category="test",
            unit="each",
            components=[
                AssemblyComponent(
                    description="Part A",
                    category=CostCategory.MATERIAL,
                    unit_cost=10.0,
                    unit="each",
                    waste_factor=0.0,
                ),
                AssemblyComponent(
                    description="Labor",
                    category=CostCategory.LABOR,
                    unit_cost=20.0,
                    unit="each",
                ),
            ],
        )
        result = assembly.calculate(5.0)
        assert result["material"] == 50.0
        assert result["labor"] == 100.0
        assert result["total"] == 150.0


class TestRegionalAdjustments:
    """Test regional cost adjustments for Bend, OR."""

    def test_bend_or_exists(self) -> None:
        factors = get_regional_factors("bend_or")
        assert factors.region_code == "bend_or"
        assert factors.sales_tax_rate == 0.0
        assert factors.labor_factor > 1.0

    def test_labor_adjustment(self) -> None:
        adjusted = apply_regional_adjustment(100.0, "labor", BEND_OR)
        assert adjusted == 110.0  # 10% premium

    def test_material_no_sales_tax(self) -> None:
        adjusted = apply_regional_adjustment(100.0, "material", BEND_OR)
        # No sales tax, just transport surcharge (3%)
        assert adjusted > 100.0
        assert adjusted < 110.0

    def test_unknown_region_raises(self) -> None:
        try:
            get_regional_factors("nonexistent")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass
