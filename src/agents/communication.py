"""Communication Agent — generates professional client-facing documents.

Uses Claude API for high-quality natural language generation of:
- Project proposals with detailed scope and pricing
- Client emails (follow-ups, clarifications, updates)
- Change orders with cost impact analysis
- Material selection summaries with trade-off explanations
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

PROPOSAL_SYSTEM_PROMPT = """\
You are a professional proposal writer for Nelson Tile & Stone, a premium tile \
installation and countertop fabrication company in Bend, Oregon.

Write professional, clear proposals that:
- Use warm but professional tone
- Explain scope clearly for homeowners (avoid jargon)
- Present pricing transparently with line item detail
- Include material descriptions that help clients visualize the result
- Note what IS and IS NOT included
- Mention Bend, Oregon specifics (no sales tax, seasonal scheduling)

Company info:
- Nelson Tile & Stone, Bend, Oregon
- Specialties: Tile installation, countertop fabrication (natural stone, quartz)
- Licensed, bonded, insured (Oregon CCB)
"""

EMAIL_SYSTEM_PROMPT = """\
You are writing emails on behalf of Nelson Tile & Stone, Bend, Oregon. \
Keep emails concise, professional, and helpful. Use the client's first name \
when available. Be responsive to their specific questions or concerns.
"""

CHANGE_ORDER_SYSTEM_PROMPT = """\
You are drafting a change order for Nelson Tile & Stone. Change orders must \
clearly state: what changed, why it changed, the cost impact (increase or \
decrease), and the new total. Be transparent and factual.
"""


class Proposal(BaseModel):
    """A formatted client proposal."""

    client_name: str
    project_summary: str
    scope_description: str
    pricing_table: str  # Formatted pricing breakdown
    options: list[dict[str, Any]]  # Good/better/best options if applicable
    terms_and_conditions: str
    timeline_estimate: str
    full_text: str  # Complete rendered proposal


class CommunicationAgent:
    """CrewAI-compatible agent for client communications via Claude API."""

    def __init__(self, settings: Any = None) -> None:
        self.settings = settings
        self._client = None
        api_key = ""
        if settings:
            api_key = getattr(settings, "anthropic_api_key", "")
        if api_key:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=api_key)
            except Exception as exc:
                logger.warning("Failed to initialize Anthropic client: %s", exc)

    def _call_claude(self, system: str, user_prompt: str) -> str:
        """Send a prompt to Claude API and return the response text.

        Args:
            system: System prompt for Claude.
            user_prompt: User message content.

        Returns:
            Response text from Claude, or empty string on failure.
        """
        if self._client is None:
            logger.warning("Anthropic client not initialized — returning template fallback")
            return ""

        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        except Exception as exc:
            logger.error("Claude API call failed: %s", exc)
            return ""

    def _format_pricing_table(self, estimate: dict[str, Any]) -> str:
        """Format estimate line items into a readable pricing table."""
        lines = ["| Item | Qty | Unit | Cost |", "|------|-----|------|------|"]

        for li in estimate.get("line_items", []):
            desc = li.get("description", "")
            qty = li.get("quantity", 0)
            unit = li.get("unit", "")
            total = li.get("total", 0)
            lines.append(f"| {desc} | {qty:.1f} | {unit} | ${total:,.2f} |")

        lines.append("|------|-----|------|------|")
        mat_sub = estimate.get("subtotal_materials", 0)
        lab_sub = estimate.get("subtotal_labor", 0)
        lines.append(f"| **Materials Subtotal** | | | ${mat_sub:,.2f} |")
        lines.append(f"| **Labor Subtotal** | | | ${lab_sub:,.2f} |")

        overhead = estimate.get("overhead_pct", 0.10)
        profit = estimate.get("profit_pct", 0.10)
        contingency = estimate.get("contingency_pct", 0.10)
        markup_label = (
            f"Overhead ({overhead:.0%}) + Profit ({profit:.0%})"
            f" + Contingency ({contingency:.0%})"
        )
        lines.append(f"| {markup_label} | | | included |")
        lines.append(f"| **TOTAL** | | | **${estimate.get('total', 0):,.2f}** |")

        return "\n".join(lines)

    def generate_proposal(
        self,
        estimate: dict[str, Any],
        client_name: str,
        project_type: str,
    ) -> Proposal:
        """Generate a professional project proposal from an estimate.

        Args:
            estimate: Detailed estimate breakdown from the Estimation Agent.
            client_name: Client's name for personalization.
            project_type: Type of project for template selection.

        Returns:
            Formatted proposal ready for client delivery.
        """
        pricing_table = self._format_pricing_table(estimate)
        total = estimate.get("total", 0)
        notes = estimate.get("notes", [])

        user_prompt = f"""\
Generate a professional project proposal for the following:

Client: {client_name}
Project Type: {project_type}
Location: Bend, Oregon

Pricing:
{pricing_table}

Total Investment: ${total:,.2f}

Notes: {'; '.join(notes) if notes else 'None'}

