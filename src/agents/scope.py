"""Scope Agent — extracts structured project scope from freeform descriptions.

Parses project descriptions, client emails, walkthrough notes, and voice
transcriptions into structured scope items ready for the Estimation Agent.
Flags missing information that would affect estimate accuracy.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel

from src.utils.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

SCOPE_EXTRACTION_PROMPT = """\
You are a professional remodeling project scope extractor for Nelson Tile & Stone in Bend, Oregon.

Analyze the following project description and extract a structured scope.

Rules:
- Identify all rooms involved
- Classify the project type (kitchen_remodel, bathroom_remodel, countertop_only, tile_only, full_remodel, other)
- Break down every item of work into individual scope items
- For each scope item, identify: room, category, description, estimated quantity (if inferrable), unit, material selection, and any special conditions
- Categories: demolition, tile_floor, tile_wall, countertop, backsplash, plumbing, electrical, waterproofing, backer_board, painting, cabinetry, fixtures, other
- Units: sq_ft, linear_ft, each, lump_sum
- Flag any missing information that would be needed for an accurate estimate
- List any assumptions you made

Respond with ONLY valid JSON in this exact format:
{
  "project_type": "string",
  "rooms": ["string"],
  "scope_items": [
    {
      "room": "string",
      "category": "string",
      "description": "string",
      "quantity_estimate": null or number,
      "unit": null or "string",
      "material_selection": null or "string",
      "special_conditions": ["string"]
    }
  ],
  "missing_info": ["string"],
  "assumptions": ["string"]
}

Project Description:
"""

EMAIL_PREPROCESS_PROMPT = """\
You are a text processor. Extract ONLY the relevant project scope information from this email.
Remove email signatures, quoted replies, greetings, and pleasantries.
Return just the project-relevant content as clean text.

Email:
"""


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
        ollama_host = "http://localhost:11434"
        scope_model = "qwen3:8b"
        if settings:
            ollama_host = getattr(getattr(settings, "ollama", None), "host", ollama_host)
            scope_model = getattr(getattr(settings, "ollama", None), "scope_model", scope_model)
        self.ollama = OllamaClient(host=ollama_host)
        self.model = scope_model

    def extract_scope(self, project_description: str) -> ScopeExtractionResult:
        """Parse a freeform project description into structured scope items.

        Args:
            project_description: Freeform text describing the project.

        Returns:
            Structured scope with items, missing info flags, and assumptions.
        """
        prompt = SCOPE_EXTRACTION_PROMPT + project_description

        try:
            response = self.ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                format="json",
                temperature=0.3,
            )
            content = response.get("message", {}).get("content", "")
            # Strip thinking tags if present (qwen3 uses /think blocks)
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            parsed = json.loads(content)
        except (json.JSONDecodeError, KeyError, Exception) as exc:
            logger.warning("Failed to parse scope extraction response: %s", exc)
            return ScopeExtractionResult(
                project_type="unknown",
                rooms=[],
                scope_items=[],
                missing_info=["Failed to parse project description — manual review required"],
                assumptions=[],
                raw_notes=project_description,
            )

        scope_items = []
        for item_data in parsed.get("scope_items", []):
            scope_items.append(ScopeItem(
                room=item_data.get("room", "general"),
                category=item_data.get("category", "other"),
                description=item_data.get("description", ""),
                quantity_estimate=item_data.get("quantity_estimate"),
                unit=item_data.get("unit"),
                material_selection=item_data.get("material_selection"),
                special_conditions=item_data.get("special_conditions", []),
            ))

        return ScopeExtractionResult(
            project_type=parsed.get("project_type", "unknown"),
            rooms=parsed.get("rooms", []),
            scope_items=scope_items,
            missing_info=parsed.get("missing_info", []),
            assumptions=parsed.get("assumptions", []),
            raw_notes=project_description,
        )

    def extract_from_email(self, email_text: str) -> ScopeExtractionResult:
        """Extract scope from a client email or inquiry.

        Args:
            email_text: Raw email text from a client.

        Returns:
            Structured scope extraction.
        """
        # Pre-process email to strip signatures and quoted text
        try:
            response = self.ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": EMAIL_PREPROCESS_PROMPT + email_text}],
                temperature=0.1,
            )
            cleaned = response.get("message", {}).get("content", email_text)
            cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()
        except Exception:
            cleaned = email_text

        return self.extract_scope(cleaned)

    def extract_from_transcription(self, transcription: str) -> ScopeExtractionResult:
        """Extract scope from a walkthrough voice transcription.

        Args:
            transcription: Transcribed text from a project walkthrough.

        Returns:
            Structured scope extraction.
        """
        # Clean common transcription artifacts before extraction
        cleaned = transcription
        # Remove filler words common in speech
        for filler in ["um", "uh", "like", "you know", "basically", "so basically"]:
            cleaned = re.sub(rf"\b{filler}\b", "", cleaned, flags=re.IGNORECASE)
        # Collapse multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return self.extract_scope(cleaned)
