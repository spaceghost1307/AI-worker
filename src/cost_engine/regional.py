"""Regional cost adjustments for Bend, Oregon and surrounding areas.

Key Bend, OR factors:
- No Oregon sales tax (materials cost = list price)
- +5-15% labor premium over Portland baseline (tourism-economy demand)
- Seasonal constraints (snow/freeze season affects scheduling)
- Wildfire code requirements for certain materials
- Higher material transport costs to Central Oregon
- Oregon DOR publishes Local Cost Modifiers (LCM) for Deschutes County
"""

from __future__ import annotations

from pydantic import BaseModel


class RegionalFactors(BaseModel):
    """Cost adjustment factors for a specific region."""

    region_code: str
    region_name: str
    labor_factor: float = 1.0  # multiplier on labor costs
    material_factor: float = 1.0  # multiplier on material costs
    sales_tax_rate: float = 0.0
    transport_surcharge_pct: float = 0.0
    notes: list[str] = []


# Pre-defined regional profiles
BEND_OR = RegionalFactors(
    region_code="bend_or",
    region_name="Bend, Oregon (Deschutes County)",
    labor_factor=1.10,  # 10% premium over Portland baseline
    material_factor=1.0,  # no sales tax, slight transport premium
    sales_tax_rate=0.0,  # Oregon has no sales tax
    transport_surcharge_pct=0.03,  # 3% for Central Oregon delivery
    notes=[
        "No Oregon sales tax on materials",
        "Labor premium driven by tourism-economy demand",
        "Seasonal scheduling constraints (Nov-Mar)",
        "Wildfire-rated materials may be required in WUI zones",
        "Oregon DOR Deschutes County LCM applies",
    ],
)

PORTLAND_OR = RegionalFactors(
    region_code="portland_or",
    region_name="Portland, Oregon (Multnomah County)",
    labor_factor=1.0,  # baseline
    material_factor=1.0,
    sales_tax_rate=0.0,
)

REDMOND_OR = RegionalFactors(
    region_code="redmond_or",
    region_name="Redmond, Oregon (Deschutes County)",
    labor_factor=1.08,
    material_factor=1.0,
    sales_tax_rate=0.0,
    transport_surcharge_pct=0.03,
)

REGIONS: dict[str, RegionalFactors] = {
    "bend_or": BEND_OR,
    "portland_or": PORTLAND_OR,
    "redmond_or": REDMOND_OR,
}


def get_regional_factors(region_code: str) -> RegionalFactors:
    """Look up regional cost factors by code.

    Args:
        region_code: Region identifier (e.g., "bend_or").

    Returns:
        Regional factors for the given region.

    Raises:
        KeyError: If region_code is not found.
    """
    return REGIONS[region_code]


def apply_regional_adjustment(
    base_cost: float,
    category: str,
    region: RegionalFactors,
) -> float:
    """Apply regional adjustment to a base cost.

    Args:
        base_cost: The unadjusted cost.
        category: Cost category ("material", "labor", "equipment").
        region: Regional factors to apply.

    Returns:
        Adjusted cost after regional factors.
    """
    if category == "labor":
        adjusted = base_cost * region.labor_factor
    elif category == "material":
        adjusted = base_cost * region.material_factor
        adjusted += adjusted * region.transport_surcharge_pct
        adjusted += adjusted * region.sales_tax_rate
    else:
        adjusted = base_cost

    return round(adjusted, 2)
