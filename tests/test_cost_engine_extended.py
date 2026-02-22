"""Extended cost engine tests — assembly calculations, regional adjustments, and edge cases."""


from src.cost_engine.assemblies import (
    ASSEMBLY_REGISTRY,
    BACKER_CEMENT_BOARD,
    CAULKING,
    COUNTERTOP_BACKSPLASH_4IN,
    COUNTERTOP_CUTOUT_STANDARD,
    COUNTERTOP_EDGE_BEVELED,
    COUNTERTOP_EDGE_DUPONT,
    COUNTERTOP_EDGE_EASED,
    COUNTERTOP_EDGE_OGEE,
    COUNTERTOP_GRANITE_BUDGET,
    COUNTERTOP_GRANITE_MID,
    COUNTERTOP_GRANITE_PREMIUM,
    COUNTERTOP_MARBLE,
    COUNTERTOP_QUARTZ_MID,
    COUNTERTOP_QUARTZ_PREMIUM,
    DEMO_COUNTERTOP,
    DEMO_GENERAL,
    DEMO_TILE_FLOOR,
    DEMO_TILE_WALL,
    ELECTRICAL_LIGHTING,
    ELECTRICAL_OUTLET,
    GROUT_SEALING,
    HEATED_FLOOR_ELECTRIC,
    PLUMBING_FIXTURE_DISCONNECT,
    PLUMBING_ROUGH_IN,
    SCOPE_TO_ASSEMBLY,
    STONE_SEALING,
    SUBSTRATE_LEVELING,
    TILE_BACKSPLASH_STANDARD,
    TILE_FLOOR_NATURAL_STONE,
    TILE_FLOOR_PORCELAIN_12X24,
    TILE_WALL_SHOWER,
    TILE_WALL_SUBWAY,
    WATERPROOF_FLOOR,
    WATERPROOF_SHOWER,
)
from src.cost_engine.regional import (
    BEND_OR,
    PORTLAND_OR,
    REDMOND_OR,
    REGIONS,
    RegionalFactors,
    apply_regional_adjustment,
    get_regional_factors,
)

# ---------------------------------------------------------------------------
# Assembly Calculation Deep Tests
# ---------------------------------------------------------------------------

class TestTileAssemblyCalculations:
    """Verify precise calculations for tile assemblies."""

    def test_porcelain_12x24_exact_material(self) -> None:
        result = TILE_FLOOR_PORCELAIN_12X24.calculate(100.0)
        # Tile: 4.50 * 100 * (1 + 0.10) = 4.50 * 110 = 495.0
        tile_li = next(li for li in result["line_items"] if "porcelain tile 12x24" in li["description"].lower())
        assert tile_li["total"] == 495.0
        assert tile_li["quantity"] == 110.0

    def test_porcelain_12x24_exact_thinset(self) -> None:
        result = TILE_FLOOR_PORCELAIN_12X24.calculate(100.0)
        thinset_li = next(li for li in result["line_items"] if "thinset" in li["description"].lower())
        # 0.45 * 100 * (1 + 0.05) = 0.45 * 105 = 47.25
        assert thinset_li["total"] == 47.25

    def test_porcelain_12x24_exact_grout(self) -> None:
        result = TILE_FLOOR_PORCELAIN_12X24.calculate(100.0)
        grout_li = next(li for li in result["line_items"] if "grout" in li["description"].lower())
        # 0.25 * 100 * (1 + 0.05) = 0.25 * 105 = 26.25
        assert grout_li["total"] == 26.25

    def test_porcelain_12x24_exact_total(self) -> None:
        result = TILE_FLOOR_PORCELAIN_12X24.calculate(100.0)
        # material = 495 + 47.25 + 26.25 = 568.50, labor = 800.0
        assert result["material"] == 568.5
        assert result["labor"] == 800.0
        assert result["total"] == 1368.5

    def test_subway_wall_tile(self) -> None:
        result = TILE_WALL_SUBWAY.calculate(50.0)
        assert result["total"] > 0
        # Wall tile has higher labor rate than floor
        assert result["labor"] == 500.0  # 10.00 * 50

    def test_shower_wall_tile(self) -> None:
        result = TILE_WALL_SHOWER.calculate(80.0)
        assert result["labor"] == 960.0  # 12.00 * 80

    def test_backsplash_standard(self) -> None:
        result = TILE_BACKSPLASH_STANDARD.calculate(20.0)
        assert result["total"] > 0
        assert result["labor"] == 240.0  # 12.00 * 20

    def test_natural_stone_floor(self) -> None:
        result = TILE_FLOOR_NATURAL_STONE.calculate(50.0)
        # Should include stone sealer as material component
        assert result["material"] > 0
        sealer_li = next(
            (li for li in result["line_items"] if "sealer" in li["description"].lower()),
            None,
        )
        assert sealer_li is not None


