"""CrewAI Crew and Flow definitions for the estimation pipeline.

The estimation pipeline uses CrewAI Flows for deterministic orchestration:
1. Scope Agent parses the project description
2. Image Analysis Agent processes uploaded photos (if any)
3. Estimation Agent calculates costs from scope + image data + RAG
4. Communication Agent generates the client proposal
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from crewai import Agent, Crew, Task
from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel

from src.agents.communication import CommunicationAgent
from src.agents.estimation import EstimationAgent
from src.agents.image_analysis import ImageAnalysisAgent
from src.agents.scope import ScopeAgent
from src.config.settings import Settings

logger = logging.getLogger(__name__)


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

        # Initialize agents
        self.scope_agent = ScopeAgent(settings=self.settings)
        self.image_agent = ImageAnalysisAgent()
        self.estimation_agent = EstimationAgent(settings=self.settings)
        self.communication_agent = CommunicationAgent(settings=self.settings)

    @start()
    def extract_scope(self) -> dict[str, Any]:
        """Stage 1: Parse project description into structured scope items."""
        description = self.state.get("project_description", "")
        logger.info("Stage 1: Extracting scope from project description")

        result = self.scope_agent.extract_scope(description)

        return {
            "scope_items": [item.model_dump() for item in result.scope_items],
            "project_type": result.project_type,
            "rooms": result.rooms,
            "missing_info": result.missing_info,
            "assumptions": result.assumptions,
        }

    @listen(extract_scope)
    def analyze_images(self, scope_result: dict[str, Any]) -> dict[str, Any]:
        """Stage 2: Process project photos through the vision pipeline."""
        photo_paths = self.state.get("photo_paths", [])
        logger.info("Stage 2: Analyzing %d photos", len(photo_paths))

        image_analysis = []
        if photo_paths:
            assessments = self.image_agent.analyze_project_photos(photo_paths)
            image_analysis = [a.model_dump() for a in assessments]

        return {
            **scope_result,
            "image_analysis": image_analysis,
        }

    @listen(analyze_images)
    def calculate_estimate(self, analysis_result: dict[str, Any]) -> dict[str, Any]:
        """Stage 3: Generate cost estimate from scope + image data."""
        logger.info("Stage 3: Calculating estimate")

        estimate = self.estimation_agent.estimate_from_scope(
            scope_items=analysis_result["scope_items"],
            image_analysis=analysis_result.get("image_analysis"),
        )
        estimate_dict = estimate.model_dump()

        return {
            **analysis_result,
            "estimate": estimate_dict,
            "total_cost": estimate.total,
            "confidence": estimate.confidence,
        }

    @listen(calculate_estimate)
    def generate_proposal(self, estimate_result: dict[str, Any]) -> dict[str, Any]:
        """Stage 4: Generate client-facing proposal document."""
        client_name = self.state.get("client_name", "Valued Client")
        project_type = estimate_result.get("project_type", "remodel")
        logger.info("Stage 4: Generating proposal for %s", client_name)

        proposal = self.communication_agent.generate_proposal(
            estimate=estimate_result["estimate"],
            client_name=client_name,
            project_type=project_type,
        )

        return {
            **estimate_result,
            "proposal_text": proposal.full_text,
            "proposal": proposal.model_dump(),
        }


def build_crew(settings: Settings | None = None) -> Crew:
    """Build a CrewAI Crew with all four agents for interactive use.

    Use EstimationFlow for deterministic pipeline execution.
    Use this Crew for autonomous agent collaboration on complex projects.
    """
    settings = settings or Settings()
    configs = load_agent_configs()

    scope_config = configs.get("scope_agent", {})
    estimation_config = configs.get("estimation_agent", {})
    image_config = configs.get("image_analysis_agent", {})
    comm_config = configs.get("communication_agent", {})

    scope_agent = Agent(
        role=scope_config.get("role", "Project Scope Extractor"),
        goal=scope_config.get("goal", "Extract structured scope from project descriptions"),
        backstory=scope_config.get("backstory", "Experienced remodeling project manager"),
        llm=scope_config.get("llm", "ollama/qwen3:8b"),
        max_iter=scope_config.get("max_iter", 5),
        verbose=scope_config.get("verbose", True),
    )

    estimation_agent = Agent(
        role=estimation_config.get("role", "Remodeling Cost Estimator"),
        goal=estimation_config.get("goal", "Generate accurate cost estimates"),
        backstory=estimation_config.get("backstory", "Certified professional estimator"),
        llm=estimation_config.get("llm", "ollama/qwen3:14b"),
        max_iter=estimation_config.get("max_iter", 10),
        verbose=estimation_config.get("verbose", True),
    )

    image_agent = Agent(
        role=image_config.get("role", "Construction Image Analyst"),
        goal=image_config.get("goal", "Analyze construction photos"),
        backstory=image_config.get("backstory", "Expert construction photographer"),
        llm=image_config.get("llm", "ollama/qwen2.5vl:7b"),
        max_iter=image_config.get("max_iter", 3),
        verbose=image_config.get("verbose", True),
    )

    comm_agent = Agent(
        role=comm_config.get("role", "Client Communications Specialist"),
        goal=comm_config.get("goal", "Generate professional proposals"),
        backstory=comm_config.get("backstory", "Communications specialist"),
        llm=comm_config.get("llm", "anthropic/claude-sonnet-4-20250514"),
        max_iter=comm_config.get("max_iter", 5),
        verbose=comm_config.get("verbose", True),
    )

    scope_task = Task(
        description=(
            "Extract structured scope items from the project "
            "description: {project_description}"
        ),
        expected_output=(
            "Structured JSON with project_type, rooms, "
            "scope_items, missing_info"
        ),
        agent=scope_agent,
    )

    image_task = Task(
        description=(
            "Analyze project photos and identify rooms, "
            "materials, fixtures, and conditions."
        ),
        expected_output=(
            "List of room assessments with materials, "
            "fixtures, dimensions, and conditions"
        ),
        agent=image_agent,
    )

    estimation_task = Task(
        description="Generate a detailed cost estimate based on scope items and image analysis. "
        "Use assembly-based calculations with Bend, OR regional adjustments.",
        expected_output="Detailed estimate breakdown with line items, subtotals, and total",
        agent=estimation_agent,
    )

    proposal_task = Task(
        description="Generate a professional proposal for the client based on the estimate.",
        expected_output="Complete proposal document with scope, pricing, terms, and timeline",
        agent=comm_agent,
    )

    agents = [scope_agent, image_agent, estimation_agent, comm_agent]
    tasks = [scope_task, image_task, estimation_task, proposal_task]

    return Crew(agents=agents, tasks=tasks, verbose=True)


if __name__ == "__main__":
    flow = EstimationFlow()
    result = flow.kickoff(inputs={
        "project_description": "Kitchen remodel: replace countertops with quartz, "
        "new tile backsplash, and tile the floor with porcelain 12x24. "
        "Kitchen is approximately 12x15 feet.",
        "client_name": "Sample Client",
    })
    print(result)
