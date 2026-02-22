"""Ollama API client for model management and inference.

Handles model loading, inference routing, and VRAM management.
Ollama's OpenAI-compatible API at http://localhost:11434/v1/chat/completions
integrates with CrewAI, LangChain, LlamaIndex, and n8n.
"""

from __future__ import annotations

from typing import Any

import httpx


class OllamaClient:
    """Client for Ollama API operations."""

    def __init__(self, host: str = "http://localhost:11434") -> None:
        self.host = host
        self._client = httpx.Client(timeout=300.0)

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        format: str | None = None,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Send a chat completion request.

        Args:
            model: Ollama model name (e.g., "qwen3:14b").
            messages: Chat messages in OpenAI format.
            format: Response format ("json" for JSON mode).
            temperature: Sampling temperature.

        Returns:
            Chat completion response.
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if format:
            payload["format"] = format

        response = self._client.post(f"{self.host}/api/chat", json=payload)
        response.raise_for_status()
        return response.json()

    def chat_with_images(
        self,
        model: str,
        prompt: str,
        image_paths: list[str],
        format: str | None = None,
    ) -> dict[str, Any]:
        """Send a vision chat request with images.

        Args:
            model: Vision model name (e.g., "qwen2.5vl:7b").
            prompt: Text prompt for image analysis.
            image_paths: Paths to images to analyze.
            format: Response format ("json" for JSON mode).

        Returns:
            Vision model response.
        """
        import base64
        from pathlib import Path

        images = []
        for path in image_paths:
            image_data = Path(path).read_bytes()
            images.append(base64.b64encode(image_data).decode("utf-8"))

        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt, "images": images}],
            "stream": False,
        }
        if format:
            payload["format"] = format

        response = self._client.post(f"{self.host}/api/chat", json=payload)
        response.raise_for_status()
        return response.json()

    def list_models(self) -> list[dict[str, Any]]:
        """List all locally available models.

        Returns:
            List of model info dicts with name, size, and modified date.
        """
        response = self._client.get(f"{self.host}/api/tags")
        response.raise_for_status()
        return response.json().get("models", [])

    def pull_model(self, model: str) -> None:
        """Pull a model from the Ollama registry.

        Args:
            model: Model name to pull (e.g., "qwen3:14b").
        """
        response = self._client.post(
            f"{self.host}/api/pull",
            json={"name": model, "stream": False},
            timeout=600.0,
        )
        response.raise_for_status()

    def is_model_loaded(self, model: str) -> bool:
        """Check if a model is currently loaded in VRAM.

        Args:
            model: Model name to check.

        Returns:
            True if model is loaded and ready.
        """
        response = self._client.get(f"{self.host}/api/ps")
        response.raise_for_status()
        running = response.json().get("models", [])
        return any(m.get("name") == model for m in running)
