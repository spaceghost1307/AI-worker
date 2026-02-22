"""Estimation Agent — generates assembly-based cost estimates with ML refinement.

The estimation process:
1. Receives structured scope items and image analysis results
2. Retrieves relevant cost data via RAG (regional pricing, historical projects)
3. Calculates costs using the assembly-based engine
4. Applies regional adjustments for Bend, OR
5. Refines with ML model trained on historical project data
6. Returns detailed line-item breakdown with confidence scores
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from src.cost_engine.assemblies import (
    SCOPE_TO_ASSEMBLY,
    Assembly,
    get_assembly,
)
from src.cost_engine.ml_refiner import EstimateRefiner
from src.cost_engine.regional import (
    BEND_OR,
    apply_regional_adjustment,
    get_regional_factors,
)

logger = logging.getLogger(__name__)


class LineItem(BaseModel):
    """A single line item in the estimate."""

    description: str
    category: str  # material, labor, equipment, subcontractor
    quantity: float
    unit: str  # sq_ft, linear_ft, each, hour, etc.
    unit_cost: float
    waste_factor: float = 0.0
    total: float = 0.0
    source: str = ""  # where the cost data came from


class EstimateBreakdown(BaseModel):
    """Full estimate with line items grouped by category."""

    project_type: str
    line_items: list[LineItem]
    subtotal_materials: float = 0.0
    subtotal_labor: float = 0.0
    subtotal_equipment: float = 0.0
    overhead_pct: float = 0.10
    profit_pct: float = 0.10
    contingency_pct: float = 0.10
    total: float = 0.0
    confidence: float = 0.0
    notes: list[str] = []
    ml_adjustment: float = 0.0
    ml_explanation: str = ""


# Mapping from scope item categories to assembly lookup keys
_CATEGORY_MAP: dict[str, str] = {
    "tile_floor": "tile_floor",
    "tile": "tile_floor",
    "tile_wall": "tile_wall",
    "tile_wall_shower": "tile_wall_shower",
    "shower_tile": "tile_wall_shower",
    "backsplash": "backsplash",
    "countertop": "countertop",
    "countertop_quartz": "countertop_quartz",
    "countertop_marble": "countertop_marble",
    "demolition": "demolition",
    "demo": "demolition",
    "demolition_floor": "demolition_floor",
    "demolition_wall": "demolition_wall",
    "demolition_countertop": "demolition_countertop",
    "backer_board": "backer_board",
    "waterproofing": "waterproofing",
    "waterproofing_floor": "waterproofing_floor",
    "plumbing": "plumbing",
    "electrical": "electrical",
    "heated_floor": "heated_floor",
    "grout_sealing": "grout_sealing",
    "stone_sealing": "stone_sealing",
    "caulking": "caulking",
    "leveling": "leveling",
    "prep_work": "leveling",
}


def _match_assembly(scope_category: str, material_hint: str | None = None) -> Assembly | None:
    """Match a scope item category to the best assembly.

    Args:
        scope_category: Category from scope extraction.
        material_hint: Optional material selection hint for better matching.

    Returns:
        Matching assembly or None.
    """
    # Normalize category
    cat = scope_category.lower().replace(" ", "_").replace("-", "_")
    lookup_key = _CATEGORY_MAP.get(cat, cat)

    # Check for material-specific overrides
    if material_hint:
        hint = material_hint.lower()
        if "quartz" in hint and "countertop" in cat:
            lookup_key = "countertop_quartz"
        elif "marble" in hint and "countertop" in cat:
            lookup_key = "countertop_marble"
        elif "mosaic" in hint:
            return get_assembly("TILE-FLR-MOSAIC")
        elif "large format" in hint or "24x48" in hint:
            return get_assembly("TILE-FLR-LF2448")
        elif "natural stone" in hint or "travertine" in hint or "slate" in hint:
            return get_assembly("TILE-FLR-STONE")
        elif "shower" in hint and "tile" in cat:
            lookup_key = "tile_wall_shower"

    assembly_code = SCOPE_TO_ASSEMBLY.get(lookup_key)
    if assembly_code:
        return get_assembly(assembly_code)

    return None


class EstimationAgent:
    """CrewAI-compatible agent for cost estimation."""

    def __init__(self, settings: Any = None) -> None:
        self.settings = settings
        region_code = "bend_or"
        if settings:
            region_code = getattr(settings, "default_region", "bend_or")
        try:
            self.region = get_regional_factors(region_code)
        except KeyError:
            self.region = BEND_OR
        self.ml_refiner = EstimateRefiner()

    def estimate_from_scope(
        self,
        scope_items: list[dict[str, Any]],
        image_analysis: list[dict[str, Any]] | None = None,
    ) -> EstimateBreakdown:
        """Generate a cost estimate from structured scope items.

        Args:
            scope_items: Structured scope data from the Scope Agent.
            image_analysis: Optional image analysis data to supplement scope.

        Returns:
            Detailed estimate breakdown with line items and totals.
        """
        line_items: list[LineItem] = []
        notes: list[str] = []
        unmatched: list[str] = []

        # Supplement scope with image analysis dimensions if available
        dimension_map: dict[str, dict[str, float]] = {}
        if image_analysis:
            for assessment in image_analysis:
                room = assessment.get("room_type", "unknown")
                dims = assessment.get("dimensions_estimate", {})
                if dims.get("floor_area_sq_ft", 0) > 0:
                    dimension_map[room] = dims

        for item in scope_items:
            category = item.get("category", "other")
            material = item.get("material_selection")
            assembly = _match_assembly(category, material)

            if assembly is None:
                unmatched.append(f"{category}: {item.get('description', 'unknown')}")
                continue

            # Determine quantity
            quantity = item.get("quantity_estimate", 0.0) or 0.0

            # If no quantity, try to get from image analysis dimensions
            if quantity <= 0:
                room = item.get("room", "")
                if room in dimension_map and assembly.unit == "sq_ft":
                    quantity = dimension_map[room].get("floor_area_sq_ft", 0.0)
                    if quantity > 0:
                        notes.append(
                            f"Estimated {assembly.unit} for {room} from photo analysis"
                        )

            if quantity <= 0:
                notes.append(
                    f"Quantity missing for {item.get('description', category)} — "
                    f"using placeholder 1.0 {assembly.unit}"
                )
                quantity = 1.0

            # Calculate assembly cost
            calc = assembly.calculate(quantity)

            # Apply regional adjustments and build line items
            for li in calc["line_items"]:
                adjusted_total = apply_regional_adjustment(
                    li["total"], li["category"], self.region
                )
                line_items.append(LineItem(
                    description=li["description"],
                    category=li["category"],
                    quantity=li["quantity"],
                    unit=li["unit"],
                    unit_cost=li["unit_cost"],
                    waste_factor=li["waste_factor"],
                    total=adjusted_total,
                    source=assembly.code,
                ))

        if unmatched:
            notes.append(f"Unmatched scope items (no assembly found): {', '.join(unmatched)}")

        # Calculate subtotals
        subtotal_materials = sum(li.total for li in line_items if li.category == "material")
        subtotal_labor = sum(li.total for li in line_items if li.category == "labor")
        subtotal_equipment = sum(
            li.total for li in line_items
            if li.category in ("equipment", "subcontractor")
        )

        subtotal = subtotal_materials + subtotal_labor + subtotal_equipment

        # Determine project type from scope items
        categories = {item.get("category", "") for item in scope_items}
        if "countertop" in categories:
            project_type = "countertop"
        elif categories & {"tile_floor", "tile_wall", "tile", "backsplash"}:
            project_type = "tile"
        else:
            project_type = "remodel"

        # Apply overhead, profit, and contingency
        overhead_pct = 0.10
        profit_pct = 0.10
        contingency_pct = 0.10

        markups = subtotal * (overhead_pct + profit_pct + contingency_pct)
        total = subtotal + markups

        # Apply ML refinement
        estimate_data = {
            "total": total,
            "project_type": project_type,
            "region": self.region.region_code,
            "subtotal_materials": subtotal_materials,
            "subtotal_labor": subtotal_labor,
        }
        ml_result = self.ml_refiner.refine(estimate_data)

        # Confidence: higher if we matched more items and have quantities
        matched_pct = 1.0 - (len(unmatched) / max(len(scope_items), 1))
        has_quantities = sum(
            1 for item in scope_items if (item.get("quantity_estimate") or 0) > 0
        ) / max(len(scope_items), 1)
        confidence = round(0.5 * matched_pct + 0.5 * has_quantities, 2)

        return EstimateBreakdown(
            project_type=project_type,
            line_items=line_items,
            subtotal_materials=round(subtotal_materials, 2),
            subtotal_labor=round(subtotal_labor, 2),
            subtotal_equipment=round(subtotal_equipment, 2),
            overhead_pct=overhead_pct,
            profit_pct=profit_pct,
            contingency_pct=contingency_pct,
            total=round(ml_result.adjusted_total, 2),
            confidence=confidence,
            notes=notes,
            ml_adjustment=ml_result.adjustment_pct,
            ml_explanation=ml_result.explanation,
        )

    def estimate_countertop(
        self,
        material: str,
        square_feet: float,
        edge_profile: str = "eased",
        cutouts: int = 1,
        backsplash: bool = False,
    ) -> EstimateBreakdown:
        """Specialized estimator for countertop fabrication projects.

        Args:
            material: Stone type (e.g., "granite_mid", "quartz_mid", "marble").
            square_feet: Total countertop area.
            edge_profile: Edge detail (eased, beveled, ogee, dupont).
            cutouts: Number of sink/cooktop cutouts.
            backsplash: Whether 4\" stone backsplash is included.

        Returns:
            Countertop-specific estimate breakdown.
        """
        line_items: list[LineItem] = []
        notes: list[str] = []

        # Match countertop assembly based on material
        material_lower = material.lower()
        if "quartz" in material_lower:
            if "premium" in material_lower:
                assembly_code = "CNTR-QUARTZ-PREM"
            else:
                assembly_code = "CNTR-QUARTZ-MID"
        elif "marble" in material_lower:
            assembly_code = "CNTR-MARBLE-MID"
        elif "premium" in material_lower or "exotic" in material_lower:
            assembly_code = "CNTR-GRAN-PREM"
        elif "budget" in material_lower:
            assembly_code = "CNTR-GRAN-BUD"
        else:
            assembly_code = "CNTR-GRAN-MID"

        assembly = get_assembly(assembly_code)
        if assembly is None:
            return EstimateBreakdown(
                project_type="countertop_fabrication",
                line_items=[],
                notes=["Assembly not found for material: " + material],
            )

        # Main countertop calculation
        calc = assembly.calculate(square_feet)
        for li in calc["line_items"]:
            adjusted = apply_regional_adjustment(li["total"], li["category"], self.region)
            line_items.append(LineItem(
                description=li["description"],
                category=li["category"],
                quantity=li["quantity"],
                unit=li["unit"],
                unit_cost=li["unit_cost"],
                waste_factor=li["waste_factor"],
                total=adjusted,
                source=assembly_code,
            ))

        # Edge profile
        edge_codes = {
            "eased": "CNTR-EDGE-EASE",
            "beveled": "CNTR-EDGE-BEV",
            "ogee": "CNTR-EDGE-OGEE",
            "dupont": "CNTR-EDGE-DUP",
        }
        edge_code = edge_codes.get(edge_profile.lower(), "CNTR-EDGE-EASE")
        edge_assembly = get_assembly(edge_code)
        if edge_assembly:
            # Estimate perimeter from square footage (rough: perimeter ≈ 4 * sqrt(area))
            import math
            perimeter_lf = round(4 * math.sqrt(square_feet), 1)
            edge_calc = edge_assembly.calculate(perimeter_lf)
            for li in edge_calc["line_items"]:
                adjusted = apply_regional_adjustment(li["total"], li["category"], self.region)
                line_items.append(LineItem(
                    description=li["description"],
                    category=li["category"],
                    quantity=li["quantity"],
                    unit=li["unit"],
                    unit_cost=li["unit_cost"],
                    waste_factor=li["waste_factor"],
                    total=adjusted,
                    source=edge_code,
                ))
            notes.append(f"Edge profile: {edge_profile} ({perimeter_lf} linear ft estimated)")

        # Cutouts
        if cutouts > 0:
            cutout_assembly = get_assembly("CNTR-CUT-STD")
            if cutout_assembly:
                cutout_calc = cutout_assembly.calculate(float(cutouts))
                for li in cutout_calc["line_items"]:
                    adjusted = apply_regional_adjustment(
                        li["total"], li["category"], self.region
                    )
                    line_items.append(LineItem(
                        description=li["description"],
                        category=li["category"],
                        quantity=li["quantity"],
                        unit=li["unit"],
                        unit_cost=li["unit_cost"],
                        waste_factor=li["waste_factor"],
                        total=adjusted,
                        source="CNTR-CUT-STD",
                    ))

        # Backsplash
        if backsplash:
            back_assembly = get_assembly("CNTR-BACK-4")
            if back_assembly:
                import math
                back_lf = round(4 * math.sqrt(square_feet) * 0.75, 1)
                back_calc = back_assembly.calculate(back_lf)
                for li in back_calc["line_items"]:
                    adjusted = apply_regional_adjustment(
                        li["total"], li["category"], self.region
                    )
                    line_items.append(LineItem(
                        description=li["description"],
                        category=li["category"],
                        quantity=li["quantity"],
                        unit=li["unit"],
                        unit_cost=li["unit_cost"],
                        waste_factor=li["waste_factor"],
                        total=adjusted,
                        source="CNTR-BACK-4",
                    ))
                notes.append(f"4\" stone backsplash: {back_lf} linear ft estimated")

        # Slab utilization note
        slab_area = 9 * 5  # typical slab size 9'x5'
        slabs_needed = max(1, -(-int(square_feet) // slab_area))  # ceiling division
        notes.append(f"Slab requirement: ~{slabs_needed} slab(s) based on {square_feet} sq ft")

        # Calculate totals
        subtotal_materials = sum(li.total for li in line_items if li.category == "material")
        subtotal_labor = sum(li.total for li in line_items if li.category == "labor")
        subtotal_equipment = sum(
            li.total for li in line_items
            if li.category in ("equipment", "subcontractor")
        )
        subtotal = subtotal_materials + subtotal_labor + subtotal_equipment

        overhead_pct = 0.10
        profit_pct = 0.12  # slightly higher margin for countertops
        contingency_pct = 0.08
        markups = subtotal * (overhead_pct + profit_pct + contingency_pct)
        total = subtotal + markups

        return EstimateBreakdown(
            project_type="countertop_fabrication",
            line_items=line_items,
            subtotal_materials=round(subtotal_materials, 2),
            subtotal_labor=round(subtotal_labor, 2),
            subtotal_equipment=round(subtotal_equipment, 2),
            overhead_pct=overhead_pct,
            profit_pct=profit_pct,
            contingency_pct=contingency_pct,
            total=round(total, 2),
            confidence=0.85,
            notes=notes,
        )
