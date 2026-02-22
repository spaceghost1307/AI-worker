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
# Standard assembly library — Nelson Tile & Stone, Bend, Oregon
# ---------------------------------------------------------------------------

# --- Tile Floor Assemblies ---

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
            description="Thinset mortar",
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

TILE_FLOOR_PORCELAIN_LARGE_FORMAT = Assembly(
    name="Tile Floor Installation — Large Format Porcelain 24x48",
    code="TILE-FLR-LF2448",
    category="tile_floor",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Large format porcelain tile 24x48",
            category=CostCategory.MATERIAL,
            unit_cost=7.50,
            unit="sq_ft",
            waste_factor=0.12,
            source="supplier_catalog",
        ),
        AssemblyComponent(
            description="Large format thinset (LFT)",
            category=CostCategory.MATERIAL,
            unit_cost=0.65,
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
            description="Tile leveling system clips/wedges",
            category=CostCategory.MATERIAL,
            unit_cost=0.35,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Large format tile installation labor (premium)",
            category=CostCategory.LABOR,
            unit_cost=11.00,
            unit="sq_ft",
        ),
    ],
    notes="Large format requires substrate flatness within 1/8\" per 10ft. "
    "Leveling system required. Higher waste due to cuts.",
)

TILE_FLOOR_MOSAIC = Assembly(
    name="Tile Floor Installation — Mosaic (sheet mount)",
    code="TILE-FLR-MOSAIC",
    category="tile_floor",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Mosaic tile sheets (glass/porcelain)",
            category=CostCategory.MATERIAL,
            unit_cost=12.00,
            unit="sq_ft",
            waste_factor=0.08,
            source="supplier_catalog",
        ),
        AssemblyComponent(
            description="White thinset for mosaic",
            category=CostCategory.MATERIAL,
            unit_cost=0.55,
            unit="sq_ft",
            waste_factor=0.05,
        ),
        AssemblyComponent(
            description="Non-sanded grout",
            category=CostCategory.MATERIAL,
            unit_cost=0.40,
            unit="sq_ft",
            waste_factor=0.05,
        ),
        AssemblyComponent(
            description="Mosaic tile installation labor",
            category=CostCategory.LABOR,
            unit_cost=14.00,
            unit="sq_ft",
        ),
    ],
)

TILE_FLOOR_NATURAL_STONE = Assembly(
    name="Tile Floor Installation — Natural Stone (travertine/slate)",
    code="TILE-FLR-STONE",
    category="tile_floor",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Natural stone tile (travertine/slate)",
            category=CostCategory.MATERIAL,
            unit_cost=8.00,
            unit="sq_ft",
            waste_factor=0.12,
            source="supplier_catalog",
        ),
        AssemblyComponent(
            description="White thinset mortar",
            category=CostCategory.MATERIAL,
            unit_cost=0.55,
            unit="sq_ft",
            waste_factor=0.05,
        ),
        AssemblyComponent(
            description="Sanded grout",
            category=CostCategory.MATERIAL,
            unit_cost=0.30,
            unit="sq_ft",
            waste_factor=0.05,
        ),
        AssemblyComponent(
            description="Stone sealer",
            category=CostCategory.MATERIAL,
            unit_cost=0.35,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Natural stone installation labor",
            category=CostCategory.LABOR,
            unit_cost=10.00,
            unit="sq_ft",
        ),
    ],
)

# --- Tile Wall Assemblies ---

TILE_WALL_SUBWAY = Assembly(
    name="Tile Wall Installation — Subway 3x6/4x12",
    code="TILE-WALL-SUB",
    category="tile_wall",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Ceramic subway tile",
            category=CostCategory.MATERIAL,
            unit_cost=3.50,
            unit="sq_ft",
            waste_factor=0.10,
            source="supplier_catalog",
        ),
        AssemblyComponent(
            description="Thinset mortar",
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
            description="Wall tile installation labor",
            category=CostCategory.LABOR,
            unit_cost=10.00,
            unit="sq_ft",
        ),
    ],
)

