"""JobTread MCP server — connects AI agents to project management data.

JobTread has a GraphQL-style API plus Zapier integration with triggers for
job/contact/document creation and actions for creating jobs, tasks, contacts.

This MCP server exposes JobTread operations as callable tools for AI agents:
- List/search jobs and contacts
- Create new jobs and tasks
- Sync estimates and line items
- Retrieve project history for ML training data
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("jobtread")

_settings: dict[str, str] = {}
_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    """Get or create the HTTP client for JobTread API."""
    global _client
    if _client is None:
        from src.config.settings import Settings

        settings = Settings()
        _settings["api_key"] = settings.jobtread.api_key
        _settings["api_url"] = settings.jobtread.api_url
        _client = httpx.Client(
            headers={
                "Authorization": f"Bearer {_settings['api_key']}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    return _client


def _graphql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a GraphQL query against the JobTread API."""
    client = _get_client()
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables

    response = client.post(_settings["api_url"], json=payload)
    response.raise_for_status()
    result = response.json()

    if "errors" in result:
        logger.error("JobTread GraphQL errors: %s", result["errors"])

    return result.get("data", {})


@mcp.tool()
def list_jobs(status: str = "active", limit: int = 20) -> list[dict[str, Any]]:
    """List jobs from JobTread filtered by status.

    Args:
        status: Job status filter (active, completed, on_hold, all).
        limit: Maximum number of jobs to return.

    Returns:
        List of job summaries with ID, name, client, status, and dates.
    """
    query = """
    query ListJobs($status: String, $limit: Int) {
        jobs(filter: { status: $status }, limit: $limit) {
            id
            name
            status
            clientName
            projectType
            createdAt
            updatedAt
            totalAmount
        }
    }
    """
    variables: dict[str, Any] = {"limit": limit}
    if status != "all":
        variables["status"] = status

    data = _graphql(query, variables)
    return data.get("jobs", [])


@mcp.tool()
def get_job_details(job_id: str) -> dict[str, Any]:
    """Get full details for a specific job including line items and documents.

    Args:
        job_id: JobTread job identifier.

    Returns:
        Complete job details with contacts, line items, tasks, and documents.
    """
    query = """
    query GetJob($jobId: ID!) {
        job(id: $jobId) {
            id
            name
            status
            clientName
            clientEmail
            projectType
            description
            address
            createdAt
            updatedAt
            totalAmount
            lineItems {
                id
                description
                category
                quantity
                unit
                unitCost
                total
            }
            tasks {
                id
                name
                status
                dueDate
            }
            documents {
                id
                name
                type
                url
            }
        }
    }
    """
    data = _graphql(query, {"jobId": job_id})
    return data.get("job", {})


@mcp.tool()
def create_job(
    name: str,
    client_name: str,
    description: str = "",
    project_type: str = "",
) -> dict[str, Any]:
    """Create a new job in JobTread.

    Args:
        name: Job/project name.
        client_name: Client name (creates contact if new).
        description: Project description.
        project_type: Type of project (kitchen, bathroom, countertop, etc.).

    Returns:
        Created job details with ID.
    """
    mutation = """
    mutation CreateJob($input: CreateJobInput!) {
        createJob(input: $input) {
            id
            name
            status
            clientName
        }
    }
    """
    variables = {
        "input": {
            "name": name,
            "clientName": client_name,
            "description": description,
            "projectType": project_type,
        }
    }
    data = _graphql(mutation, variables)
    return data.get("createJob", {})


@mcp.tool()
def sync_estimate(job_id: str, estimate: dict[str, Any]) -> dict[str, Any]:
    """Sync an AI-generated estimate to a JobTread job as line items.

    Args:
        job_id: Target JobTread job ID.
        estimate: Estimate breakdown from the Estimation Agent.

    Returns:
        Sync result with created line item IDs.
    """
    line_items = estimate.get("line_items", [])
    created_ids = []

    mutation = """
    mutation AddLineItem($jobId: ID!, $input: CreateLineItemInput!) {
        createLineItem(jobId: $jobId, input: $input) {
            id
            description
        }
    }
    """

    for item in line_items:
        variables = {
            "jobId": job_id,
            "input": {
                "description": item.get("description", ""),
                "category": item.get("category", ""),
                "quantity": item.get("quantity", 0),
                "unit": item.get("unit", ""),
                "unitCost": item.get("unit_cost", 0),
                "total": item.get("total", 0),
            },
        }
        data = _graphql(mutation, variables)
        created = data.get("createLineItem", {})
        if created.get("id"):
            created_ids.append(created["id"])

    return {
        "job_id": job_id,
        "line_items_created": len(created_ids),
        "line_item_ids": created_ids,
        "total": estimate.get("total", 0),
    }


@mcp.tool()
def search_contacts(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search for contacts in JobTread.

    Args:
        query: Search query (name, email, phone).
        limit: Maximum results.

    Returns:
        Matching contacts.
    """
    gql_query = """
    query SearchContacts($query: String!, $limit: Int) {
        contacts(search: $query, limit: $limit) {
            id
            name
            email
            phone
            company
        }
    }
    """
    data = _graphql(gql_query, {"query": query, "limit": limit})
    return data.get("contacts", [])


if __name__ == "__main__":
    mcp.run()
