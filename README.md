# AI-Worker

Open-source multi-agent AI estimation system for remodeling and construction.

## What It Does

AI-Worker uses four specialized AI agents to automate the remodeling estimation pipeline — from analyzing project photos through calculating costs to generating professional client proposals.

| Agent | Model | Purpose |
|-------|-------|---------|
| **Image Analysis** | Qwen2.5-VL 7B (local) | Analyze construction photos: detect materials, fixtures, dimensions |
| **Scope** | Qwen3 8B (local) | Extract structured scope from descriptions, emails, transcriptions |
| **Estimation** | Qwen3 14B (local) + Claude | Assembly-based cost calculation with RAG and ML refinement |
| **Communication** | Claude API | Generate proposals, emails, and change orders |

## Architecture

- **Orchestration**: CrewAI (Crews + Flows)
- **Local LLM**: Ollama with Qwen models on RTX 5070 Ti (16GB VRAM)
- **RAG**: LlamaIndex + Qdrant + Docling + nomic-embed-text
- **Cost Engine**: Assembly-based calculations + XGBoost/LightGBM refinement
- **Integrations**: JobTread, Moraware, QuickBooks via MCP servers
- **Workflows**: n8n for business process automation
- **Infrastructure**: Docker Compose on Proxmox LXC with GPU passthrough

## Quick Start

```bash
# Clone and set up
git clone https://github.com/spaceghost1307/AI-worker.git
cd AI-worker
cp .env.example .env
# Edit .env with your API keys

# Install Python dependencies
pip install -e ".[dev]"

# Start infrastructure
docker compose up -d

# Pull required models
ollama pull qwen3:14b
ollama pull qwen2.5vl:7b
ollama pull qwen3:8b
ollama pull nomic-embed-text

# Run tests
pytest tests/
```

## Project Structure

```
src/
├── agents/          # CrewAI agent definitions and crew orchestration
├── config/          # Settings (env-based) and agent YAML configs
├── cost_engine/     # Assembly calculations, regional adjustments, ML refinement
├── rag/             # Document ingestion, embeddings, Qdrant retrieval
├── vision/          # Three-stage photo analysis pipeline
├── mcp_servers/     # JobTread, Moraware, QuickBooks MCP integrations
└── utils/           # Ollama client and shared utilities
```

See [CLAUDE.md](CLAUDE.md) for detailed development guide and conventions.
See [docs/architecture.md](docs/architecture.md) for full system architecture.

## License

MIT
