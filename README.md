# LLM Benchmark CT

Containerized LLM benchmarking tool for comparing performance across multiple endpoints and models.

## Overview

Configure external LLM endpoints (OpenAI, llama.cpp, vLLM, LiteLLM, llama-swap), select models, run benchmark prompts, and capture detailed metrics — all through a web dashboard served from a single container at a dedicated LAN IP.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Container: 192.168.1.4              │
│                                                     │
│  ┌──────────┐    ┌──────────────────┐               │
│  │ Frontend │    │   FastAPI API    │               │
│  │  (SPA)   │◄──►│   (Port 80)      │               │
│  └──────────┘    └──┬───────────┬───┘               │
│                     │           │                    │
│              ┌──────▼────┐  ┌───▼────────┐          │
│              │  SQLite   │  │  Adapters  │          │
│              │  (DB)     │  │  (HTTP)    │          │
│              └───────────┘  └─────┬──────┘          │
│                                   │                  │
└───────────────────────────────────┼──────────────────┘
                                    │
                          ┌─────────▼──────────┐
                          │  External LLM APIs  │
                          │  OpenAI / llama.cpp │
                          │  vLLM / LiteLLM     │
                          └─────────────────────┘
```

## Benchmark Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  1. User     │     │  2. Backend  │     │  3. LLM API  │
│  Selects     │────►│  Resolves    │────►│  Receives    │
│  Endpoint +  │     │  Endpoint    │     │  Prompt via  │
│  Model       │     │  Config      │     │  Adapter     │
└──────────────┘     └──────────────┘     └──────────────┘
                           │                      │
                           │              ┌────────▼──────┐
                           │              │  Returns     │
                           │              │  Response +   │
                           │              │  Raw Metrics  │
                           │              └────────┬──────┘
                           │                       │
                           │     ┌─────────────────▼──────┐
                           │     │  4. Capture Metrics    │
                           │     │  - Latency (ms)        │
                           │     │  - Tokens Generated    │
                           │     │  - Output Length       │
                           │     │  - Throughput (t/s)    │
                           │     └────────┬───────────────┘
                           │              │
                           │     ┌────────▼───────────────┐
                           │     │  5. Store in SQLite    │
                           │     │  - Run ID              │
                           │     │  - Timestamp           │
                           │     │  - All metrics         │
                           │     └────────┬───────────────┘
                           │              │
                           │     ┌────────▼───────────────┐
                           │     │  6. Return to Frontend │
                           │     │  - Display results     │
                           │     │  - Show metric cards   │
                           │     └────────────────────────┘
```

## Supported Providers

| Provider | Adapter | Protocol |
|----------|---------|----------|
| OpenAI | `OpenAIAdapter` | OpenAI API |
| llama.cpp | `LlamaCppAdapter` | v1/chat/completions |
| vLLM | `VLLMAdapter` | OpenAI-compatible |
| LiteLLM | `LiteLLMAdapter` | OpenAI-compatible |
| llama-swap | `LlamaSwapAdapter` | OpenAI-compatible |

## Future: Agentic Harness Plan

The endpoint abstraction is designed to support agentic stacks in the future:

```
EndpointConfig → AgentStackConfig
├── base_url         → orchestration_endpoint
├── provider         → agent_framework (Pi, Hermes, LangGraph)
├── api_key          → tool_registry_token
├── model_name       → agent_system_prompt_id
└── metadata         → agent_capabilities, tool_list, memory_config
```

Key design principles:

1. **Agents as endpoints** — An agent stack exposes the same OpenAI-compatible interface as a model server
2. **Metadata extension** — `EndpointConfig` supports arbitrary JSON metadata for agent-specific config
3. **Benchmark parity** — Agents are benchmarked the same way as models: latency, token usage, output quality
4. **No breaking changes** — The current adapter pattern extends naturally to agentic workflows

No implementation yet. This is architecture-only planning.

## Development

```bash
# Local (requires Python 3.11)
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
```

## Deployment

```bash
# Remote (hlh-docker)
cd /root/git/llm-benchmark-ct
git pull origin master
bash deploy-llm-benchmark-ct.sh
```
