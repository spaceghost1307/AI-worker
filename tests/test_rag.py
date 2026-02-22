"""Tests for the RAG pipeline components."""

import json
import tempfile
from pathlib import Path

from src.rag.embeddings import EmbeddingClient
from src.rag.ingest import DocumentMetadata, IngestionPipeline


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


class TestIngestionPipeline:
    """Test ingestion pipeline chunking and file processing."""

    def test_pipeline_initialization(self) -> None:
        # Without real Qdrant/Ollama, pipeline initializes gracefully
        pipeline = IngestionPipeline()
        assert pipeline._collection_name == "construction_knowledge"

    def test_chunk_text_small(self) -> None:
        pipeline = IngestionPipeline()
        text = "This is a small document with just a few words."
        chunks = pipeline._chunk_text(text, "cost_data")
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_large(self) -> None:
        pipeline = IngestionPipeline()
        # Create text larger than target chunk size
        words = ["word"] * 500
        text = " ".join(words)
        chunks = pipeline._chunk_text(text, "cost_data")
        assert len(chunks) > 1

    def test_chunk_text_empty(self) -> None:
        pipeline = IngestionPipeline()
        chunks = pipeline._chunk_text("", "cost_data")
        assert chunks == []

    def test_ingest_csv(self) -> None:
        pipeline = IngestionPipeline()
        # Without Qdrant, should return 0 but not crash
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("item,cost,unit\n")
            f.write("Porcelain Tile 12x24,4.50,sq_ft\n")
            f.write("Thinset Mortar,0.45,sq_ft\n")
            tmp_path = Path(f.name)

        meta = DocumentMetadata(document_type="cost_data", source="test")
        result = pipeline.ingest_file(tmp_path, meta)
        # Returns 0 because Qdrant is not running, but no exception
        assert result == 0

    def test_ingest_json(self) -> None:
        pipeline = IngestionPipeline()
        data = [
            {"item": "Granite Slab", "cost": 45.00, "unit": "sq_ft"},
            {"item": "Fabrication", "cost": 35.00, "unit": "sq_ft"},
        ]
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f)
            tmp_path = Path(f.name)

        meta = DocumentMetadata(document_type="cost_data", source="test")
        result = pipeline.ingest_file(tmp_path, meta)
        assert result == 0  # No Qdrant

    def test_ingest_txt(self) -> None:
        pipeline = IngestionPipeline()
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("Oregon Building Code Section 1405\n")
            f.write("Shower waterproofing requirements...")
            tmp_path = Path(f.name)

        meta = DocumentMetadata(document_type="building_code", source="test")
        result = pipeline.ingest_file(tmp_path, meta)
        assert result == 0

    def test_ingest_unsupported_format(self) -> None:
        pipeline = IngestionPipeline()
        with tempfile.NamedTemporaryFile(suffix=".xyz", mode="w", delete=False) as f:
            f.write("unsupported")
            tmp_path = Path(f.name)

        meta = DocumentMetadata(document_type="cost_data", source="test")
        result = pipeline.ingest_file(tmp_path, meta)
        assert result == 0
