# Phases Completed

## Phase 0 — Repository + Container Skeleton ✅ PASS
- All 10/10 tests passed
- Docker container builds and runs on hlh-docker (192.168.1.4)
- FastAPI root endpoint returning HTTP 200

## Phase 1 — Remote llama-bench Integration ✅ PASS
- All 8/8 tests passed (PLH only — HLH not tested per HARD RULE)
- SSH key-based connectivity to PLH via lxc exec
- Model discovery finds 16+ GGUF models
- llama-bench binary + llama-server API fallback working
- `run_remote_bench()` returns structured JSON with tok_s > 0

## Phase 2 — promptfoo Integration ✅ PASS
- All 8/8 tests passed (PLH only — HLH not tested per HARD RULE)
- `scripts/run_prompt_test.py` operational with OpenAI SDK
- Supports single/multiple prompts, repeat testing, prompt files
- Content fallback to reasoning_content (Gemma-4 reasoning models)
- Structured JSON output with latency, tokens, response, summary stats

## Phase 3 — Landing Page + Config UI ✅ PASS
- All 6/6 tests passed
- FastAPI + Jinja2/HTMX landing page at http://192.168.1.4/
- Routes: `/` (landing), `/health`, `/run-bench`, `/run-prompt`, `/results`, `/comparison`
- SQLite storage with `bench_runs` and `prompt_runs` tables
- Model discovery via llama-server `/v1/models` API
- HLH llama-server API working from container via macvlan
- Dark-themed responsive UI with HTMX partial responses
- Engine/model selection forms for both bench and prompt tests

## Phase 4 — SQLite Storage + Comparison UI ✅ PASS
- All 6/6 tests passed
- SQLite schema: `bench_runs` and `prompt_runs` tables with indexes
- Insert functions store all benchmark and prompt results
- Comparison page at `/comparison` shows:
  - Benchmark tok/s comparison across engines/models
  - Prompt latency comparison across engines/models
  - Detailed bench metrics (avg eval time, prompt time, run count)
- Results page at `/results` shows run history with filters
- All data persisted in `/app/db/benchmark.db`
- Deployed on 192.168.1.4 container (macvlan)
