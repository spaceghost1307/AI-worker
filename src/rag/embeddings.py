"""Embedding model management for the RAG pipeline.

Primary model: nomic-embed-text (768-dim, 0.5GB VRAM, 8K context)
- Always loaded on GPU alongside the active inference model
- Long context ideal for construction specification documents

Upgrade path: mxbai-embed-large (1024-dim, 1.2GB, higher accuracy)
"""

from __future__ import annotations

import httpx


class EmbeddingClient:
    """Client for generating embeddings via Ollama."""

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
    ) -> None:
        self.ollama_host = ollama_host
        self.model = model
        self._client = httpx.Client(timeout=30.0)

    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text.

        Args:
            text: The text to embed.

        Returns:
            Embedding vector as a list of floats.
        """
        response = self._client.post(
            f"{self.ollama_host}/api/embed",
            json={"model": self.model, "input": text},
        )
        response.raise_for_status()
        data = response.json()
        return data["embeddings"][0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        response = self._client.post(
            f"{self.ollama_host}/api/embed",
            json={"model": self.model, "input": texts},
        )
        response.raise_for_status()
        data = response.json()
        return data["embeddings"]

    def ensure_model_loaded(self) -> bool:
        """Verify the embedding model is loaded and ready.

        Returns:
            True if model is available.
        """
        try:
            response = self._client.post(
                f"{self.ollama_host}/api/show",
                json={"name": self.model},
            )
            return response.status_code == 200
        except httpx.HTTPError:
            return False
