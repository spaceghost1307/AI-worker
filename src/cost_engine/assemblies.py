"""Assembly-based cost calculation engine.

Assemblies are the foundation of the estimation system. Each assembly
represents a complete unit of work (e.g., "Tile floor installation — porcelain
12x24") with component materials, labor units, waste factors, and markups.

Every cost in the system traces back to: material rate + labor rate + waste factor.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class CostCategory(str, Enum):
    MATERIAL = "material"
    LABOR = "labor"
    EQUIPMENT = "equipment"
    SUBCONTRACTOR = "subcontractor"


class AssemblyComponent(BaseModel):
    """A single component within an assembly."""

    description: str
    category: CostCategory
    unit_cost: float
    unit: str  # sq_ft, linear_ft, each, hour
    quantity_per_assembly_unit: float = 1.0
    waste_factor: float = 0.0  # 0.05 = 5% waste
    source: str = ""
    effective_date: str = ""


class Assembly(BaseModel):
    """A complete work assembly with all cost components."""

    name: str
    code: str  # internal assembly code
    category: str  # tile_floor, tile_wall, countertop, demolition, plumbing, etc.
    unit: str  # the unit this assembly is measured in (sq_ft, linear_ft, each)
    components: list[AssemblyComponent]
    notes: str = ""

    def calculate(self, quantity: float) -> dict[str, Any]:
        """Calculate total cost for a given quantity of this assembly.

        Args:
            quantity: Amount in assembly units (e.g., 150 sq_ft).

        Returns:
            Breakdown with material, labor, equipment totals and grand total.
        """
        totals: dict[str, float] = {
            "material": 0.0,
            "labor": 0.0,
            "equipment": 0.0,
            "subcontractor": 0.0,
        }
        line_items = []

        for component in self.components:
            effective_qty = quantity * component.quantity_per_assembly_unit
            waste_qty = effective_qty * component.waste_factor
            total_qty = effective_qty + waste_qty
            cost = total_qty * component.unit_cost

            totals[component.category.value] += cost
            line_items.append({
                "description": component.description,
                "category": component.category.value,
                "quantity": total_qty,
                "unit": component.unit,
                "unit_cost": component.unit_cost,
                "waste_factor": component.waste_factor,
                "total": cost,
            })

        grand_total = sum(totals.values())
        return {
            "assembly": self.name,
            "quantity": quantity,
            "unit": self.unit,
            "line_items": line_items,
            **totals,
            "total": grand_total,
        }


# ---------------------------------------------------------------------------
# Standard assembly library — starting templates for Nelson Tile & Stone
# ---------------------------------------------------------------------------

TILE_FLOOR_PORCELAIN_12X24 = Assembly(
    name="Tile Floor Installation — Porcelain 12x24",
    code="TILE-FLR-P1224",
    category="tile_floor",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Porcelain tile 12x24",
            category=CostCategory.MATERIAL,
            unit_cost=4.50,
            unit="sq_ft",
            waste_factor=0.10,
            source="supplier_catalog",
        ),
        AssemblyComponent(
            description="Thinset morite",
            category=CostCategory.MATERIAL,
            unit_cost=0.45,
            unit="sq_ft",
            waste_factor=0.05,
        ),
        AssemblyComponent(
            description="Grout",
            category=CostCategory.MATERIAL,
            unit_cost=0.25,
            unit="sq_ft",
            waste_factor=0.05,
        ),
        AssemblyComponent(
            description="Tile installation labor",
            category=CostCategory.LABOR,
            unit_cost=8.00,
            unit="sq_ft",
        ),
    ],
)

COUNTERTOP_GRANITE_MID = Assembly(
    name="Granite Countertop — Mid Grade",
    code="CNTR-GRAN-MID",
    category="countertop",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Granite slab — mid grade (Santa Cecilia, Giallo Ornamental)",
            category=CostCategory.MATERIAL,
            unit_cost=45.00,
            unit="sq_ft",
            waste_factor=0.15,
            source="supplier_catalog",
        ),
        AssemblyComponent(
            description="Fabrication labor",
            category=CostCategory.LABOR,
            unit_cost=35.00,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Installation labor",
            category=CostCategory.LABOR,
            unit_cost=15.00,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Template/measure",
            category=CostCategory.LABOR,
            unit_cost=2.50,
            unit="sq_ft",
        ),
    ],
    notes="Does not include cutouts, edge profiles, backsplash, or demolition — add separately.",
)

# TODO: Add more assemblies:
# - TILE-WALL-* (wall tile variants)
# - TILE-FLR-MOSAIC (mosaic floor)
# - TILE-FLR-LF (large format 24x48+)
# - CNTR-GRAN-BUDGET, CNTR-GRAN-PREMIUM, CNTR-GRAN-EXOTIC
# - CNTR-QUARTZ-*
# - CNTR-MARBLE-*
# - DEMO-* (demolition assemblies)
# - PLUMB-* (plumbing rough-in, finish)
# - ELEC-* (electrical)
# - WATERPROOF-* (shower waterproofing)
# - BACKER-* (cement board, Kerdi)
