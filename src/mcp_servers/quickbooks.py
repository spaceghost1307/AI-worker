"""QuickBooks Online MCP server wrapper.

Intuit provides an official MCP server (intuit/quickbooks-online-mcp-server)
that exposes customer management, estimates, bills, and financial operations
via OAuth authentication.

This module wraps the official server with project-specific convenience tools
and handles OAuth credential management.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("quickbooks")

_settings: dict[str, str] = {}
_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    """Get or create the HTTP client for QuickBooks API."""
    global _client
    if _client is None:
        from src.config.settings import Settings

        settings = Settings()
        _settings["client_id"] = settings.quickbooks.client_id
        _settings["client_secret"] = settings.quickbooks.client_secret
        _settings["environment"] = settings.quickbooks.environment

        base_url = (
            "https://sandbox-quickbooks.api.intuit.com"
            if _settings["environment"] == "sandbox"
            else "https://quickbooks.api.intuit.com"
        )
        _settings["base_url"] = base_url

        _client = httpx.Client(
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    return _client


def _qb_api(
    method: str, endpoint: str, data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Make a request to the QuickBooks API."""
    client = _get_client()
    url = f"{_settings['base_url']}/v3/company/default/{endpoint}"

    if method.upper() == "GET":
        response = client.get(url)
    else:
        response = client.post(url, json=data)

    response.raise_for_status()
    return response.json()


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
    qb_lines = []
    for idx, item in enumerate(line_items, 1):
        qb_lines.append({
            "Id": str(idx),
            "LineNum": idx,
            "Description": item.get("description", ""),
            "Amount": item.get("total", item.get("quantity", 0) * item.get("rate", 0)),
            "DetailType": "SalesItemLineDetail",
            "SalesItemLineDetail": {
                "Qty": item.get("quantity", 1),
                "UnitPrice": item.get("rate", item.get("unit_cost", 0)),
            },
        })

    estimate_data = {
        "CustomerRef": {"name": customer_name},
        "Line": qb_lines,
        "PrivateNote": memo,
    }

    result = _qb_api("POST", "estimate", estimate_data)
    estimate = result.get("Estimate", {})

    return {
        "id": estimate.get("Id"),
        "doc_number": estimate.get("DocNumber"),
        "total": estimate.get("TotalAmt", 0),
        "status": "created",
    }


@mcp.tool()
def create_invoice_from_estimate(estimate_id: str) -> dict[str, Any]:
    """Convert a QuickBooks estimate to an invoice.

    Args:
        estimate_id: QuickBooks estimate ID.

    Returns:
        Created invoice details.
    """
    estimate_result = _qb_api("GET", f"estimate/{estimate_id}")
    estimate = estimate_result.get("Estimate", {})

    if not estimate:
        return {"error": f"Estimate {estimate_id} not found"}

    invoice_data = {
        "CustomerRef": estimate.get("CustomerRef", {}),
        "Line": estimate.get("Line", []),
        "LinkedTxn": [{
            "TxnId": estimate_id,
            "TxnType": "Estimate",
        }],
    }

    result = _qb_api("POST", "invoice", invoice_data)
    invoice = result.get("Invoice", {})

    return {
        "id": invoice.get("Id"),
        "doc_number": invoice.get("DocNumber"),
        "total": invoice.get("TotalAmt", 0),
        "from_estimate": estimate_id,
        "status": "created",
    }


@mcp.tool()
def search_customers(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search for customers in QuickBooks Online.

    Args:
        query: Search query (name, email, company).
        limit: Maximum results.

    Returns:
        Matching customers.
    """
    # Note: In production, use parameterized queries to prevent injection
    safe_query = query.replace("'", "").replace('"', "")
    sql_query = (
        f"SELECT * FROM Customer WHERE DisplayName LIKE '%{safe_query}%' "
        f"MAXRESULTS {limit}"
    )
    result = _qb_api("GET", f"query?query={sql_query}")

    customers = []
    for customer in result.get("QueryResponse", {}).get("Customer", []):
        customers.append({
            "id": customer.get("Id"),
            "display_name": customer.get("DisplayName", ""),
            "email": customer.get("PrimaryEmailAddr", {}).get("Address", ""),
            "phone": customer.get("PrimaryPhone", {}).get("FreeFormNumber", ""),
            "balance": customer.get("Balance", 0),
        })
    return customers


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
    result = _qb_api(
        "GET",
        f"reports/ProfitAndLoss?start_date={start_date}&end_date={end_date}",
    )

    report = result.get("Report", {})
    rows = report.get("Rows", {}).get("Row", [])

    summary: dict[str, Any] = {
        "start_date": start_date,
        "end_date": end_date,
        "total_income": 0.0,
        "total_expenses": 0.0,
        "net_income": 0.0,
    }

    for row in rows:
        group = row.get("group", "")
        header = row.get("Header", {})
        col_data = header.get("ColData", [])

        if group == "Income" and len(col_data) >= 2:
            summary["total_income"] = float(col_data[1].get("value", 0))
        elif group == "Expenses" and len(col_data) >= 2:
            summary["total_expenses"] = float(col_data[1].get("value", 0))
        elif group == "NetIncome" and len(col_data) >= 2:
            summary["net_income"] = float(col_data[1].get("value", 0))

    return summary


if __name__ == "__main__":
    mcp.run()