TILE_WALL_SHOWER = Assembly(
    name="Tile Wall Installation — Shower Walls (porcelain)",
    code="TILE-WALL-SHOWER",
    category="tile_wall",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Porcelain wall tile",
            category=CostCategory.MATERIAL,
            unit_cost=5.50,
            unit="sq_ft",
            waste_factor=0.10,
            source="supplier_catalog",
        ),
        AssemblyComponent(
            description="Modified thinset (shower-rated)",
            category=CostCategory.MATERIAL,
            unit_cost=0.55,
            unit="sq_ft",
            waste_factor=0.05,
        ),
        AssemblyComponent(
            description="Epoxy grout (shower-rated)",
            category=CostCategory.MATERIAL,
            unit_cost=0.65,
            unit="sq_ft",
            waste_factor=0.05,
        ),
        AssemblyComponent(
            description="Shower tile installation labor",
            category=CostCategory.LABOR,
            unit_cost=12.00,
            unit="sq_ft",
        ),
    ],
    notes="Does not include waterproofing — add WATERPROOF-SHOWER separately.",
)

# --- Backsplash ---

TILE_BACKSPLASH_STANDARD = Assembly(
    name="Tile Backsplash — Standard",
    code="TILE-BACK-STD",
    category="backsplash",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Backsplash tile (ceramic/porcelain)",
            category=CostCategory.MATERIAL,
            unit_cost=5.00,
            unit="sq_ft",
            waste_factor=0.10,
            source="supplier_catalog",
        ),
        AssemblyComponent(
            description="Thinset mortar",
            category=CostCategory.MATERIAL,
            unit_cost=0.45,
            unit="sq_ft",
            waste_factor=0.05,
        ),
        AssemblyComponent(
            description="Grout",
            category=CostCategory.MATERIAL,
            unit_cost=0.30,
            unit="sq_ft",
            waste_factor=0.05,
        ),
        AssemblyComponent(
            description="Backsplash installation labor",
            category=CostCategory.LABOR,
            unit_cost=12.00,
            unit="sq_ft",
        ),
    ],
)

# --- Countertop Assemblies ---

COUNTERTOP_GRANITE_BUDGET = Assembly(
    name="Granite Countertop — Budget Grade",
    code="CNTR-GRAN-BUD",
    category="countertop",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Granite slab — budget grade (Ubatuba, Tan Brown)",
            category=CostCategory.MATERIAL,
            unit_cost=32.00,
            unit="sq_ft",
            waste_factor=0.15,
            source="supplier_catalog",
        ),
        AssemblyComponent(
            description="Fabrication labor",
            category=CostCategory.LABOR,
            unit_cost=30.00,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Installation labor",
            category=CostCategory.LABOR,
            unit_cost=12.00,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Template/measure",
            category=CostCategory.LABOR,
            unit_cost=2.50,
            unit="sq_ft",
        ),
    ],
    notes="Does not include cutouts, edge profiles, backsplash, or demolition.",
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

COUNTERTOP_GRANITE_PREMIUM = Assembly(
    name="Granite Countertop — Premium/Exotic Grade",
    code="CNTR-GRAN-PREM",
    category="countertop",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Granite slab — premium/exotic (Blue Bahia, Patagonia)",
            category=CostCategory.MATERIAL,
            unit_cost=75.00,
            unit="sq_ft",
            waste_factor=0.18,
            source="supplier_catalog",
        ),
        AssemblyComponent(
            description="Fabrication labor (premium)",
            category=CostCategory.LABOR,
            unit_cost=40.00,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Installation labor",
            category=CostCategory.LABOR,
            unit_cost=18.00,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Template/measure",
            category=CostCategory.LABOR,
            unit_cost=3.00,
            unit="sq_ft",
        ),
    ],
)

COUNTERTOP_QUARTZ_MID = Assembly(
    name="Quartz Countertop — Mid Grade",
    code="CNTR-QUARTZ-MID",
    category="countertop",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Quartz slab — mid grade (Cambria, Caesarstone standard)",
            category=CostCategory.MATERIAL,
            unit_cost=55.00,
            unit="sq_ft",
            waste_factor=0.12,
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
)

