"""Qdrant-backed retrieval with metadata filtering for construction knowledge.

Metadata filtering is critical for construction RAG — it narrows results
by material category, document type, date, project ID, or code section
before semantic similarity ranking.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from src.rag.embeddings import EmbeddingClient


class RetrievalResult(BaseModel):
    """A single retrieval result with content, metadata, and score."""

    content: str
    metadata: dict[str, Any]
    score: float


class ConstructionRetriever:
    """Retrieves construction knowledge from Qdrant with metadata filtering."""

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "construction_knowledge",
        embedding_client: EmbeddingClient | None = None,
    ) -> None:
        self.client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name
        self.embeddings = embedding_client or EmbeddingClient()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_type: str | None = None,
        material_category: str | None = None,
        region: str | None = None,
        source: str | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve relevant construction knowledge for a query.

        Args:
            query: Natural language query.
            top_k: Number of results to return.
            document_type: Filter by document type (cost_data, building_code, etc.).
            material_category: Filter by material (tile, stone, countertop, etc.).
            region: Filter by region code (bend_or, portland_or).
            source: Filter by data source (rsm means, jobtread, etc.).

        Returns:
            Ranked list of relevant content with metadata.
        """
        query_vector = self.embeddings.embed_text(query)

        # Build metadata filter
        conditions = []
        if document_type:
            conditions.append(
                FieldCondition(key="document_type", match=MatchValue(value=document_type))
            )
        if material_category:
            conditions.append(
                FieldCondition(key="material_category", match=MatchValue(value=material_category))
            )
        if region:
            conditions.append(FieldCondition(key="region", match=MatchValue(value=region)))
        if source:
            conditions.append(FieldCondition(key="source", match=MatchValue(value=source)))

        search_filter = Filter(must=conditions) if conditions else None

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            query_filter=search_filter,
        )

        return [
            RetrievalResult(
                content=point.payload.get("content", ""),
                metadata={k: v for k, v in point.payload.items() if k != "content"},
                score=point.score,
            )
            for point in results.points
        ]

    def retrieve_cost_data(
        self,
        material: str,
        region: str = "bend_or",
        top_k: int = 3,
    ) -> list[RetrievalResult]:
        """Retrieve cost data for a specific material and region.

        Args:
            material: Material description (e.g., "porcelain tile 12x24").
            region: Region code for regional pricing.
            top_k: Number of results.

        Returns:
            Relevant cost data entries.
        """
        return self.retrieve(
            query=f"cost price rate for {material}",
            top_k=top_k,
            document_type="cost_data",
            region=region,
        )

    def retrieve_building_code(
        self,
        topic: str,
        top_k: int = 3,
    ) -> list[RetrievalResult]:
        """Retrieve relevant building code sections.

        Args:
            topic: Code topic (e.g., "shower waterproofing requirements").
            top_k: Number of results.

        Returns:
            Relevant code sections.
        """
        return self.retrieve(
            query=topic,
            top_k=top_k,
            document_type="building_code",
        )
