# LLM Benchmark Container (llama.bench + prompt.foo)

This repository contains the benchmark container (“llama-benchmark.ct”) used to
run deterministic, empirical performance tests across multiple AI-engine
containers (HLH and PLH). It integrates:

- llama.bench (remote execution on HLH/PLH)
- prompt.foo (local clone inside benchmark CT)
- FastAPI + HTMX landing page at http://192.168.1.4
- SQLite-backed run history + comparison UI
- Multi-phase agentic workflow driven by Pi-Agent or similar deterministic agent

The benchmark container does **not** host models. Models live on:

- `/srv/ai/models` on HLH-AI-Engine
- `/srv/ai/models` on PLH-AI-Engine

The benchmark CT mounts these directories read-only.

## Architecture Summary

- **llama.bench**  
  Executed remotely via SSH on HLH and PLH at:
  `/opt/llama.cpp/build/bin/llama-bench`

- **prompt.foo**  
  Cloned into benchmark CT. Python scripts orchestrate prompt tests against
  llama.cpp servers running on HLH/PLH at `/v1`.

- **Landing Page**  
  FastAPI + HTMX UI served from benchmark CT at:
  `http://192.168.1.4`

- **Data Store**  
  SQLite database inside benchmark CT, backed by a persistent volume.

## Agentic Workflow

Development and execution follow a deterministic multi-phase workflow defined in:

