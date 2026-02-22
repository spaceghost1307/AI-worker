"""Moraware MCP server — connects AI agents to fabrication scheduling and slab inventory.

Moraware's Systemize product includes an open API. DataBridge Integrations
has deep Moraware API expertise.

This MCP server exposes:
- Slab inventory lookup (material, dimensions, availability)
- Fabrication schedule queries
- Job status tracking
- Template/install scheduling
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("moraware")

_settings: dict[str, str] = {}
_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    """Get or create the HTTP client for Moraware API."""
    global _client
    if _client is None:
        from src.config.settings import Settings

        settings = Settings()
        _settings["api_key"] = settings.moraware.api_key
        _settings["api_url"] = settings.moraware.api_url
        _client = httpx.Client(
            headers={
                "Authorization": f"Bearer {_settings['api_key']}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )
    return _client


def _api_get(endpoint: str, params: dict[str, Any] | None = None) -> Any:
    """Make a GET request to the Moraware API."""
    client = _get_client()
    url = f"{_settings['api_url']}/{endpoint.lstrip('/')}"
    response = client.get(url, params=params)
    response.raise_for_status()
    return response.json()


@mcp.tool()
def search_slab_inventory(
    material: str = "",
    color: str = "",
    min_width_inches: float = 0,
    min_length_inches: float = 0,
) -> list[dict[str, Any]]:
    """Search available slab inventory in Moraware.

    Args:
        material: Material type (granite, quartz, marble, quartzite).
        color: Color/pattern name.
        min_width_inches: Minimum slab width.
        min_length_inches: Minimum slab length.

    Returns:
        Available slabs with dimensions, lot numbers, and location.
    """
    params: dict[str, Any] = {}
    if material:
        params["material"] = material
    if color:
        params["color"] = color
    if min_width_inches > 0:
        params["min_width"] = min_width_inches
    if min_length_inches > 0:
        params["min_length"] = min_length_inches

    data = _api_get("inventory/slabs", params)

    results = []
    for slab in data if isinstance(data, list) else data.get("slabs", []):
        results.append({
            "id": slab.get("id"),
            "material": slab.get("material", ""),
            "color": slab.get("color", ""),
            "width_inches": slab.get("width", 0),
            "length_inches": slab.get("length", 0),
            "thickness": slab.get("thickness", ""),
            "lot_number": slab.get("lot_number", ""),
            "location": slab.get("location", ""),
            "available": slab.get("available", True),
        })
    return results


@mcp.tool()
def get_fabrication_schedule(
    start_date: str = "",
    end_date: str = "",
    status: str = "scheduled",
) -> list[dict[str, Any]]:
    """Get the fabrication schedule from Moraware.

    Args:
        start_date: Start of date range (YYYY-MM-DD).
        end_date: End of date range (YYYY-MM-DD).
        status: Filter by status (scheduled, in_progress, completed).

    Returns:
        Scheduled fabrication jobs with details.
    """
    params: dict[str, Any] = {"status": status}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    data = _api_get("schedule/fabrication", params)

    results = []
    for job in data if isinstance(data, list) else data.get("jobs", []):
        results.append({
            "id": job.get("id"),
            "job_name": job.get("name", ""),
            "client": job.get("client", ""),
            "material": job.get("material", ""),
            "template_date": job.get("template_date"),
            "fabrication_date": job.get("fabrication_date"),
            "install_date": job.get("install_date"),
            "status": job.get("status", ""),
            "square_feet": job.get("square_feet", 0),
        })
    return results


@mcp.tool()
def get_job_status(job_id: str) -> dict[str, Any]:
    """Get current status of a fabrication job in Moraware.

    Args:
        job_id: Moraware job identifier.

    Returns:
        Job status with template date, fabrication date, install date.
    """
    data = _api_get(f"jobs/{job_id}")

    if isinstance(data, dict):
        return {
            "id": data.get("id"),
            "name": data.get("name", ""),
            "client": data.get("client", ""),
            "status": data.get("status", ""),
            "template_date": data.get("template_date"),
            "fabrication_date": data.get("fabrication_date"),
            "install_date": data.get("install_date"),
            "material": data.get("material", ""),
            "color": data.get("color", ""),
            "square_feet": data.get("square_feet", 0),
            "edge_profile": data.get("edge_profile", ""),
        }
    return {}


@mcp.tool()
def check_material_availability(
    material: str,
    square_feet_needed: float,
) -> dict[str, Any]:
    """Check if enough material is in stock for a project.

    Args:
        material: Material name/code.
        square_feet_needed: Required square footage.

    Returns:
        Availability status, matching slabs, and estimated slab count needed.
    """
    slabs = search_slab_inventory(material=material)
    available_slabs = [s for s in slabs if s.get("available", False)]

    total_available_sqft = 0.0
    for slab in available_slabs:
        width_ft = slab.get("width_inches", 0) / 12.0
        length_ft = slab.get("length_inches", 0) / 12.0
        total_available_sqft += width_ft * length_ft

    typical_slab_sqft = 45.0  # 9' x 5'
    slabs_needed = max(1, int(square_feet_needed / (typical_slab_sqft * 0.75)) + 1)

    return {
        "material": material,
        "square_feet_needed": square_feet_needed,
        "available_slabs_count": len(available_slabs),
        "total_available_sqft": round(total_available_sqft, 1),
        "estimated_slabs_needed": slabs_needed,
        "sufficient": total_available_sqft >= square_feet_needed,
        "matching_slabs": available_slabs[:5],
    }


if __name__ == "__main__":
    mcp.run()