COUNTERTOP_QUARTZ_PREMIUM = Assembly(
    name="Quartz Countertop — Premium Grade",
    code="CNTR-QUARTZ-PREM",
    category="countertop",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Quartz slab — premium (Cambria premium, Dekton, Neolith)",
            category=CostCategory.MATERIAL,
            unit_cost=80.00,
            unit="sq_ft",
            waste_factor=0.12,
            source="supplier_catalog",
        ),
        AssemblyComponent(
            description="Fabrication labor (premium)",
            category=CostCategory.LABOR,
            unit_cost=40.00,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Installation labor",
            category=CostCategory.LABOR,
            unit_cost=18.00,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Template/measure",
            category=CostCategory.LABOR,
            unit_cost=3.00,
            unit="sq_ft",
        ),
    ],
)

COUNTERTOP_MARBLE = Assembly(
    name="Marble Countertop — Mid Grade",
    code="CNTR-MARBLE-MID",
    category="countertop",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Marble slab — mid grade (Carrara, Calacatta Gold)",
            category=CostCategory.MATERIAL,
            unit_cost=60.00,
            unit="sq_ft",
            waste_factor=0.15,
            source="supplier_catalog",
        ),
        AssemblyComponent(
            description="Fabrication labor",
            category=CostCategory.LABOR,
            unit_cost=38.00,
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
        AssemblyComponent(
            description="Stone sealer (marble requires sealing)",
            category=CostCategory.MATERIAL,
            unit_cost=1.50,
            unit="sq_ft",
        ),
    ],
)

# --- Countertop Add-ons ---

COUNTERTOP_CUTOUT_STANDARD = Assembly(
    name="Countertop Cutout — Standard (sink/cooktop)",
    code="CNTR-CUT-STD",
    category="countertop_addon",
    unit="each",
    components=[
        AssemblyComponent(
            description="Sink/cooktop cutout fabrication",
            category=CostCategory.LABOR,
            unit_cost=250.00,
            unit="each",
        ),
    ],
)

COUNTERTOP_EDGE_EASED = Assembly(
    name="Edge Profile — Eased/Straight",
    code="CNTR-EDGE-EASE",
    category="countertop_addon",
    unit="linear_ft",
    components=[
        AssemblyComponent(
            description="Eased edge profile fabrication",
            category=CostCategory.LABOR,
            unit_cost=8.00,
            unit="linear_ft",
        ),
    ],
)

COUNTERTOP_EDGE_BEVELED = Assembly(
    name="Edge Profile — Beveled",
    code="CNTR-EDGE-BEV",
    category="countertop_addon",
    unit="linear_ft",
    components=[
        AssemblyComponent(
            description="Beveled edge profile fabrication",
            category=CostCategory.LABOR,
            unit_cost=15.00,
            unit="linear_ft",
        ),
    ],
)

COUNTERTOP_EDGE_OGEE = Assembly(
    name="Edge Profile — Ogee",
    code="CNTR-EDGE-OGEE",
    category="countertop_addon",
    unit="linear_ft",
    components=[
        AssemblyComponent(
            description="Ogee edge profile fabrication",
            category=CostCategory.LABOR,
            unit_cost=25.00,
            unit="linear_ft",
        ),
    ],
)

COUNTERTOP_EDGE_DUPONT = Assembly(
    name="Edge Profile — Dupont",
    code="CNTR-EDGE-DUP",
    category="countertop_addon",
    unit="linear_ft",
    components=[
        AssemblyComponent(
            description="Dupont edge profile fabrication",
            category=CostCategory.LABOR,
            unit_cost=30.00,
            unit="linear_ft",
        ),
    ],
)

COUNTERTOP_BACKSPLASH_4IN = Assembly(
    name="Countertop Backsplash — 4\" Stone",
    code="CNTR-BACK-4",
    category="countertop_addon",
    unit="linear_ft",
    components=[
        AssemblyComponent(
            description="4\" stone backsplash material",
            category=CostCategory.MATERIAL,
            unit_cost=12.00,
            unit="linear_ft",
            waste_factor=0.10,
        ),
        AssemblyComponent(
            description="Backsplash fabrication and install",
            category=CostCategory.LABOR,
            unit_cost=15.00,
            unit="linear_ft",
        ),
    ],
)

