"""Scope Agent — extracts structured project scope from freeform descriptions.

Parses project descriptions, client emails, walkthrough notes, and voice
transcriptions into structured scope items ready for the Estimation Agent.
Flags missing information that would affect estimate accuracy.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ScopeItem(BaseModel):
    """A single item extracted from the project scope."""

    room: str  # kitchen, master_bath, guest_bath, etc.
    category: str  # demolition, tile, countertop, plumbing, electrical, etc.
    description: str
    quantity_estimate: float | None = None
    unit: str | None = None  # sq_ft, linear_ft, each
    material_selection: str | None = None
    special_conditions: list[str] = []


class ScopeExtractionResult(BaseModel):
    """Complete scope extraction with items and missing information flags."""

    project_type: str  # kitchen_remodel, bathroom_remodel, countertop, tile_only
    rooms: list[str]
    scope_items: list[ScopeItem]
    missing_info: list[str]  # info needed for accurate estimation
    assumptions: list[str]  # assumptions made during extraction
    raw_notes: str = ""


class ScopeAgent:
    """CrewAI-compatible agent for project scope extraction."""

    def __init__(self, settings: Any = None) -> None:
        self.settings = settings
        # TODO: Initialize Ollama client with qwen3:8b

    def extract_scope(self, project_description: str) -> ScopeExtractionResult:
        """Parse a freeform project description into structured scope items.

        Args:
            project_description: Freeform text describing the project.

        Returns:
            Structured scope with items, missing info flags, and assumptions.
        """
        # TODO: Send description to qwen3:8b with structured output prompt
        # TODO: Parse response into ScopeItem models
        # TODO: Identify missing information (dimensions, material choices, etc.)
        # TODO: List assumptions made
        return ScopeExtractionResult(
            project_type="",
            rooms=[],
            scope_items=[],
            missing_info=[],
            assumptions=[],
            raw_notes=project_description,
        )

    def extract_from_email(self, email_text: str) -> ScopeExtractionResult:
        """Extract scope from a client email or inquiry.

        Args:
            email_text: Raw email text from a client.

        Returns:
            Structured scope extraction.
        """
        # TODO: Pre-process email (strip signatures, quoted text)
        # TODO: Run scope extraction
        return self.extract_scope(email_text)

    def extract_from_transcription(self, transcription: str) -> ScopeExtractionResult:
        """Extract scope from a walkthrough voice transcription.

        Args:
            transcription: Transcribed text from a project walkthrough.

        Returns:
            Structured scope extraction.
        """
        # TODO: Clean up transcription artifacts
        # TODO: Run scope extraction with walkthrough-specific prompts
        return self.extract_scope(transcription)
