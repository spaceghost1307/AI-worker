"""CrewAI Crew and Flow definitions for the estimation pipeline.

The estimation pipeline uses CrewAI Flows for deterministic orchestration:
1. Scope Agent parses the project description
2. Image Analysis Agent processes uploaded photos (if any)
3. Estimation Agent calculates costs from scope + image data + RAG
4. Communication Agent generates the client proposal
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from crewai import Agent, Crew, Task
from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel

from src.config.settings import Settings


class EstimationInput(BaseModel):
    """Input data for the estimation pipeline."""

    project_description: str
    photo_paths: list[str] = []
    client_name: str = ""
    project_type: str = ""  # kitchen, bathroom, countertop, tile, full_remodel


class EstimationOutput(BaseModel):
    """Final output from the estimation pipeline."""

    scope_items: list[dict[str, Any]]
    image_analysis: list[dict[str, Any]]
    estimate: dict[str, Any]
    proposal_text: str
    total_cost: float
    confidence: float


def load_agent_configs() -> dict[str, Any]:
    """Load agent definitions from the YAML config file."""
    config_path = Path(__file__).parent.parent / "config" / "agents.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


class EstimationFlow(Flow[dict[str, Any]]):
    """Deterministic flow orchestrating the four-agent estimation pipeline."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self.settings = settings or Settings()
        self.agent_configs = load_agent_configs()

    @start()
    def extract_scope(self) -> dict[str, Any]:
        """Stage 1: Parse project description into structured scope items."""
        # TODO: Initialize Scope Agent with config from agents.yaml
        # TODO: Run scope extraction on self.state["project_description"]
        # TODO: Return structured scope items
        return {"scope_items": [], "missing_info": []}

    @listen(extract_scope)
    def analyze_images(self, scope_result: dict[str, Any]) -> dict[str, Any]:
        """Stage 2: Process project photos through the vision pipeline."""
        # TODO: Initialize Image Analysis Agent
        # TODO: Run three-stage pipeline on each photo
        # TODO: Return structured image analysis results
        return {"image_analysis": [], "scope_items": scope_result["scope_items"]}

    @listen(analyze_images)
    def calculate_estimate(self, analysis_result: dict[str, Any]) -> dict[str, Any]:
        """Stage 3: Generate cost estimate from scope + image data."""
        # TODO: Initialize Estimation Agent
        # TODO: Retrieve relevant cost data via RAG
        # TODO: Run assembly-based calculation
        # TODO: Apply ML refinement
        # TODO: Return detailed estimate breakdown
        return {
            **analysis_result,
            "estimate": {},
            "total_cost": 0.0,
            "confidence": 0.0,
        }

    @listen(calculate_estimate)
    def generate_proposal(self, estimate_result: dict[str, Any]) -> dict[str, Any]:
        """Stage 4: Generate client-facing proposal document."""
        # TODO: Initialize Communication Agent (Claude API)
        # TODO: Render proposal from estimate data + company templates
        # TODO: Return formatted proposal text
        return {
            **estimate_result,
            "proposal_text": "",
        }


def build_crew(settings: Settings | None = None) -> Crew:
    """Build a CrewAI Crew with all four agents for interactive use.

    Use EstimationFlow for deterministic pipeline execution.
    Use this Crew for autonomous agent collaboration on complex projects.
    """
    settings = settings or Settings()
    configs = load_agent_configs()

    # TODO: Instantiate agents from YAML configs with proper LLM routing
    # TODO: Define tasks for each agent
    # TODO: Return configured Crew

    agents: list[Agent] = []
    tasks: list[Task] = []

    return Crew(agents=agents, tasks=tasks, verbose=True)


if __name__ == "__main__":
    flow = EstimationFlow()
    result = flow.kickoff(inputs={"project_description": "Sample project"})
    print(result)
