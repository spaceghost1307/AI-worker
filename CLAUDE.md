# CLAUDE.md — AI-Worker Project Guide

## Project Overview

AI-Worker is an open-source multi-agent AI estimation system for remodeling and construction, built for Nelson Tile & Stone in Bend, Oregon. It uses four specialized AI agents orchestrated by CrewAI to automate project estimation — from photo analysis through cost calculation to client proposal generation.

The system runs on a self-hosted Proxmox server with local Ollama inference (Qwen models on an RTX 5070 Ti with 16GB VRAM) and hybrid Claude API access for high-quality client-facing outputs.

## Architecture

### Four-Agent System

| Agent | Model | Role |
|-------|-------|------|
| **Image Analysis** | `qwen2.5vl:7b` (local) | Three-stage vision pipeline: Florence-2 detection → Depth Anything V3 measurement → Qwen2.5-VL scene analysis |
| **Scope** | `qwen3:8b` (local) | Parses project descriptions, transcriptions, and emails into structured scope items |
| **Estimation** | `qwen3:14b` (local) + Claude API | Assembly-based cost calculation with RAG-retrieved data and ML refinement |
| **Communication** | Claude API | Generates proposals, emails, change orders using company-branded templates |

### Core Tech Stack

- **Orchestration**: CrewAI (Crews for agent collaboration, Flows for deterministic pipelines)
- **Local LLM**: Ollama with Qwen model family
- **Vector DB**: Qdrant (metadata filtering for construction domains)
- **RAG Framework**: LlamaIndex (document ingestion, semantic chunking, query routing)
- **Document Processing**: Docling (PDF/table extraction at 97.9% accuracy)
- **Embeddings**: nomic-embed-text (768-dim, 8K context, always loaded at 0.5GB)
- **Cost Engine**: Assembly-based calculations + XGBoost/LightGBM ML refinement
- **Workflow Automation**: n8n (business process orchestration)
- **Database**: PostgreSQL + pgvector
- **MCP Servers**: FastMCP for JobTread, Moraware, QuickBooks integrations
- **Infrastructure**: Docker Compose on Proxmox LXC with GPU passthrough

## Project Structure

```
AI-worker/
├── CLAUDE.md                 # This file — project guide for AI assistants
├── README.md                 # Project overview and quick start
├── pyproject.toml            # Python dependencies and tool configuration
├── Dockerfile                # Application container
├── docker-compose.yml        # Full infrastructure stack
├── .env.example              # Environment variable template
├── .gitignore
├── src/
│   ├── config/
│   │   ├── settings.py       # Pydantic BaseSettings (env-based config)
│   │   └── agents.yaml       # CrewAI agent definitions (roles, goals, backstories)
│   ├── agents/
│   │   ├── crew.py           # CrewAI Crew + Flow definitions
│   │   ├── image_analysis.py # Image Analysis Agent
│   │   ├── estimation.py     # Estimation Agent
│   │   ├── scope.py          # Scope Agent
│   │   └── communication.py  # Communication Agent
│   ├── cost_engine/
│   │   ├── assemblies.py     # Assembly-based cost calculations
│   │   ├── regional.py       # Regional adjustments (Bend, OR specifics)
│   │   └── ml_refiner.py     # ML model refinement (XGBoost/LightGBM)
│   ├── rag/
│   │   ├── ingest.py         # Document ingestion (Docling + LlamaIndex)
│   │   ├── embeddings.py     # Embedding model management
│   │   └── retriever.py      # Qdrant retrieval with metadata filtering
│   ├── mcp_servers/
│   │   ├── jobtread.py       # JobTread MCP server (FastMCP)
│   │   ├── moraware.py       # Moraware MCP server (FastMCP)
│   │   └── quickbooks.py     # QuickBooks Online MCP server wrapper
│   ├── vision/
│   │   ├── pipeline.py       # Three-stage vision pipeline orchestration
│   │   ├── detection.py      # Florence-2 object detection
│   │   ├── depth.py          # Depth Anything V3 room measurement
│   │   └── analysis.py       # Qwen2.5-VL scene analysis
│   └── utils/
│       └── ollama_client.py  # Ollama API client and model management
├── tests/
│   ├── test_cost_engine.py
│   ├── test_agents.py
│   └── test_rag.py
├── data/                     # Local cost data, templates, training data
├── docs/
│   └── architecture.md       # Full architecture document
└── n8n/
    └── workflows/            # Exported n8n workflow JSON files
```

## Development Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type checking
mypy src/

