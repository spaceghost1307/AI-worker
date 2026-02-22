# Architecture: Multi-Agent AI Estimator for Remodeling

## Overview

A self-hosted, four-agent system running on Proxmox with local Ollama inference and hybrid Claude API access for generating remodeling project estimates at Nelson Tile & Stone.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Proxmox LXC Container                      │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  Scope   │  │  Image   │  │Estimation│  │  Comms   │      │
│  │  Agent   │  │ Analysis │  │  Agent   │  │  Agent   │      │
│  │(qwen3:8b)│  │(qwen2.5vl│  │(qwen3:14b│  │(Claude  │      │
│  │          │  │  :7b)    │  │+ Claude) │  │  API)   │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │              │              │              │            │
│  ┌────┴──────────────┴──────────────┴──────────────┴─────┐     │
│  │                    CrewAI Orchestration                │     │
│  │              (Crews + Flows via LiteLLM)              │     │
│  └──────────┬────────────────────────────────┬───────────┘     │
│             │                                │                  │
│  ┌──────────┴──────────┐  ┌──────────────────┴───────────┐    │
│  │     Ollama          │  │         RAG Pipeline          │    │
│  │  (GPU Inference)    │  │  Docling → LlamaIndex → Qdrant│    │
│  │  RTX 5070 Ti 16GB   │  │  + nomic-embed-text           │    │
│  └─────────────────────┘  └───────────────────────────────┘    │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │PostgreSQL│ │  Redis   │ │  MinIO   │ │   n8n    │         │
│  │+pgvector │ │          │ │          │ │          │         │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
│                                                                 │
│  ┌──────────────── MCP Servers ─────────────────────┐         │
│  │  JobTread  │  Moraware  │  QuickBooks  │  Google  │         │
│  └──────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## Agent Details

### Image Analysis Agent
- **Model**: `qwen2.5vl:7b` (~6GB VRAM)
- **Pipeline**: Florence-2 detection → Depth Anything V3 measurement → Qwen2.5-VL analysis
- **Output**: Structured JSON with room type, materials, fixtures, dimensions, condition

### Scope Agent
- **Model**: `qwen3:8b` (5.2GB VRAM)
- **Input**: Freeform project descriptions, emails, voice transcriptions
- **Output**: Structured scope items with rooms, materials, quantities, missing info flags

### Estimation Agent
- **Models**: `qwen3:14b` (9.3GB VRAM) + Claude API fallback
- **Engine**: Assembly-based calculations + RAG cost data + ML refinement
- **Output**: Line-item estimate with material/labor/equipment breakdown

### Communication Agent
- **Model**: Claude API (Sonnet)
- **Output**: Professional proposals, emails, change orders with company branding

## Cost Engine Architecture

### Four-Layer System

1. **Assembly Engine**: Rule-based calculations from material + labor + waste components
2. **Regional Adjustments**: Bend, OR specific factors (no sales tax, +10% labor, transport surcharge)
3. **ML Refinement**: XGBoost/LightGBM trained on historical JobTread data with SHAP explainability
4. **NLP Scope Extraction**: Structured scope parsing from freeform text

## VRAM Budget (16GB RTX 5070 Ti)

| Model | VRAM | Role |
|-------|------|------|
| nomic-embed-text | 0.5 GB | Always loaded — embeddings |
| qwen3:8b | 5.2 GB | Scope/Communication (fast) |
| qwen2.5vl:7b | ~6 GB | Image Analysis |
| qwen3:14b | 9.3 GB | Estimation/Reasoning |

One inference model loaded at a time + embedding model. Ollama manages swapping.

## Infrastructure

- **Host**: Proxmox LXC with NVIDIA GPU passthrough (device bind-mounts)
- **Runtime**: Docker Compose with 11 services
- **GPU**: RTX 5070 Ti (16GB GDDR7 VRAM)
- **RAM**: 32GB minimum, 64GB recommended
- **Storage**: 500GB+ NVMe SSD

## Business System Integrations

| System | Integration | Purpose |
|--------|-------------|---------|
| JobTread | Custom MCP (GraphQL API) | Project management, estimate sync |
| Moraware | Custom MCP (REST API) | Fabrication scheduling, slab inventory |
| QuickBooks Online | Official MCP (OAuth) | Accounting, invoicing |
| Google Drive/Sheets | Existing MCP servers | Document storage, spreadsheets |

## Deployment Phases

1. **Foundation**: Proxmox + Docker stack + Ollama models + n8n
2. **RAG Knowledge Base**: Document ingestion + Qdrant + cost database
3. **Core Agents**: Scope → Image Analysis → Estimation → Communication
4. **Business Integration**: MCP servers for JobTread, Moraware, QuickBooks
5. **ML Refinement**: Historical data training, SHAP explainability
6. **Production Hardening**: Monitoring, auth, human-in-the-loop review