# --- Demolition ---

DEMO_TILE_FLOOR = Assembly(
    name="Demolition — Tile Floor Removal",
    code="DEMO-TILE-FLR",
    category="demolition",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Tile floor removal labor",
            category=CostCategory.LABOR,
            unit_cost=3.50,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Disposal/hauling",
            category=CostCategory.MATERIAL,
            unit_cost=0.50,
            unit="sq_ft",
        ),
    ],
)

DEMO_TILE_WALL = Assembly(
    name="Demolition — Tile Wall Removal",
    code="DEMO-TILE-WALL",
    category="demolition",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Wall tile removal labor",
            category=CostCategory.LABOR,
            unit_cost=4.00,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Disposal/hauling",
            category=CostCategory.MATERIAL,
            unit_cost=0.50,
            unit="sq_ft",
        ),
    ],
)

DEMO_COUNTERTOP = Assembly(
    name="Demolition — Countertop Removal",
    code="DEMO-CNTR",
    category="demolition",
    unit="linear_ft",
    components=[
        AssemblyComponent(
            description="Countertop removal labor",
            category=CostCategory.LABOR,
            unit_cost=12.00,
            unit="linear_ft",
        ),
        AssemblyComponent(
            description="Disposal/hauling",
            category=CostCategory.MATERIAL,
            unit_cost=3.00,
            unit="linear_ft",
        ),
    ],
)

DEMO_GENERAL = Assembly(
    name="Demolition — General (cabinets, vanity, fixtures)",
    code="DEMO-GEN",
    category="demolition",
    unit="each",
    components=[
        AssemblyComponent(
            description="General demolition labor",
            category=CostCategory.LABOR,
            unit_cost=150.00,
            unit="each",
        ),
        AssemblyComponent(
            description="Disposal/hauling",
            category=CostCategory.MATERIAL,
            unit_cost=75.00,
            unit="each",
        ),
    ],
)

# --- Prep Work ---

BACKER_CEMENT_BOARD = Assembly(
    name="Cement Backer Board Installation",
    code="BACKER-CBU",
    category="backer_board",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Cement backer board (1/2\")",
            category=CostCategory.MATERIAL,
            unit_cost=1.25,
            unit="sq_ft",
            waste_factor=0.08,
        ),
        AssemblyComponent(
            description="Backer board screws and tape",
            category=CostCategory.MATERIAL,
            unit_cost=0.20,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Backer board installation labor",
            category=CostCategory.LABOR,
            unit_cost=3.00,
            unit="sq_ft",
        ),
    ],
)

WATERPROOF_SHOWER = Assembly(
    name="Shower Waterproofing — Schluter Kerdi System",
    code="WATERPROOF-SHOWER",
    category="waterproofing",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Kerdi membrane",
            category=CostCategory.MATERIAL,
            unit_cost=3.50,
            unit="sq_ft",
            waste_factor=0.10,
        ),
        AssemblyComponent(
            description="Kerdi-Band (seams and corners)",
            category=CostCategory.MATERIAL,
            unit_cost=0.75,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Kerdi-Seal (pipe penetrations)",
            category=CostCategory.MATERIAL,
            unit_cost=0.30,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Waterproofing installation labor",
            category=CostCategory.LABOR,
            unit_cost=5.00,
            unit="sq_ft",
        ),
    ],
)

WATERPROOF_FLOOR = Assembly(
    name="Floor Waterproofing — RedGard/Hydro Ban",
    code="WATERPROOF-FLR",
    category="waterproofing",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Liquid waterproofing membrane (RedGard/Hydro Ban)",
            category=CostCategory.MATERIAL,
            unit_cost=0.75,
            unit="sq_ft",
            waste_factor=0.05,
        ),
        AssemblyComponent(
            description="Waterproofing application labor",
            category=CostCategory.LABOR,
            unit_cost=1.50,
            unit="sq_ft",
        ),
    ],
)

