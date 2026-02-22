"""QuickBooks Online MCP server wrapper.

Intuit provides an official MCP server (intuit/quickbooks-online-mcp-server)
that exposes customer management, estimates, bills, and financial operations
via OAuth authentication.

This module wraps the official server with project-specific convenience tools
and handles OAuth credential management.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("quickbooks")


@mcp.tool()
def create_estimate(
    customer_name: str,
    line_items: list[dict[str, Any]],
    memo: str = "",
) -> dict[str, Any]:
    """Create an estimate in QuickBooks Online.

    Args:
        customer_name: Customer display name in QuickBooks.
        line_items: Estimate line items with description, quantity, rate.
        memo: Internal memo/notes.

    Returns:
        Created estimate with QB ID and doc number.
    """
    # TODO: Map to QuickBooks estimate format
    # TODO: Create via QuickBooks API
    return {}


@mcp.tool()
def create_invoice_from_estimate(estimate_id: str) -> dict[str, Any]:
    """Convert a QuickBooks estimate to an invoice.

    Args:
        estimate_id: QuickBooks estimate ID.

    Returns:
        Created invoice details.
    """
    # TODO: Fetch estimate, convert to invoice via QB API
    return {}


@mcp.tool()
def search_customers(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search for customers in QuickBooks Online.

    Args:
        query: Search query (name, email, company).
        limit: Maximum results.

    Returns:
        Matching customers.
    """
    # TODO: Query QuickBooks customer API
    return []


@mcp.tool()
def get_profit_loss(
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Get profit and loss report for a date range.

    Args:
        start_date: Report start date (YYYY-MM-DD).
        end_date: Report end date (YYYY-MM-DD).

    Returns:
        P&L summary with income, expenses, and net income.
    """
    # TODO: Fetch P&L report via QuickBooks reporting API
    return {}


if __name__ == "__main__":
    mcp.run()