class TestCountertopAssemblyCalculations:
    """Verify countertop assembly calculations."""

    def test_granite_budget_vs_mid_vs_premium(self) -> None:
        budget = COUNTERTOP_GRANITE_BUDGET.calculate(30.0)
        mid = COUNTERTOP_GRANITE_MID.calculate(30.0)
        premium = COUNTERTOP_GRANITE_PREMIUM.calculate(30.0)
        assert budget["total"] < mid["total"] < premium["total"]

    def test_quartz_mid_vs_premium(self) -> None:
        mid = COUNTERTOP_QUARTZ_MID.calculate(30.0)
        premium = COUNTERTOP_QUARTZ_PREMIUM.calculate(30.0)
        assert mid["total"] < premium["total"]

    def test_marble_includes_sealer(self) -> None:
        result = COUNTERTOP_MARBLE.calculate(30.0)
        sealer_li = next(
            (li for li in result["line_items"] if "sealer" in li["description"].lower()),
            None,
        )
        assert sealer_li is not None
        assert sealer_li["total"] == 45.0  # 1.50 * 30

    def test_cutout_per_each(self) -> None:
        result = COUNTERTOP_CUTOUT_STANDARD.calculate(2.0)
        assert result["labor"] == 500.0  # 250 * 2

    def test_edge_profiles_ordering(self) -> None:
        lf = 20.0  # 20 linear feet
        eased = COUNTERTOP_EDGE_EASED.calculate(lf)
        beveled = COUNTERTOP_EDGE_BEVELED.calculate(lf)
        ogee = COUNTERTOP_EDGE_OGEE.calculate(lf)
        dupont = COUNTERTOP_EDGE_DUPONT.calculate(lf)
        assert eased["total"] < beveled["total"] < ogee["total"] < dupont["total"]

    def test_backsplash_4in(self) -> None:
        result = COUNTERTOP_BACKSPLASH_4IN.calculate(15.0)
        assert result["material"] > 0
        assert result["labor"] > 0
        # Material: 12 * 15 * 1.1 = 198, Labor: 15 * 15 = 225
        assert result["material"] == 198.0
        assert result["labor"] == 225.0


class TestDemolitionAssemblies:
    """Test demolition assembly calculations."""

    def test_floor_demo(self) -> None:
        result = DEMO_TILE_FLOOR.calculate(100.0)
        assert result["labor"] == 350.0  # 3.50 * 100
        assert result["material"] == 50.0  # disposal 0.50 * 100

    def test_wall_demo(self) -> None:
        result = DEMO_TILE_WALL.calculate(60.0)
        assert result["labor"] == 240.0  # 4.00 * 60

    def test_countertop_demo(self) -> None:
        result = DEMO_COUNTERTOP.calculate(20.0)
        assert result["labor"] == 240.0  # 12.00 * 20

    def test_general_demo(self) -> None:
        result = DEMO_GENERAL.calculate(3.0)
        assert result["labor"] == 450.0  # 150 * 3
        assert result["material"] == 225.0  # 75 * 3


class TestPrepWorkAssemblies:
    """Test prep work assemblies."""

    def test_backer_board(self) -> None:
        result = BACKER_CEMENT_BOARD.calculate(80.0)
        assert result["total"] > 0
        assert result["material"] > 0
        assert result["labor"] == 240.0  # 3.00 * 80

    def test_waterproofing_shower(self) -> None:
        result = WATERPROOF_SHOWER.calculate(60.0)
        assert result["material"] > 0
        assert result["labor"] == 300.0  # 5.00 * 60

    def test_waterproofing_floor(self) -> None:
        result = WATERPROOF_FLOOR.calculate(100.0)
        assert result["labor"] == 150.0  # 1.50 * 100

    def test_leveling(self) -> None:
        result = SUBSTRATE_LEVELING.calculate(50.0)
        assert result["material"] > 0
        assert result["labor"] == 150.0  # 3.00 * 50


class TestMEPAssemblies:
    """Test mechanical/electrical/plumbing assemblies."""

    def test_plumbing_disconnect(self) -> None:
        result = PLUMBING_FIXTURE_DISCONNECT.calculate(1.0)
        assert result["subcontractor"] == 250.0

    def test_plumbing_rough_in(self) -> None:
        result = PLUMBING_ROUGH_IN.calculate(1.0)
        assert result["subcontractor"] == 850.0

    def test_electrical_outlet(self) -> None:
        result = ELECTRICAL_OUTLET.calculate(3.0)
        assert result["subcontractor"] == 825.0  # 275 * 3

    def test_electrical_lighting(self) -> None:
        result = ELECTRICAL_LIGHTING.calculate(4.0)
        assert result["subcontractor"] == 900.0  # 225 * 4


class TestFinishAssemblies:
    """Test finish/sealing assemblies."""

    def test_grout_sealing(self) -> None:
        result = GROUT_SEALING.calculate(100.0)
        assert result["material"] == 15.0  # 0.15 * 100
        assert result["labor"] == 50.0  # 0.50 * 100

    def test_stone_sealing(self) -> None:
        result = STONE_SEALING.calculate(50.0)
        assert result["material"] == 25.0  # 0.50 * 50
        assert result["labor"] == 50.0  # 1.00 * 50

    def test_caulking(self) -> None:
        result = CAULKING.calculate(40.0)
        assert result["material"] == 20.0  # 0.50 * 40
        assert result["labor"] == 80.0  # 2.00 * 40


