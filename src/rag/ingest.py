"""Document ingestion pipeline using Docling and LlamaIndex.

Ingests and chunks construction documents for the RAG knowledge base:
- Cost data (RSMeans, supplier pricing) → row-level chunks
- Building codes (Oregon residential) → section-level chunks
- Material specifications → per-product chunks
- Historical projects (JobTread exports) → per-line-item chunks
- Company pricing/labor rates → row-level chunks

All chunks include metadata for Qdrant filtering: document type, material
category, date, source, region.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel


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
        # TODO: Initialize Docling processor
        # TODO: Initialize LlamaIndex with SemanticSplitterNodeParser
        # TODO: Initialize Qdrant client and collection

    def ingest_file(self, file_path: Path, metadata: DocumentMetadata) -> int:
        """Ingest a single document into the knowledge base.

        Args:
            file_path: Path to the document (PDF, XLSX, CSV, etc.).
            metadata: Base metadata for all chunks from this document.

        Returns:
            Number of chunks created and stored.
        """
        # TODO: Process document with Docling (handles tables, OCR)
        # TODO: Chunk with appropriate strategy based on document_type
        # TODO: Attach metadata to each chunk
        # TODO: Generate embeddings via Ollama (nomic-embed-text)
        # TODO: Store in Qdrant with metadata payload
        return 0

    def ingest_directory(self, directory: Path, metadata: DocumentMetadata) -> int:
        """Ingest all supported documents in a directory.

        Args:
            directory: Path to directory containing documents.
            metadata: Base metadata applied to all documents.

        Returns:
            Total number of chunks created.
        """
        total = 0
        for file_path in directory.iterdir():
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
        # TODO: Parse JobTread export format
        # TODO: Create per-line-item chunks with project metadata
        return self.ingest_file(export_path, metadata)