Please generate:
1. A 2-3 sentence project summary
2. A detailed scope description (what's included and not included)
3. Terms and conditions (payment schedule, warranty, timeline)
4. An estimated timeline

Format as a complete proposal letter.
"""

        full_text = self._call_claude(PROPOSAL_SYSTEM_PROMPT, user_prompt)

        if not full_text:
            full_text = self._template_proposal(client_name, project_type, pricing_table, total)

        return Proposal(
            client_name=client_name,
            project_summary=f"{project_type.replace('_', ' ').title()} project for {client_name}",
            scope_description=f"See detailed breakdown below. Total: ${total:,.2f}",
            pricing_table=pricing_table,
            options=[],
            terms_and_conditions=(
                "50% deposit due upon acceptance. Balance due upon completion. "
                "Nelson Tile & Stone provides a 2-year workmanship warranty. "
                "Materials carry manufacturer warranty."
            ),
            timeline_estimate="Estimated 2-4 weeks from deposit to completion, "
            "subject to material availability and scheduling.",
            full_text=full_text,
        )

    def _template_proposal(
        self, client_name: str, project_type: str, pricing_table: str, total: float
    ) -> str:
        """Generate a template-based proposal when Claude API is unavailable."""
        return f"""\
NELSON TILE & STONE
Project Proposal
================

Dear {client_name},

Thank you for the opportunity to provide this estimate for your \
{project_type.replace('_', ' ')} project.

SCOPE OF WORK
{'-' * 40}
Please see the detailed pricing breakdown below.

PRICING
{'-' * 40}
{pricing_table}

TOTAL INVESTMENT: ${total:,.2f}

Note: Oregon has no sales tax — the price above is your complete investment.

TERMS & CONDITIONS
{'-' * 40}
- 50% deposit due upon acceptance
- Balance due upon completion
- 2-year workmanship warranty
- Materials carry manufacturer warranty
- Estimated timeline: 2-4 weeks from deposit

We look forward to working with you!

Nelson Tile & Stone
Bend, Oregon
"""

    def generate_email(
        self,
        purpose: str,
        context: dict[str, Any],
        tone: str = "professional",
    ) -> str:
        """Generate a client email.

        Args:
            purpose: Email purpose (follow_up, clarification, update, thank_you).
            context: Relevant project/client context.
            tone: Desired tone (professional, friendly, formal).

        Returns:
            Formatted email text.
        """
        client_name = context.get("client_name", "Client")
        project_type = context.get("project_type", "project")
        details = context.get("details", "")

        user_prompt = f"""\
Write a {tone} {purpose.replace('_', ' ')} email.

Client: {client_name}
Project: {project_type}
Details: {details}

Keep it concise (2-3 paragraphs max).
"""

        result = self._call_claude(EMAIL_SYSTEM_PROMPT, user_prompt)

        if not result:
            greetings = {
                "follow_up": f"Hi {client_name},\n\nI wanted to follow up on your "
                f"{project_type.replace('_', ' ')} project. {details}\n\n"
                "Please let me know if you have any questions.\n\nBest,\nNelson Tile & Stone",
                "thank_you": f"Hi {client_name},\n\nThank you for choosing Nelson Tile & Stone "
                f"for your {project_type.replace('_', ' ')} project. "
                "We appreciate your business!\n\nBest,\nNelson Tile & Stone",
            }
            result = greetings.get(
                purpose,
                f"Hi {client_name},\n\n{details}\n\nBest,\nNelson Tile & Stone",
            )

        return result

    def generate_change_order(
        self,
        original_estimate: dict[str, Any],
        changes: list[dict[str, Any]],
    ) -> str:
        """Generate a change order document with cost impact.

        Args:
            original_estimate: The original approved estimate.
            changes: List of scope changes with descriptions.

        Returns:
            Formatted change order document.
        """
        original_total = original_estimate.get("total", 0)
        change_descriptions = []
        total_delta = 0.0

        for change in changes:
            desc = change.get("description", "")
            delta = change.get("cost_delta", 0.0)
            total_delta += delta
            sign = "+" if delta >= 0 else ""
            change_descriptions.append(f"- {desc}: {sign}${delta:,.2f}")

        new_total = original_total + total_delta

        user_prompt = f"""\
Generate a change order document.

Original Estimate Total: ${original_total:,.2f}
Changes:
{chr(10).join(change_descriptions)}
Cost Impact: {"+" if total_delta >= 0 else ""}${total_delta:,.2f}
New Total: ${new_total:,.2f}

Write a clear, professional change order that the client can review and approve.
"""

        result = self._call_claude(CHANGE_ORDER_SYSTEM_PROMPT, user_prompt)

        if not result:
            result = f"""\
CHANGE ORDER — Nelson Tile & Stone
{'=' * 40}

Original Estimate: ${original_total:,.2f}

Changes:
{chr(10).join(change_descriptions)}

Cost Impact: {"+" if total_delta >= 0 else ""}${total_delta:,.2f}
NEW TOTAL: ${new_total:,.2f}

Client Signature: ____________________  Date: ________
"""

        return result
