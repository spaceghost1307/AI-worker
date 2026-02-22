"""Document ingestion pipeline using Docling and LlamaIndex.

Ingests and chunks construction documents for the RAG knowledge base:
- Cost data (RSMeans, supplier pricing) -> row-level chunks
- Building codes (Oregon residential) -> section-level chunks
- Material specifications -> per-product chunks
- Historical projects (JobTread exports) -> per-line-item chunks
- Company pricing/labor rates -> row-level chunks

All chunks include metadata for Qdrant filtering: document type, material
category, date, source, region.
"""

from __future__ import annotations

import csv
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.rag.embeddings import EmbeddingClient

logger = logging.getLogger(__name__)

# Chunk size targets by document type
CHUNK_STRATEGIES: dict[str, dict[str, int]] = {
    "cost_data": {"target_size": 200, "overlap": 20},
    "building_code": {"target_size": 500, "overlap": 50},
    "spec": {"target_size": 300, "overlap": 30},
    "project": {"target_size": 200, "overlap": 20},
    "pricing": {"target_size": 150, "overlap": 10},
}


class DocumentMetadata(BaseModel):
    """Metadata attached to every ingested chunk for Qdrant filtering."""

    document_type: str  # cost_data, building_code, spec, project, pricing
    material_category: str = ""  # tile, stone, countertop, plumbing, etc.
    source: str = ""  # rsm means, supplier_name, jobtread, oregon_dor
    region: str = ""  # bend_or, portland_or, etc.
    effective_date: str = ""
    project_id: str = ""