SUBSTRATE_LEVELING = Assembly(
    name="Substrate Leveling — Self-Leveling Compound",
    code="PREP-LEVEL",
    category="prep_work",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Self-leveling compound",
            category=CostCategory.MATERIAL,
            unit_cost=1.50,
            unit="sq_ft",
            waste_factor=0.10,
        ),
        AssemblyComponent(
            description="Primer",
            category=CostCategory.MATERIAL,
            unit_cost=0.25,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Leveling labor",
            category=CostCategory.LABOR,
            unit_cost=3.00,
            unit="sq_ft",
        ),
    ],
)

# --- Plumbing ---

PLUMBING_FIXTURE_DISCONNECT = Assembly(
    name="Plumbing — Fixture Disconnect/Reconnect",
    code="PLUMB-DISC",
    category="plumbing",
    unit="each",
    components=[
        AssemblyComponent(
            description="Plumbing disconnect and reconnect labor",
            category=CostCategory.SUBCONTRACTOR,
            unit_cost=250.00,
            unit="each",
        ),
    ],
)

PLUMBING_ROUGH_IN = Assembly(
    name="Plumbing — Rough-In (new location)",
    code="PLUMB-ROUGH",
    category="plumbing",
    unit="each",
    components=[
        AssemblyComponent(
            description="Plumbing rough-in labor and materials",
            category=CostCategory.SUBCONTRACTOR,
            unit_cost=850.00,
            unit="each",
        ),
    ],
)

# --- Electrical ---

ELECTRICAL_OUTLET = Assembly(
    name="Electrical — Add/Move Outlet",
    code="ELEC-OUTLET",
    category="electrical",
    unit="each",
    components=[
        AssemblyComponent(
            description="Electrical outlet add/move (licensed electrician)",
            category=CostCategory.SUBCONTRACTOR,
            unit_cost=275.00,
            unit="each",
        ),
    ],
)

ELECTRICAL_LIGHTING = Assembly(
    name="Electrical — Recessed Lighting",
    code="ELEC-LIGHT-REC",
    category="electrical",
    unit="each",
    components=[
        AssemblyComponent(
            description="Recessed light fixture and installation",
            category=CostCategory.SUBCONTRACTOR,
            unit_cost=225.00,
            unit="each",
        ),
    ],
)

# --- Finish ---

GROUT_SEALING = Assembly(
    name="Grout Sealing",
    code="FINISH-GROUT-SEAL",
    category="finish",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Grout sealer",
            category=CostCategory.MATERIAL,
            unit_cost=0.15,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Grout sealing labor",
            category=CostCategory.LABOR,
            unit_cost=0.50,
            unit="sq_ft",
        ),
    ],
)

STONE_SEALING = Assembly(
    name="Stone Sealing",
    code="FINISH-STONE-SEAL",
    category="finish",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Stone impregnating sealer",
            category=CostCategory.MATERIAL,
            unit_cost=0.50,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Stone sealing labor",
            category=CostCategory.LABOR,
            unit_cost=1.00,
            unit="sq_ft",
        ),
    ],
)

CAULKING = Assembly(
    name="Caulking — Silicone",
    code="FINISH-CAULK",
    category="finish",
    unit="linear_ft",
    components=[
        AssemblyComponent(
            description="Silicone caulk",
            category=CostCategory.MATERIAL,
            unit_cost=0.50,
            unit="linear_ft",
        ),
        AssemblyComponent(
            description="Caulking labor",
            category=CostCategory.LABOR,
            unit_cost=2.00,
            unit="linear_ft",
        ),
    ],
)

# --- Heated Floor ---

