# LLM Benchmark CT — Quick Reference

## What This Is

A containerized benchmarking tool for comparing LLM endpoints (OpenAI, llama.cpp, vLLM, LiteLLM, llama-swap).

Configure endpoints, select models, run prompts, and track metrics (latency, tokens, throughput) across runs.

## Access

- **Web UI:** http://192.168.1.4/
- **Health check:** http://192.168.1.4/health
- **API docs (with auth):** http://192.168.1.4/docs

## API Authentication

All API routes require `X-API-KEY` header (except `/health` and `/static/*`).

```bash
# Health check (no auth)
curl http://192.168.1.4/health

# API (with auth)
curl -H "X-API-KEY: YOUR_KEY" http://192.168.1.4/endpoints/list
```

The API key is set via the `API_KEY` environment variable in docker-compose.yml.

## Key API Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (no auth) |
| GET | `/endpoints/list` | List configured endpoints |
| POST | `/endpoints/save` | Add/update an endpoint |
| DELETE | `/endpoints/{id}` | Delete an endpoint |
| GET | `/endpoints/models/list` | List available models |
| GET | `/presets/list` | List prompt presets |
| POST | `/presets/save` | Save a prompt preset |
| POST | `/benchmark/run` | Run a benchmark |
| GET | `/analytics/history/filter` | Query benchmark history |
| GET | `/analytics/run/{run_id}` | Get a single run |
| GET | `/analytics/compare/run` | Comparison stats for a model |
| GET | `/analytics/compare/trends` | Latency trends over time |

## Volumes

| Mount | Purpose |
|-------|---------|
| `/opt/ct/llm-benchmark/db/` | SQLite database (benchmark history, configs) |
| `/opt/ct/llm-benchmark/configs/` | Endpoint configuration files |

## Deploy

```bash
cd /root/git/llm-benchmark-ct
bash deploy-llm-benchmark-ct.sh
```

## File Structure

```
llm-benchmark-ct/
├── 00_BACKLOG.md          # Future tasks
├── 10_ACTIVE.md           # Current work
├── 90_DONE.md             # Completed milestones
├── 98_README.md           # This file
├── CHANGELOG.md           # Version history
├── README.md              # Full documentation
├── Dockerfile
├── docker-compose.yml
├── deploy-llm-benchmark-ct.sh
├── backend/
│   ├── main.py            # FastAPI app entry
│   ├── auth.py            # API key authentication
│   ├── db.py              # SQLite initialization + CRUD
│   ├── models.py          # Data classes
│   ├── schemas.py         # Pydantic schemas
│   ├── endpoints.py       # API route definitions
│   ├── benchmark.py       # Benchmark execution engine
│   ├── openai_compat.py   # LLM adapter abstractions
│   └── requirements.txt
├── frontend/
│   └── dist/              # Built SPA (HTML/CSS/JS)
│       ├── index.html
│       └── app.js
└── volumes/
    ├── db/                # SQLite data
    └── configs/           # Endpoint configs
```
