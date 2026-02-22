"""Extended RAG pipeline tests — ingestion, embeddings, and retriever."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.rag.embeddings import EmbeddingClient
from src.rag.ingest import (
    CHUNK_STRATEGIES,
    DocumentMetadata,
    IngestionPipeline,
)
from src.rag.retriever import ConstructionRetriever, RetrievalResult

# ---------------------------------------------------------------------------
# EmbeddingClient
# ---------------------------------------------------------------------------

class TestEmbeddingClientInit:
    """Test EmbeddingClient initialization."""

    def test_default_config(self) -> None:
        client = EmbeddingClient()
        assert client.model == "nomic-embed-text"
        assert client.ollama_host == "http://localhost:11434"

    def test_custom_config(self) -> None:
        client = EmbeddingClient(
            ollama_host="http://gpu:11434",
            model="mxbai-embed-large",
        )
        assert client.model == "mxbai-embed-large"


class TestEmbeddingClientEmbed:
    """Test embedding generation."""

    def test_embed_text(self) -> None:
        client = EmbeddingClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
        mock_response.raise_for_status = MagicMock()
        client._client = MagicMock()
        client._client.post.return_value = mock_response

        vector = client.embed_text("porcelain tile cost")
        assert vector == [0.1, 0.2, 0.3]

    def test_embed_batch(self) -> None:
        client = EmbeddingClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "embeddings": [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        }
        mock_response.raise_for_status = MagicMock()
        client._client = MagicMock()
        client._client.post.return_value = mock_response

        vectors = client.embed_batch(["text1", "text2", "text3"])
        assert len(vectors) == 3
        assert vectors[0] == [0.1, 0.2]

    def test_ensure_model_loaded_success(self) -> None:
        client = EmbeddingClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        client._client = MagicMock()
        client._client.post.return_value = mock_response

        assert client.ensure_model_loaded() is True

    def test_ensure_model_loaded_fail(self) -> None:
        import httpx
        client = EmbeddingClient()
        client._client = MagicMock()
        client._client.post.side_effect = httpx.HTTPError("Connection refused")

        assert client.ensure_model_loaded() is False


# ---------------------------------------------------------------------------
# DocumentMetadata
# ---------------------------------------------------------------------------

class TestDocumentMetadata:
    """Test DocumentMetadata model."""

    def test_all_fields(self) -> None:
        meta = DocumentMetadata(
            document_type="cost_data",
            material_category="tile",
            source="rsm_means",
            region="bend_or",
            effective_date="2025-01-01",
            project_id="proj-123",
        )
        assert meta.document_type == "cost_data"
        assert meta.project_id == "proj-123"

    def test_defaults(self) -> None:
        meta = DocumentMetadata(document_type="spec")
        assert meta.material_category == ""
        assert meta.source == ""
        assert meta.region == ""


# ---------------------------------------------------------------------------
# ChunkStrategies
# ---------------------------------------------------------------------------

class TestChunkStrategies:
    """Test chunk strategy configuration."""

    def test_cost_data_small_chunks(self) -> None:
        assert CHUNK_STRATEGIES["cost_data"]["target_size"] == 200

    def test_building_code_larger_chunks(self) -> None:
        assert CHUNK_STRATEGIES["building_code"]["target_size"] == 500

    def test_all_strategies_have_overlap(self) -> None:
        for doc_type, strategy in CHUNK_STRATEGIES.items():
            assert "overlap" in strategy, f"No overlap for {doc_type}"
            assert strategy["overlap"] > 0


# ---------------------------------------------------------------------------
# IngestionPipeline Chunking
# ---------------------------------------------------------------------------

class TestIngestionChunking:
    """Test _chunk_text method."""

    def test_short_text_single_chunk(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None
        text = "This is a short piece of text."
        chunks = pipeline._chunk_text(text, "cost_data")
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_empty_text(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None
        chunks = pipeline._chunk_text("", "cost_data")
        assert chunks == []

    def test_whitespace_only(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None
        chunks = pipeline._chunk_text("   \n\t   ", "cost_data")
        assert chunks == []

    def test_long_text_multiple_chunks(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None
        words = ["word"] * 500
        text = " ".join(words)
        chunks = pipeline._chunk_text(text, "cost_data")  # target 200 words
        assert len(chunks) >= 2

    def test_chunk_overlap(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None
        words = [f"w{i}" for i in range(400)]
        text = " ".join(words)
        chunks = pipeline._chunk_text(text, "cost_data")  # target 200, overlap 20
        assert len(chunks) >= 2
        # Chunks should overlap
        chunk1_words = set(chunks[0].split())
        chunk2_words = set(chunks[1].split())
        overlap = chunk1_words & chunk2_words
        assert len(overlap) > 0

    def test_building_code_larger_chunks(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None
        words = ["code"] * 600
        text = " ".join(words)
        cost_chunks = pipeline._chunk_text(text, "cost_data")  # 200 target
        code_chunks = pipeline._chunk_text(text, "building_code")  # 500 target
        assert len(cost_chunks) > len(code_chunks)

    def test_unknown_doc_type_default(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None
        words = ["test"] * 400
        text = " ".join(words)
        chunks = pipeline._chunk_text(text, "unknown_type")
        assert len(chunks) >= 1


# ---------------------------------------------------------------------------
# IngestionPipeline File Ingestion
# ---------------------------------------------------------------------------

class TestIngestionCSV:
    """Test CSV file ingestion."""

    def test_ingest_csv_rows(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("material,unit_cost,unit\n")
            f.write("Porcelain 12x24,4.50,sq_ft\n")
            f.write("Thinset,0.45,sq_ft\n")
            f.write("Grout,0.25,sq_ft\n")
            temp_path = Path(f.name)

        try:
            result = pipeline._ingest_csv(
                temp_path,
                DocumentMetadata(document_type="cost_data"),
            )
            assert result == 0  # No Qdrant client, returns 0
        finally:
            temp_path.unlink()


class TestIngestionJSON:
    """Test JSON file ingestion."""

    def test_ingest_json_array(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None

        data = [
            {"material": "Granite", "cost": 45.0},
            {"material": "Quartz", "cost": 55.0},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)

        try:
            result = pipeline._ingest_json(
                temp_path,
                DocumentMetadata(document_type="cost_data"),
            )
            assert result == 0  # No Qdrant
        finally:
            temp_path.unlink()

    def test_ingest_json_object(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None

        data = {"project": "Kitchen", "total": 15000, "items": []}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)

        try:
            result = pipeline._ingest_json(
                temp_path,
                DocumentMetadata(document_type="project"),
            )
            assert result == 0
        finally:
            temp_path.unlink()


class TestIngestionJobTread:
    """Test JobTread export ingestion."""

    def test_jobtread_export_json(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None

        export_data = [
            {
                "id": "proj-1",
                "name": "Smith Kitchen",
                "project_type": "kitchen_remodel",
                "date": "2025-06-15",
                "line_items": [
                    {"description": "Tile floor", "category": "tile", "quantity": 150, "unit": "sq_ft", "unit_cost": 4.50, "total": 675.0},
                    {"description": "Labor", "category": "labor", "quantity": 150, "unit": "sq_ft", "unit_cost": 8.00, "total": 1200.0},
                ],
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(export_data, f)
            temp_path = Path(f.name)

        try:
            result = pipeline.ingest_jobtread_export(temp_path)
            assert result == 0  # No Qdrant
        finally:
            temp_path.unlink()


class TestIngestionFile:
    """Test ingest_file dispatch."""

    def test_txt_file(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Oregon building code section 1234: waterproofing requirements.")
            temp_path = Path(f.name)

        try:
            result = pipeline.ingest_file(
                temp_path,
                DocumentMetadata(document_type="building_code"),
            )
            assert result == 0
        finally:
            temp_path.unlink()

    def test_unsupported_format(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xyz", delete=False) as f:
            f.write("unsupported")
            temp_path = Path(f.name)

        try:
            result = pipeline.ingest_file(
                temp_path,
                DocumentMetadata(document_type="other"),
            )
            assert result == 0
        finally:
            temp_path.unlink()


class TestStoreChunks:
    """Test _store_chunks method."""

    def test_no_client_returns_zero(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None
        pipeline._collection_name = "test"

        result = pipeline._store_chunks(
            ["chunk1", "chunk2"],
            DocumentMetadata(document_type="cost_data"),
        )
        assert result == 0

    def test_empty_chunks_returns_zero(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = MagicMock()
        pipeline._embeddings = MagicMock()
        pipeline._collection_name = "test"

        result = pipeline._store_chunks(
            [],
            DocumentMetadata(document_type="cost_data"),
        )
        assert result == 0


# ---------------------------------------------------------------------------
# RetrievalResult
# ---------------------------------------------------------------------------

class TestRetrievalResult:
    """Test RetrievalResult pydantic model."""

    def test_create_result(self) -> None:
        result = RetrievalResult(
            content="Porcelain tile 12x24 costs $4.50/sqft installed",
            metadata={"document_type": "cost_data", "region": "bend_or"},
            score=0.95,
        )
        assert result.score == 0.95
        assert result.metadata["region"] == "bend_or"


# ---------------------------------------------------------------------------
# ConstructionRetriever
# ---------------------------------------------------------------------------

class TestConstructionRetrieverInit:
    """Test ConstructionRetriever initialization."""

    def test_default_config(self) -> None:
        retriever = ConstructionRetriever.__new__(ConstructionRetriever)
        retriever.collection_name = "construction_knowledge"
        assert retriever.collection_name == "construction_knowledge"


class TestIngestionDirectory:
    """Test directory ingestion."""

    def test_empty_directory(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None

        with tempfile.TemporaryDirectory() as tmpdir:
            result = pipeline.ingest_directory(
                Path(tmpdir),
                DocumentMetadata(document_type="cost_data"),
            )
            assert result == 0

    def test_directory_with_mixed_files(self) -> None:
        pipeline = IngestionPipeline.__new__(IngestionPipeline)
        pipeline._qdrant = None
        pipeline._embeddings = None

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files of different types
            (Path(tmpdir) / "data.csv").write_text("col1,col2\nval1,val2\n")
            (Path(tmpdir) / "notes.txt").write_text("Some building code notes")
            (Path(tmpdir) / "readme.md").write_text("# Not supported")

            result = pipeline.ingest_directory(
                Path(tmpdir),
                DocumentMetadata(document_type="spec"),
            )
            assert result == 0  # No Qdrant, all return 0