HEATED_FLOOR_ELECTRIC = Assembly(
    name="Electric Radiant Floor Heat",
    code="HEAT-FLR-ELEC",
    category="heated_floor",
    unit="sq_ft",
    components=[
        AssemblyComponent(
            description="Electric heating mat (Schluter DITRA-HEAT / Nuheat)",
            category=CostCategory.MATERIAL,
            unit_cost=8.00,
            unit="sq_ft",
            waste_factor=0.05,
        ),
        AssemblyComponent(
            description="Thermostat and wiring",
            category=CostCategory.MATERIAL,
            unit_cost=1.50,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Heating mat installation labor",
            category=CostCategory.LABOR,
            unit_cost=4.00,
            unit="sq_ft",
        ),
        AssemblyComponent(
            description="Electrician — thermostat hookup",
            category=CostCategory.SUBCONTRACTOR,
            unit_cost=1.00,
            unit="sq_ft",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Assembly registry — lookup by code or category
# ---------------------------------------------------------------------------

ASSEMBLY_REGISTRY: dict[str, Assembly] = {
    a.code: a
    for a in [
        TILE_FLOOR_PORCELAIN_12X24,
        TILE_FLOOR_PORCELAIN_LARGE_FORMAT,
        TILE_FLOOR_MOSAIC,
        TILE_FLOOR_NATURAL_STONE,
        TILE_WALL_SUBWAY,
        TILE_WALL_SHOWER,
        TILE_BACKSPLASH_STANDARD,
        COUNTERTOP_GRANITE_BUDGET,
        COUNTERTOP_GRANITE_MID,
        COUNTERTOP_GRANITE_PREMIUM,
        COUNTERTOP_QUARTZ_MID,
        COUNTERTOP_QUARTZ_PREMIUM,
        COUNTERTOP_MARBLE,
        COUNTERTOP_CUTOUT_STANDARD,
        COUNTERTOP_EDGE_EASED,
        COUNTERTOP_EDGE_BEVELED,
        COUNTERTOP_EDGE_OGEE,
        COUNTERTOP_EDGE_DUPONT,
        COUNTERTOP_BACKSPLASH_4IN,
        DEMO_TILE_FLOOR,
        DEMO_TILE_WALL,
        DEMO_COUNTERTOP,
        DEMO_GENERAL,
        BACKER_CEMENT_BOARD,
        WATERPROOF_SHOWER,
        WATERPROOF_FLOOR,
        SUBSTRATE_LEVELING,
        PLUMBING_FIXTURE_DISCONNECT,
        PLUMBING_ROUGH_IN,
        ELECTRICAL_OUTLET,
        ELECTRICAL_LIGHTING,
        GROUT_SEALING,
        STONE_SEALING,
        CAULKING,
        HEATED_FLOOR_ELECTRIC,
    ]
}


def get_assembly(code: str) -> Assembly | None:
    """Look up an assembly by code."""
    return ASSEMBLY_REGISTRY.get(code)


def get_assemblies_by_category(category: str) -> list[Assembly]:
    """Get all assemblies matching a category."""
    return [a for a in ASSEMBLY_REGISTRY.values() if a.category == category]


# Category mapping: scope category -> best-match assembly code
SCOPE_TO_ASSEMBLY: dict[str, str] = {
    "tile_floor": "TILE-FLR-P1224",
    "tile_wall": "TILE-WALL-SUB",
    "tile_wall_shower": "TILE-WALL-SHOWER",
    "backsplash": "TILE-BACK-STD",
    "countertop": "CNTR-GRAN-MID",
    "countertop_quartz": "CNTR-QUARTZ-MID",
    "countertop_marble": "CNTR-MARBLE-MID",
    "demolition_floor": "DEMO-TILE-FLR",
    "demolition_wall": "DEMO-TILE-WALL",
    "demolition_countertop": "DEMO-CNTR",
    "demolition": "DEMO-GEN",
    "backer_board": "BACKER-CBU",
    "waterproofing": "WATERPROOF-SHOWER",
    "waterproofing_floor": "WATERPROOF-FLR",
    "leveling": "PREP-LEVEL",
    "plumbing": "PLUMB-DISC",
    "plumbing_rough": "PLUMB-ROUGH",
    "electrical": "ELEC-OUTLET",
    "heated_floor": "HEAT-FLR-ELEC",
    "grout_sealing": "FINISH-GROUT-SEAL",
    "stone_sealing": "FINISH-STONE-SEAL",
    "caulking": "FINISH-CAULK",
}
