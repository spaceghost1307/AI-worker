"""Tests for the RAG pipeline components."""

from src.rag.embeddings import EmbeddingClient
from src.rag.ingest import DocumentMetadata


class TestDocumentMetadata:
    """Test metadata model for ingested documents."""

    def test_cost_data_metadata(self) -> None:
        meta = DocumentMetadata(
            document_type="cost_data",
            material_category="tile",
            source="supplier_catalog",
            region="bend_or",
            effective_date="2026-01-01",
        )
        assert meta.document_type == "cost_data"
        assert meta.region == "bend_or"

    def test_building_code_metadata(self) -> None:
        meta = DocumentMetadata(
            document_type="building_code",
            source="oregon_residential",
        )
        assert meta.document_type == "building_code"

    def test_project_metadata(self) -> None:
        meta = DocumentMetadata(
            document_type="project",
            source="jobtread",
            project_id="JT-2026-001",
            region="bend_or",
        )
        assert meta.project_id == "JT-2026-001"


class TestEmbeddingClient:
    """Test embedding client initialization (no live Ollama required)."""

    def test_client_initialization(self) -> None:
        client = EmbeddingClient(
            ollama_host="http://localhost:11434",
            model="nomic-embed-text",
        )
        assert client.model == "nomic-embed-text"
        assert client.ollama_host == "http://localhost:11434"

    def test_custom_model(self) -> None:
        client = EmbeddingClient(model="mxbai-embed-large")
        assert client.model == "mxbai-embed-large"