class TestHeatedFloor:
    """Test heated floor assembly."""

    def test_heated_floor_components(self) -> None:
        result = HEATED_FLOOR_ELECTRIC.calculate(50.0)
        assert result["material"] > 0
        assert result["labor"] > 0
        assert result["subcontractor"] > 0
        assert result["total"] == result["material"] + result["labor"] + result["subcontractor"]


class TestAssemblyEdgeCases:
    """Test edge cases in assembly calculations."""

    def test_fractional_quantity(self) -> None:
        result = TILE_FLOOR_PORCELAIN_12X24.calculate(33.7)
        assert result["total"] > 0
        assert result["quantity"] == 33.7

    def test_very_large_quantity(self) -> None:
        result = TILE_FLOOR_PORCELAIN_12X24.calculate(10000.0)
        assert result["total"] > 100000.0

    def test_very_small_quantity(self) -> None:
        result = TILE_FLOOR_PORCELAIN_12X24.calculate(0.5)
        assert result["total"] > 0

    def test_negative_quantity_not_prevented(self) -> None:
        """Assembly doesn't validate negative — caller responsibility."""
        result = TILE_FLOOR_PORCELAIN_12X24.calculate(-10.0)
        assert result["total"] < 0


# ---------------------------------------------------------------------------
# Regional Adjustments Extended
# ---------------------------------------------------------------------------

class TestRegionalFactorsModel:
    """Test RegionalFactors pydantic model."""

    def test_bend_or_notes(self) -> None:
        assert len(BEND_OR.notes) >= 3
        assert any("sales tax" in n.lower() for n in BEND_OR.notes)

    def test_portland_baseline(self) -> None:
        assert PORTLAND_OR.labor_factor == 1.0
        assert PORTLAND_OR.transport_surcharge_pct == 0.0

    def test_redmond_between_bend_portland(self) -> None:
        assert PORTLAND_OR.labor_factor <= REDMOND_OR.labor_factor <= BEND_OR.labor_factor

    def test_custom_region(self) -> None:
        custom = RegionalFactors(
            region_code="seattle_wa",
            region_name="Seattle, WA",
            labor_factor=1.15,
            sales_tax_rate=0.10,
            transport_surcharge_pct=0.01,
        )
        assert custom.sales_tax_rate == 0.10


class TestRegionalAdjustmentPrecision:
    """Test precise regional adjustment calculations."""

    def test_bend_labor_precise(self) -> None:
        adjusted = apply_regional_adjustment(1000.0, "labor", BEND_OR)
        assert adjusted == 1100.0  # 1000 * 1.10

    def test_bend_material_with_transport(self) -> None:
        adjusted = apply_regional_adjustment(1000.0, "material", BEND_OR)
        # 1000 * 1.0 = 1000, + 3% transport = 1030, + 0% tax = 1030
        assert adjusted == 1030.0

    def test_redmond_labor(self) -> None:
        adjusted = apply_regional_adjustment(1000.0, "labor", REDMOND_OR)
        assert adjusted == 1080.0  # 1000 * 1.08

    def test_zero_base_cost(self) -> None:
        adjusted = apply_regional_adjustment(0.0, "labor", BEND_OR)
        assert adjusted == 0.0

    def test_subcontractor_no_adjustment(self) -> None:
        adjusted = apply_regional_adjustment(500.0, "subcontractor", BEND_OR)
        assert adjusted == 500.0


class TestScopeToAssemblyMapping:
    """Test SCOPE_TO_ASSEMBLY mapping completeness."""

    def test_all_codes_in_registry(self) -> None:
        for key, code in SCOPE_TO_ASSEMBLY.items():
            assert code in ASSEMBLY_REGISTRY, f"Code {code} for scope key '{key}' not in registry"

    def test_key_categories_mapped(self) -> None:
        required = [
            "tile_floor", "tile_wall", "backsplash", "countertop",
            "demolition", "waterproofing", "plumbing", "electrical",
        ]
        for cat in required:
            assert cat in SCOPE_TO_ASSEMBLY, f"Category '{cat}' missing from SCOPE_TO_ASSEMBLY"

    def test_unique_assembly_codes(self) -> None:
        codes = list(ASSEMBLY_REGISTRY.keys())
        assert len(codes) == len(set(codes))


class TestRegionsDict:
    """Test REGIONS dictionary."""

    def test_all_regions_present(self) -> None:
        assert "bend_or" in REGIONS
        assert "portland_or" in REGIONS
        assert "redmond_or" in REGIONS

    def test_get_regional_factors_all(self) -> None:
        for code in REGIONS:
            factors = get_regional_factors(code)
            assert factors.region_code == code