class IngestionPipeline:
    """Processes documents and stores embeddings in Qdrant."""

    def __init__(self, settings: Any = None) -> None:
        self.settings = settings
        self._qdrant = None
        self._embeddings = None
        self._collection_name = "construction_knowledge"

        qdrant_url = "http://localhost:6333"
        ollama_host = "http://localhost:11434"

        if settings:
            qdrant_url = getattr(getattr(settings, "qdrant", None), "url", qdrant_url)
            self._collection_name = getattr(
                getattr(settings, "qdrant", None), "collection", self._collection_name
            )
            ollama_host = getattr(getattr(settings, "ollama", None), "host", ollama_host)

        try:
            from qdrant_client import QdrantClient

            self._qdrant = QdrantClient(url=qdrant_url)
            self._embeddings = EmbeddingClient(ollama_host=ollama_host)
        except Exception as exc:
            logger.warning("Failed to initialize Qdrant/embedding clients: %s", exc)

    def _ensure_collection(self) -> None:
        """Create Qdrant collection if it doesn't exist."""
        if self._qdrant is None:
            return

        try:
            from qdrant_client.models import Distance, VectorParams

            collections = self._qdrant.get_collections().collections
            exists = any(c.name == self._collection_name for c in collections)
            if not exists:
                self._qdrant.create_collection(
                    collection_name=self._collection_name,
                    vectors_config=VectorParams(
                        size=768,  # nomic-embed-text dimension
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Created Qdrant collection: %s", self._collection_name)
        except Exception as exc:
            logger.error("Failed to ensure Qdrant collection: %s", exc)

    def _chunk_text(self, text: str, doc_type: str) -> list[str]:
        """Split text into chunks based on document type strategy.

        Args:
            text: Full document text.
            doc_type: Document type for chunk size selection.

        Returns:
            List of text chunks.
        """
        strategy = CHUNK_STRATEGIES.get(doc_type, {"target_size": 300, "overlap": 30})
        target = strategy["target_size"]
        overlap = strategy["overlap"]

        words = text.split()
        if len(words) <= target:
            return [text] if text.strip() else []

        chunks = []
        start = 0
        while start < len(words):
            end = min(start + target, len(words))
            chunk = " ".join(words[start:end])
            if chunk.strip():
                chunks.append(chunk)
            start = end - overlap
            if start >= len(words) - overlap:
                break

        return chunks

    def _store_chunks(
        self, chunks: list[str], metadata: DocumentMetadata
    ) -> int:
        """Embed and store chunks in Qdrant.

        Args:
            chunks: Text chunks to store.
            metadata: Metadata for all chunks.

        Returns:
            Number of chunks stored.
        """
        if not chunks or self._qdrant is None or self._embeddings is None:
            return 0

        self._ensure_collection()

        try:
            from qdrant_client.models import PointStruct

            # Batch embed
            vectors = self._embeddings.embed_batch(chunks)

            points = []
            for chunk, vector in zip(chunks, vectors, strict=True):
                point_id = str(uuid.uuid4())
                payload = {
                    "content": chunk,
                    "document_type": metadata.document_type,
                    "material_category": metadata.material_category,
                    "source": metadata.source,
                    "region": metadata.region,
                    "effective_date": metadata.effective_date,
                    "project_id": metadata.project_id,
                }
                points.append(PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                ))

            self._qdrant.upsert(
                collection_name=self._collection_name,
                points=points,
            )
            logger.info("Stored %d chunks in Qdrant", len(points))
            return len(points)
        except Exception as exc:
            logger.error("Failed to store chunks in Qdrant: %s", exc)
            return 0

    def ingest_file(self, file_path: Path, metadata: DocumentMetadata) -> int:
        """Ingest a single document into the knowledge base.

        Args:
            file_path: Path to the document (PDF, XLSX, CSV, etc.).
            metadata: Base metadata for all chunks from this document.

        Returns:
            Number of chunks created and stored.
        """
        suffix = file_path.suffix.lower()

        try:
            if suffix == ".csv":
                return self._ingest_csv(file_path, metadata)
            elif suffix == ".json":
                return self._ingest_json(file_path, metadata)
            elif suffix == ".txt":
                text = file_path.read_text(encoding="utf-8")
                chunks = self._chunk_text(text, metadata.document_type)
                return self._store_chunks(chunks, metadata)
            elif suffix == ".pdf":
                return self._ingest_pdf(file_path, metadata)
            else:
                logger.warning("Unsupported file type: %s", suffix)
                return 0
        except Exception as exc:
            logger.error("Failed to ingest %s: %s", file_path, exc)
            return 0

    def _ingest_csv(self, file_path: Path, metadata: DocumentMetadata) -> int:
        """Ingest a CSV file with row-level chunking."""
        chunks = []
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert row to a readable text chunk
                parts = [f"{k}: {v}" for k, v in row.items() if v]
                if parts:
                    chunks.append("; ".join(parts))
        return self._store_chunks(chunks, metadata)

    def _ingest_json(self, file_path: Path, metadata: DocumentMetadata) -> int:
        """Ingest a JSON file."""
        data = json.loads(file_path.read_text(encoding="utf-8"))

        chunks = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    parts = [f"{k}: {v}" for k, v in item.items() if v]
                    chunks.append("; ".join(parts))
                else:
                    chunks.append(str(item))
        elif isinstance(data, dict):
            text = json.dumps(data, indent=2)
            chunks = self._chunk_text(text, metadata.document_type)
        else:
            chunks = [str(data)]

        return self._store_chunks(chunks, metadata)

    def _ingest_pdf(self, file_path: Path, metadata: DocumentMetadata) -> int:
        """Ingest a PDF file using Docling for extraction."""
        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            result = converter.convert(str(file_path))
            text = result.document.export_to_markdown()
        except ImportError:
            logger.warning("Docling not available — falling back to basic PDF text extraction")
            try:
                import subprocess

                result = subprocess.run(
                    ["pdftotext", str(file_path), "-"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                text = result.stdout
            except Exception:
                logger.error("No PDF extraction method available for %s", file_path)
                return 0
        except Exception as exc:
            logger.error("PDF conversion failed for %s: %s", file_path, exc)
            return 0

        chunks = self._chunk_text(text, metadata.document_type)
        return self._store_chunks(chunks, metadata)

    def ingest_directory(self, directory: Path, metadata: DocumentMetadata) -> int:
        """Ingest all supported documents in a directory.

        Args:
            directory: Path to directory containing documents.
            metadata: Base metadata applied to all documents.

        Returns:
            Total number of chunks created.
        """
        total = 0
        for file_path in sorted(directory.iterdir()):
            if file_path.suffix.lower() in {".pdf", ".csv", ".xlsx", ".xls", ".json", ".txt"}:
                total += self.ingest_file(file_path, metadata)
        return total

    def ingest_jobtread_export(self, export_path: Path) -> int:
        """Ingest a JobTread project data export.

        Args:
            export_path: Path to the JobTread CSV/JSON export.

        Returns:
            Number of chunks created.
        """
        metadata = DocumentMetadata(
            document_type="project",
            source="jobtread",
            region="bend_or",
        )

        suffix = export_path.suffix.lower()
        if suffix == ".json":
            data = json.loads(export_path.read_text(encoding="utf-8"))

            chunks = []
            projects = data if isinstance(data, list) else [data]
            for project in projects:
                project_id = project.get("id", project.get("job_id", ""))
                metadata = DocumentMetadata(
                    document_type="project",
                    source="jobtread",
                    region="bend_or",
                    project_id=str(project_id),
                )

                # Chunk per line item for detailed retrieval
                for item in project.get("line_items", project.get("items", [])):
                    chunk = (
                        f"Project: {project.get('name', 'Unknown')}; "
                        f"Type: {project.get('project_type', '')}; "
                        f"Item: {item.get('description', '')}; "
                        f"Category: {item.get('category', '')}; "
                        f"Quantity: {item.get('quantity', '')} {item.get('unit', '')}; "
                        f"Unit Cost: ${item.get('unit_cost', 0)}; "
                        f"Total: ${item.get('total', 0)}; "
                        f"Date: {project.get('date', project.get('created_at', ''))}"
                    )
                    chunks.append(chunk)

            return self._store_chunks(chunks, metadata)

        return self.ingest_file(export_path, metadata)
