"""Tests for MCP server modules (JobTread, Moraware, QuickBooks).

Tests verify tool function logic with mocked HTTP clients — no live API access.
"""

from unittest.mock import MagicMock

import pytest

try:
    from src.mcp_servers import jobtread, moraware, quickbooks
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

pytestmark = pytest.mark.skipif(not HAS_MCP, reason="mcp package not installed")


# ---------------------------------------------------------------------------
# JobTread MCP Server
# ---------------------------------------------------------------------------

class TestJobTreadGraphQL:
    """Test _graphql helper."""

    def test_graphql_query(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"jobs": [{"id": "1"}]}}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        # Inject mocks
        jobtread._client = mock_client
        jobtread._settings = {"api_url": "https://api.jobtread.com/graphql"}

        result = jobtread._graphql("query { jobs { id } }")
        assert result == {"jobs": [{"id": "1"}]}
        mock_client.post.assert_called_once()

    def test_graphql_with_variables(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"job": {"id": "42"}}}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        jobtread._client = mock_client
        jobtread._settings = {"api_url": "https://api.jobtread.com/graphql"}

        result = jobtread._graphql("query GetJob($id: ID!) { job(id: $id) { id } }", {"id": "42"})
        assert result == {"job": {"id": "42"}}
        call_args = mock_client.post.call_args
        assert "variables" in call_args[1]["json"]

    def test_graphql_errors_logged(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"errors": [{"message": "bad"}], "data": {}}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        jobtread._client = mock_client
        jobtread._settings = {"api_url": "https://api.test.com"}

        result = jobtread._graphql("bad query")
        assert result == {}


class TestJobTreadListJobs:
    """Test list_jobs tool."""

    def test_list_jobs_active(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "jobs": [
                    {"id": "1", "name": "Kitchen Remodel", "status": "active"},
                    {"id": "2", "name": "Bath Remodel", "status": "active"},
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        jobtread._client = mock_client
        jobtread._settings = {"api_url": "https://api.test.com"}

        jobs = jobtread.list_jobs(status="active", limit=10)
        assert len(jobs) == 2
        assert jobs[0]["name"] == "Kitchen Remodel"

    def test_list_jobs_all_status(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"jobs": []}}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        jobtread._client = mock_client
        jobtread._settings = {"api_url": "https://api.test.com"}

        jobs = jobtread.list_jobs(status="all")
        assert jobs == []


class TestJobTreadGetJobDetails:
    """Test get_job_details tool."""

    def test_get_details(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "job": {
                    "id": "100",
                    "name": "Smith Kitchen",
                    "lineItems": [{"id": "1", "description": "Tile"}],
                }
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        jobtread._client = mock_client
        jobtread._settings = {"api_url": "https://api.test.com"}

        result = jobtread.get_job_details("100")
        assert result["name"] == "Smith Kitchen"
        assert len(result["lineItems"]) == 1


class TestJobTreadCreateJob:
    """Test create_job tool."""

    def test_create_job(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"createJob": {"id": "new-1", "name": "Test Job", "status": "active", "clientName": "Doe"}}
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        jobtread._client = mock_client
        jobtread._settings = {"api_url": "https://api.test.com"}

        result = jobtread.create_job("Test Job", "Doe", "Kitchen remodel", "kitchen")
        assert result["id"] == "new-1"
        assert result["clientName"] == "Doe"


class TestJobTreadSyncEstimate:
    """Test sync_estimate tool."""

    def test_sync_multiple_items(self) -> None:
        call_count = 0

        mock_client = MagicMock()

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "data": {"createLineItem": {"id": f"li-{call_count}", "description": "item"}}
            }
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_client.post = mock_post

        jobtread._client = mock_client
        jobtread._settings = {"api_url": "https://api.test.com"}

        estimate = {
            "line_items": [
                {"description": "Tile", "category": "material", "quantity": 100, "unit": "sq_ft", "unit_cost": 4.50, "total": 450.0},
                {"description": "Labor", "category": "labor", "quantity": 100, "unit": "sq_ft", "unit_cost": 8.00, "total": 800.0},
            ],
            "total": 1250.0,
        }

        result = jobtread.sync_estimate("job-1", estimate)
        assert result["line_items_created"] == 2
        assert result["total"] == 1250.0

    def test_sync_empty_estimate(self) -> None:
        mock_client = MagicMock()
        jobtread._client = mock_client
        jobtread._settings = {"api_url": "https://api.test.com"}

        result = jobtread.sync_estimate("job-1", {"line_items": [], "total": 0})
        assert result["line_items_created"] == 0


class TestJobTreadSearchContacts:
    """Test search_contacts tool."""

    def test_search(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"contacts": [{"id": "c1", "name": "John Smith", "email": "john@example.com"}]}
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        jobtread._client = mock_client
        jobtread._settings = {"api_url": "https://api.test.com"}

        contacts = jobtread.search_contacts("Smith")
        assert len(contacts) == 1
        assert contacts[0]["name"] == "John Smith"


# ---------------------------------------------------------------------------
# Moraware MCP Server
# ---------------------------------------------------------------------------

class TestMorewareApiGet:
    """Test Moraware _api_get helper."""

    def test_api_get(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "s1", "material": "granite"}]
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        moraware._client = mock_client
        moraware._settings = {"api_key": "test", "api_url": "https://api.moraware.com"}

        result = moraware._api_get("inventory/slabs", {"material": "granite"})
        assert isinstance(result, list)
        mock_client.get.assert_called_once()


