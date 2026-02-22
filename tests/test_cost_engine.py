"""Tests for the assembly-based cost engine."""

from src.cost_engine.assemblies import (
    ASSEMBLY_REGISTRY,
    COUNTERTOP_GRANITE_MID,
    COUNTERTOP_QUARTZ_MID,
    DEMO_TILE_FLOOR,
    TILE_FLOOR_MOSAIC,
    TILE_FLOOR_PORCELAIN_12X24,
    TILE_FLOOR_PORCELAIN_LARGE_FORMAT,
    WATERPROOF_SHOWER,
    Assembly,
    AssemblyComponent,
    CostCategory,
    get_assemblies_by_category,
    get_assembly,
)
from src.cost_engine.regional import (
    BEND_OR,
    PORTLAND_OR,
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

    def test_large_format_tile(self) -> None:
        result = TILE_FLOOR_PORCELAIN_LARGE_FORMAT.calculate(50.0)
        assert result["total"] > 0
        assert result["labor"] > 0
        # Large format has higher labor rate than standard
        lf_labor_per_sqft = result["labor"] / 50.0
        std_result = TILE_FLOOR_PORCELAIN_12X24.calculate(50.0)
        std_labor_per_sqft = std_result["labor"] / 50.0
        assert lf_labor_per_sqft > std_labor_per_sqft

    def test_mosaic_tile(self) -> None:
        result = TILE_FLOOR_MOSAIC.calculate(20.0)
        assert result["total"] > 0
        assert result["material"] > 0
        # Mosaic is more expensive per sqft than standard porcelain
        mosaic_per_sqft = result["total"] / 20.0
        std_result = TILE_FLOOR_PORCELAIN_12X24.calculate(20.0)
        std_per_sqft = std_result["total"] / 20.0
        assert mosaic_per_sqft > std_per_sqft

    def test_demolition_assembly(self) -> None:
        result = DEMO_TILE_FLOOR.calculate(100.0)
        assert result["labor"] > 0
        assert result["material"] > 0  # disposal/hauling
        assert result["total"] > 0

    def test_waterproofing_assembly(self) -> None:
        result = WATERPROOF_SHOWER.calculate(60.0)
        assert result["material"] > 0
        assert result["labor"] > 0
        assert result["total"] > 0

    def test_quartz_countertop(self) -> None:
        result = COUNTERTOP_QUARTZ_MID.calculate(40.0)
        assert result["total"] > 0
        # Quartz mid should be more expensive than granite mid per sqft
        quartz_per_sqft = result["total"] / 40.0
        granite_result = COUNTERTOP_GRANITE_MID.calculate(40.0)
        granite_per_sqft = granite_result["total"] / 40.0
        assert quartz_per_sqft > granite_per_sqft

    def test_line_items_returned(self) -> None:
        result = TILE_FLOOR_PORCELAIN_12X24.calculate(100.0)
        assert len(result["line_items"]) == 4  # tile, thinset, grout, labor
        for li in result["line_items"]:
            assert "description" in li
            assert "category" in li
            assert "total" in li

    def test_waste_factor_applied(self) -> None:
        result = TILE_FLOOR_PORCELAIN_12X24.calculate(100.0)
        tile_item = next(li for li in result["line_items"] if "tile 12x24" in li["description"].lower())
        # 100 sqft + 10% waste = 110 sqft
        assert tile_item["quantity"] == 110.0


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

    def test_portland_baseline(self) -> None:
        adjusted = apply_regional_adjustment(100.0, "labor", PORTLAND_OR)
        assert adjusted == 100.0  # Portland is baseline

    def test_redmond_factors(self) -> None:
        factors = get_regional_factors("redmond_or")
        assert factors.labor_factor == 1.08
        assert factors.transport_surcharge_pct == 0.03

    def test_equipment_passthrough(self) -> None:
        adjusted = apply_regional_adjustment(100.0, "equipment", BEND_OR)
        assert adjusted == 100.0  # no adjustment for equipment


class TestAssemblyRegistry:
    """Test the assembly registry and lookup functions."""

    def test_registry_not_empty(self) -> None:
        assert len(ASSEMBLY_REGISTRY) > 30  # We have 35 assemblies

    def test_lookup_by_code(self) -> None:
        assembly = get_assembly("TILE-FLR-P1224")
        assert assembly is not None
        assert assembly.name == "Tile Floor Installation — Porcelain 12x24"

    def test_lookup_missing_returns_none(self) -> None:
        assert get_assembly("NONEXISTENT") is None

    def test_get_by_category(self) -> None:
        tile_floors = get_assemblies_by_category("tile_floor")
        assert len(tile_floors) >= 4  # standard, large format, mosaic, stone

    def test_countertop_assemblies(self) -> None:
        countertops = get_assemblies_by_category("countertop")
        assert len(countertops) >= 6  # budget/mid/premium granite, quartz mid/prem, marble

    def test_demolition_assemblies(self) -> None:
        demos = get_assemblies_by_category("demolition")
        assert len(demos) >= 4  # floor, wall, countertop, general

    def test_all_assemblies_have_components(self) -> None:
        for code, assembly in ASSEMBLY_REGISTRY.items():
            assert len(assembly.components) > 0, f"Assembly {code} has no components"