# Start infrastructure (Docker Compose)
docker compose up -d

# Start only core services (Ollama, Qdrant, PostgreSQL)
docker compose up -d ollama qdrant postgres

# Pull required Ollama models
ollama pull qwen3:14b
ollama pull qwen2.5vl:7b
ollama pull qwen3:8b
ollama pull nomic-embed-text

# Run the estimation crew
python -m src.agents.crew

# Run a specific MCP server
python -m src.mcp_servers.jobtread
```

## Coding Conventions

### Python Style
- Python 3.11+ required
- Use `ruff` for linting and formatting (configured in `pyproject.toml`)
- Use `mypy` for type checking — type hints required on all public functions
- Use Pydantic models for all data structures passed between agents
- Use `pydantic-settings` for configuration (environment variables)

### Agent Definitions
- Agent roles, goals, and backstories are defined in `src/config/agents.yaml`
- Agent Python classes in `src/agents/` implement tool methods and processing logic
- CrewAI Flows define deterministic execution order; Crews handle agent collaboration
- Each agent file exports a single class that encapsulates the agent's capabilities

### Model Routing
- Local Ollama models for high-volume, cost-sensitive tasks (scope extraction, image analysis, embeddings)
- Claude API for complex reasoning (estimation edge cases) and client-facing text (proposals, emails)
- Model selection is configured per-agent in `agents.yaml`, not hardcoded

### Cost Engine
- Assembly-based calculations are the source of truth — every cost traces to materials + labor + waste
- ML refinement adjusts assembly estimates, never replaces them
- Regional adjustments for Bend, OR: no sales tax, +5-15% labor over Portland baseline
- All cost data includes effective dates and sources for auditability

### MCP Servers
- Built with FastMCP (from the `mcp` Python SDK)
- Each server is a standalone module that can run independently
- Tools are decorated with `@mcp.tool()` with full type hints and docstrings
- Authentication credentials come from environment variables via `settings.py`

### RAG Pipeline
- Documents are chunked semantically using LlamaIndex's `SemanticSplitterNodeParser`
- All chunks include metadata: document type, material category, date, source, region
- Cost data → row-level chunks; building codes → section-level chunks; projects → line-item chunks
- Qdrant metadata filtering narrows retrieval before semantic search

### Vision Pipeline
- Three-stage process: detection (Florence-2) → depth (Depth Anything V3) → analysis (Qwen2.5-VL)
- All outputs are structured JSON with bounding boxes and confidence scores
- Pipeline is modular — stages can be run independently or skipped

### Testing
- Tests use `pytest` with fixtures for Ollama mock responses and Qdrant test collections
- Cost engine tests validate assembly calculations against known reference values
- Agent tests verify structured output schemas without requiring live model inference

## Environment Variables

See `.env.example` for the full list. Critical variables:

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API access for Communication and Estimation agents |
| `OLLAMA_HOST` | Ollama server URL (default: `http://localhost:11434`) |
| `QDRANT_URL` | Qdrant vector DB URL (default: `http://localhost:6333`) |
| `POSTGRES_*` | PostgreSQL connection details |
| `JOBTREAD_API_KEY` | JobTread API access |
| `MORAWARE_API_KEY` | Moraware API access |
| `QB_CLIENT_ID` / `QB_CLIENT_SECRET` | QuickBooks OAuth credentials |

## VRAM Budget (16GB RTX 5070 Ti)

| Model | VRAM | Use |
|-------|------|-----|
| `nomic-embed-text` | 0.5 GB | Always loaded — embeddings |
| `qwen3:8b` | 5.2 GB | Scope/Communication (fast) |
| `qwen2.5vl:7b` | ~6 GB | Image Analysis |
| `qwen3:14b` | 9.3 GB | Estimation/Reasoning |
| `deepseek-r1:14b` | ~9 GB | Math specialist (alternative) |

Only one inference model loads at a time alongside the embedding model. Ollama auto-manages swapping with `OLLAMA_KEEP_ALIVE=5m`.

## Key Business Context

- **Company**: Nelson Tile & Stone, Bend, Oregon
- **Specialties**: Tile installation, countertop fabrication (natural stone, quartz), kitchen/bath remodeling
- **Region**: Bend, OR — no Oregon sales tax, +5-15% labor premium over Portland, seasonal constraints
- **Business systems**: JobTread (project management), Moraware (fabrication scheduling), QuickBooks Online (accounting)
- **Slab optimization**: Countertop fabrication uses 2D bin-packing for optimal slab utilization (integrates with Moraware/CounterGo)