class TestMorewareSlabInventory:
    """Test search_slab_inventory tool."""

    def test_search_slabs(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "slabs": [
                {
                    "id": "s1",
                    "material": "granite",
                    "color": "Santa Cecilia",
                    "width": 66,
                    "length": 120,
                    "thickness": "3cm",
                    "lot_number": "LOT-001",
                    "location": "Rack A",
                    "available": True,
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        moraware._client = mock_client
        moraware._settings = {"api_key": "test", "api_url": "https://api.moraware.com"}

        result = moraware.search_slab_inventory(material="granite")
        assert len(result) == 1
        assert result[0]["material"] == "granite"
        assert result[0]["available"] is True

    def test_search_with_dimensions(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"slabs": []}
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        moraware._client = mock_client
        moraware._settings = {"api_key": "test", "api_url": "https://api.moraware.com"}

        result = moraware.search_slab_inventory(min_width_inches=60, min_length_inches=110)
        assert result == []

    def test_search_list_response(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "s1", "material": "quartz", "width": 60, "length": 120, "available": True},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        moraware._client = mock_client
        moraware._settings = {"api_key": "test", "api_url": "https://api.moraware.com"}

        result = moraware.search_slab_inventory(material="quartz")
        assert len(result) == 1


class TestMorewareFabSchedule:
    """Test get_fabrication_schedule tool."""

    def test_get_schedule(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "jobs": [
                {
                    "id": "j1",
                    "name": "Smith Kitchen",
                    "client": "John Smith",
                    "material": "quartz",
                    "fabrication_date": "2025-12-15",
                    "status": "scheduled",
                    "square_feet": 40,
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        moraware._client = mock_client
        moraware._settings = {"api_key": "test", "api_url": "https://api.moraware.com"}

        result = moraware.get_fabrication_schedule(start_date="2025-12-01", end_date="2025-12-31")
        assert len(result) == 1
        assert result[0]["material"] == "quartz"


class TestMorewareJobStatus:
    """Test get_job_status tool."""

    def test_get_status(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "j1",
            "name": "Smith Kitchen",
            "client": "John Smith",
            "status": "in_progress",
            "material": "granite",
            "square_feet": 35,
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        moraware._client = mock_client
        moraware._settings = {"api_key": "test", "api_url": "https://api.moraware.com"}

        result = moraware.get_job_status("j1")
        assert result["name"] == "Smith Kitchen"
        assert result["status"] == "in_progress"

    def test_get_status_non_dict(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = "not a dict"
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        moraware._client = mock_client
        moraware._settings = {"api_key": "test", "api_url": "https://api.moraware.com"}

        result = moraware.get_job_status("j-missing")
        assert result == {}


class TestMorewareMaterialAvailability:
    """Test check_material_availability tool."""

    def test_sufficient_material(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "slabs": [
                {"id": "s1", "material": "granite", "width": 66, "length": 120, "available": True},
                {"id": "s2", "material": "granite", "width": 66, "length": 120, "available": True},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        moraware._client = mock_client
        moraware._settings = {"api_key": "test", "api_url": "https://api.moraware.com"}

        result = moraware.check_material_availability("granite", 40.0)
        assert result["material"] == "granite"
        assert result["available_slabs_count"] == 2
        assert result["total_available_sqft"] > 0
        assert result["sufficient"] is True

    def test_insufficient_material(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"slabs": []}
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        moraware._client = mock_client
        moraware._settings = {"api_key": "test", "api_url": "https://api.moraware.com"}

        result = moraware.check_material_availability("rare_marble", 100.0)
        assert result["sufficient"] is False
        assert result["available_slabs_count"] == 0


# ---------------------------------------------------------------------------
# QuickBooks MCP Server
# ---------------------------------------------------------------------------

class TestQuickBooksApiHelper:
    """Test QuickBooks _qb_api helper."""

    def test_get_request(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"Estimate": {"Id": "1"}}
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        quickbooks._client = mock_client
        quickbooks._settings = {"base_url": "https://sandbox-quickbooks.api.intuit.com"}

        result = quickbooks._qb_api("GET", "estimate/1")
        assert result["Estimate"]["Id"] == "1"
        mock_client.get.assert_called_once()

    def test_post_request(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"Estimate": {"Id": "2", "TotalAmt": 5000}}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        quickbooks._client = mock_client
        quickbooks._settings = {"base_url": "https://sandbox-quickbooks.api.intuit.com"}

        result = quickbooks._qb_api("POST", "estimate", {"test": "data"})
        assert result["Estimate"]["TotalAmt"] == 5000


class TestQuickBooksCreateEstimate:
    """Test create_estimate tool."""

    def test_create_estimate(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Estimate": {"Id": "101", "DocNumber": "EST-001", "TotalAmt": 1500.0}
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        quickbooks._client = mock_client
        quickbooks._settings = {"base_url": "https://sandbox-quickbooks.api.intuit.com"}

        result = quickbooks.create_estimate(
            customer_name="John Smith",
            line_items=[
                {"description": "Tile", "quantity": 100, "rate": 4.50, "total": 450.0},
                {"description": "Labor", "quantity": 100, "rate": 8.00, "total": 800.0},
            ],
            memo="Kitchen remodel estimate",
        )
        assert result["id"] == "101"
        assert result["doc_number"] == "EST-001"
        assert result["status"] == "created"

    def test_create_estimate_minimal(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"Estimate": {"Id": "102"}}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        quickbooks._client = mock_client
        quickbooks._settings = {"base_url": "https://sandbox-quickbooks.api.intuit.com"}

        result = quickbooks.create_estimate("Client", [{"description": "Test"}])
        assert result["id"] == "102"


class TestQuickBooksInvoice:
    """Test create_invoice_from_estimate tool."""

    def test_create_invoice(self) -> None:
        mock_client = MagicMock()

        def mock_handler(url, **kwargs):
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            if "estimate" in url:
                mock_resp.json.return_value = {
                    "Estimate": {
                        "Id": "50",
                        "CustomerRef": {"name": "Doe"},
                        "Line": [{"Amount": 500}],
                    }
                }
            else:
                mock_resp.json.return_value = {
                    "Invoice": {"Id": "200", "DocNumber": "INV-001", "TotalAmt": 500}
                }
            return mock_resp

        mock_client.get = mock_handler
        mock_client.post = mock_handler

        quickbooks._client = mock_client
        quickbooks._settings = {"base_url": "https://sandbox-quickbooks.api.intuit.com"}

        result = quickbooks.create_invoice_from_estimate("50")
        assert result["from_estimate"] == "50"
        assert result["status"] == "created"

    def test_create_invoice_missing_estimate(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"Estimate": {}}
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        quickbooks._client = mock_client
        quickbooks._settings = {"base_url": "https://sandbox-quickbooks.api.intuit.com"}

        result = quickbooks.create_invoice_from_estimate("999")
        assert "error" in result


class TestQuickBooksSearchCustomers:
    """Test search_customers tool."""

    def test_search_customers(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "QueryResponse": {
                "Customer": [
                    {
                        "Id": "c1",
                        "DisplayName": "Jane Doe",
                        "PrimaryEmailAddr": {"Address": "jane@example.com"},
                        "PrimaryPhone": {"FreeFormNumber": "555-1234"},
                        "Balance": 250.0,
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        quickbooks._client = mock_client
        quickbooks._settings = {"base_url": "https://sandbox-quickbooks.api.intuit.com"}

        customers = quickbooks.search_customers("Doe")
        assert len(customers) == 1
        assert customers[0]["display_name"] == "Jane Doe"
        assert customers[0]["email"] == "jane@example.com"

    def test_search_no_results(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"QueryResponse": {"Customer": []}}
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        quickbooks._client = mock_client
        quickbooks._settings = {"base_url": "https://sandbox-quickbooks.api.intuit.com"}

        customers = quickbooks.search_customers("nonexistent")
        assert customers == []


class TestQuickBooksProfitLoss:
    """Test get_profit_loss tool."""

    def test_profit_loss(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Report": {
                "Rows": {
                    "Row": [
                        {
                            "group": "Income",
                            "Header": {"ColData": [{"value": "Total Income"}, {"value": "50000"}]},
                        },
                        {
                            "group": "Expenses",
                            "Header": {"ColData": [{"value": "Total Expenses"}, {"value": "30000"}]},
                        },
                        {
                            "group": "NetIncome",
                            "Header": {"ColData": [{"value": "Net Income"}, {"value": "20000"}]},
                        },
                    ]
                }
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        quickbooks._client = mock_client
        quickbooks._settings = {"base_url": "https://sandbox-quickbooks.api.intuit.com"}

        result = quickbooks.get_profit_loss("2025-01-01", "2025-12-31")
        assert result["total_income"] == 50000.0
        assert result["total_expenses"] == 30000.0
        assert result["net_income"] == 20000.0

    def test_profit_loss_empty(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"Report": {"Rows": {"Row": []}}}
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        quickbooks._client = mock_client
        quickbooks._settings = {"base_url": "https://sandbox-quickbooks.api.intuit.com"}

        result = quickbooks.get_profit_loss("2025-01-01", "2025-12-31")
        assert result["total_income"] == 0.0
        assert result["net_income"] == 0.0
