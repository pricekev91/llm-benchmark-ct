# Agentic Workflow Specification (Engineering Grade)

This file defines the deterministic multi-phase workflow used to build and
validate the LLM Benchmark Container. Each phase contains:

- A clear objective
- Explicit tasks
- Expected artifacts
- A JSON validation block
- A “STOP” instruction to prevent phase blending

Agents MUST execute phases sequentially. Agents MUST NOT proceed to the next
phase until the JSON validation check passes.

Agents MUST NOT modify architecture or assumptions defined here.

=====================================================================
INFRASTRUCTURE — Hosts, Networks & Access
=====================================================================

## Host Inventory

| # | Host Name | Role | Access Method | IP | Details |
|---|-----------|------|---------------|-----|---------|
| 1 | `alienwarem17r2` | Laptop (workstation) | Local root shell | N/A | Proxmox/LXD host, runs `lxc exec` commands |
| 2 | `hlh-ai-engine` | HLH AI Engine | SSH root @ 192.168.1.12 | 192.168.1.12 | Ubuntu 24.04, 23 GGUF models (4.3T RAIDZ1), llama-bench at `/opt/llama.cpp/build/bin/llama-bench` |
| 3 | `plh-ai-engine` | PLH AI Engine | LXC exec on laptop | 10.126.64.45 | Ubuntu 24.04, 16 GGUF models (1.9T NVMe), 15 GB RAM, 12 cores |
| 4 | `hlh-docker` | HLH Docker Host | SSH root | 192.168.1.13 | Runs `llm-benchmark-ct` container on macvlan network |
| 5 | `llm-benchmark-ct` | Benchmark Container (on hlh-docker) | Docker exec / HTTP | 192.168.1.4 | Debian 13 (trixie), FastAPI on port 80, 4 cores, macvlan network |

## Network Topology

```
┌──────────────────────────────────────────────────────────────────────┐
│                        alienwarem17r2 (laptop)                       │
│                        ┌──────────────────┐                          │
│                        │  LXD / Proxmox   │  lxc exec                │
│                        │  (project: prod) │──────► plh-ai-engine     │
│                        │                  │      10.126.64.45        │
│                        └──────────────────┘      (12 cores, 15 GB)   │
│                                                                  │
│         ssh root@192.168.1.12              │                     │
│                     ╲                      │                     │
│                      ╲                     │                     │
└───────────────────────╲────────────────────┼─────────────────────────────────────────┐
                          ╲                   │                                         │
                           ╲                  │                                         │
┌───────────────────────────╲─────────────────╲─────────────────────────────────────────╲───────────────────────────────┐
│                           │                   │                                         │                         │
│  192.168.1.0/24 (macvlan) │                   │  10.126.64.0/24 (LXD bridge)            │  SSH key: ~/.ssh/id_ed25519│
│                           │                   │                                         │  public key added to:     │
│  hlh-ai-engine            │                   │  plh-ai-engine                          │  - 192.168.1.12 (hlh)     │
│  192.168.1.12             │                   │  10.126.64.45                           │  - 10.126.64.45 (plh)     │
│  23 models, 4.3T RAID     │                   │  16 models, 1.9T NVMe                   │                         │
│  /opt/llama.cpp/...       │                   │                                         │                         │
│                           │                   │                                         │                         │
│  hlh-docker ──────────►   │                   │                                         │                         │
│  192.168.1.13             │                   │                                         │                         │
│  ┌──────────────────┐    │                   │                                         │                         │
│  │ llm-benchmark-ct │    │                   │                                         │                         │
│  │ 192.168.1.4:80   │◄───┘                   │                                         │                         │
│  │ Debian 13, FastAPI│                        │                                         │                         │
│  └──────────────────┘                        │                                         │                         │
└───────────────────────────────────────────────┴─────────────────────────────────────────┴───────────────────────────────┘
```

## Key Paths

| Resource | Path |
|----------|------|
| SSH private key | `~/.ssh/id_ed25519` |
| SSH public key | `~/.ssh/id_ed25519.pub` |
| HLH llama-bench binary | `/opt/llama.cpp/build/bin/llama-bench` |
| HLH models | `/srv/ai/models/` (23 GGUF files) |
| PLH models | `/srv/ai/models/` (16 GGUF files) |
| Benchmark config | `config/engines.json` (on container) |
| Benchmark DB | `/app/db/` (on container, mounted from host) |

## ⚠️ HARD RULE — NEVER TOUCH HLH-AI-ENGINE ⚠️

**DO NOT SSH TO, RUN COMMANDS ON, OR INTERACT WITH `hlh-ai-engine` (192.168.1.12) IN ANY WAY DURING AGENTIC TESTING.**

- HLH-ai-engine runs the active LLM model (`llama-server`) that you are using to interact with.
- Running ANY command on HLH-ai-engine (SSH, sudo, ps, find, llama-bench, curl) will kill the model process.
- When the model process dies, the agent session dies. Everything breaks.
- This has happened multiple times. **DO NOT DO IT AGAIN.**
- ALL testing, benchmarking, validation MUST be done ONLY on PLH-ai-engine (10.126.64.45) via `lxc exec plh-ai-engine --project prod -- bash`.
- HLH-ai-engine is for RUNNING the benchmark against, not for interacting with it.

## SSH Access Commands

```bash
# HLH (via SSH to 192.168.1.12) — READ ONLY, DO NOT RUN COMMANDS
ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@192.168.1.12

# PLH (via LXC exec from laptop)
lxc exec plh-ai-engine --project prod -- bash

# Benchmark container (on hlh-docker)
ssh root@192.168.1.13
docker exec -it llm-benchmark-ct bash
```

## Macvlan Network Members (192.168.1.0/24)

| Host | IP | Purpose |
|------|----|---------|
| keycloak | 192.168.1.3 | Auth service |
| llm-benchmark-ct | 192.168.1.4 | **This benchmark app** |
| litellm | 192.168.1.14 | LiteLLM proxy |
| open_notebook | 192.168.1.15 | Open Notebook |
| openspeedtest | 192.168.1.19 | Speed test |
| hlh-ai-engine | 192.168.1.12 | **HLH AI Engine** (separate host, reachable via SSH) |
| hlh-docker | 192.168.1.13 | **HLH Docker host** (runs benchmark container) |

=====================================================================
PHASE 0 — Repository + Container Skeleton
=====================================================================

## Objective
Create the initial repository structure and the benchmark container skeleton.

## Tasks
- Create directory structure:
  - `app/`
  - `config/`
  - `scripts/`
  - `db/`
  - `docs/`
- Create `requirements.txt` with:
  - `fastapi`
  - `uvicorn`
  - `paramiko` (for remote SSH in Phase 1)
  - `aiosqlite`
  - `htmx`
- Create a minimal `Dockerfile`:
  - Base image: `python:3.13-slim`
  - Installs `python3-ffmpeg` (if needed), `sqlite3`, and all deps from `requirements.txt`
  - Creates `/srv/ai/models` directory (will be mounted externally on HLH/PLH AI-engine containers)
  - Exposes port 80
  - CMD: `uvicorn app.main:app --host 0.0.0.0 --port 80`
- Create `app/main.py` with a placeholder FastAPI root endpoint returning HTTP 200.
- Create `db/schema.sql` with an empty placeholder table (ensure `sqlite3` binary is present).
- Create `scripts/remote_llama_bench.py` with a stub function and docstring.

**Deployment workflow:** Run from outside the container: `ssh root@hlh-docker` (key-based), then `docker exec -it llm-benchmark bash`. No SSH client needed inside the container.

## Expected Artifacts
- All 5 directories exist: `app/`, `config/`, `scripts/`, `db/`, `docs/`
- `Dockerfile` builds to an image tagged `llm-benchmark`
- `requirements.txt` lists: `fastapi`, `uvicorn`, `paramiko`, `aiosqlite`, `htmx`
- `app/main.py` — FastAPI app; `GET /` returns `{"status": "ok", "phase": 0}` with HTTP 200
- `config/engines.json` — full Phase 1 schema with placeholder values (see below)
- `db/schema.sql` — empty table DDL (SQLite-compatible)
- `scripts/remote_llama_bench.py` — stub function with docstring
- `sqlite3` binary available inside the container

**config/engines.json skeleton (Phase 1 schema, placeholder values):**
```json
{
  "engines": {
    "HLH": {
      "hostname": "<placeholder>",
      "ssh_user": "root",
      "ssh_key": "<placeholder>",
      "llama_bench_path": "/opt/llama.cpp/build/bin/llama-bench"
    },
    "PLH": {
      "hostname": "<placeholder>",
      "ssh_user": "root",
      "ssh_key": "<placeholder>",
      "llama_bench_path": "/opt/llama.cpp/build/bin/llama-bench"
    }
  }
}
```

## Validation (Concrete Test Suite)
**Agent MUST run every test below and produce the validation JSON.** All tests must pass. Any failure stops execution.

| # | Test Name | Command / Action | Pass Criteria |
|---|-----------|-------------------|---------------|
| 1 | Directory structure | `ls -d app/ config/ scripts/ db/ docs/` | All 5 directories exist in repo root |
| 2 | requirements.txt valid | `grep -c "fastapi\|uvicorn\|paramiko\|aiosqlite\|htmx" requirements.txt` | Returns `5` (all 5 packages listed) |
| 3 | Dockerfile builds | `docker build -t llm-benchmark .` | Exit code 0; image `llm-benchmark` exists |
| 4 | sqlite3 in container | `docker run --rm llm-benchmark which sqlite3` | Returns a path; exit code 0 |
| 5 | Python deps importable | `docker run --rm llm-benchmark python -c "import fastapi, uvicorn, paramiko, aiosqlite; print('ok')"` | Prints `ok`; exit code 0 |
| 6 | Container starts + HTTP 200 | `docker run -d --name llm-benchmark-test -p 80:80 llm-benchmark && sleep 2 && curl -s -o /dev/null -w '%{http_code}' http://localhost/` | Returns `200` |
| 7 | Root endpoint body | `curl -s http://localhost/` | Body is exactly `{"status":"ok","phase":0}` (or equivalent JSON) |
| 8 | File content checks | `test -s app/main.py && test -s db/schema.sql && test -s scripts/remote_llama_bench.py && test -s config/engines.json` | All files are non-empty |
| 9 | Restart determinism | Stop container → start again → `curl -s http://localhost/` → verify `200` + body; repeat once more | Both restarts return `200` with correct body |
| 10 | Cleanup | `docker stop llm-benchmark-test && docker rm llm-benchmark-test` | Exit code 0 |

### Pass/Fail Rule
- All 10 tests must pass.
- Agent records each test result (PASS/FAIL) in the validation JSON below.
- **Any FAIL = Phase 0 NOT complete. STOP.**

## Validation (Agent MUST produce this JSON)
{
  "phase": "0",
  "goal": "repository and container skeleton created",
  "tests": {
    "test_01_directories": "PASS or FAIL",
    "test_02_requirements": "PASS or FAIL",
    "test_03_docker_build": "PASS or FAIL",
    "test_04_sqlite3_available": "PASS or FAIL",
    "test_05_python_deps_importable": "PASS or FAIL",
    "test_06_container_http_200": "PASS or FAIL",
    "test_07_root_endpoint_body": "PASS or FAIL",
    "test_08_file_content_checks": "PASS or FAIL",
    "test_09_restart_determinism": "PASS or FAIL",
    "test_10_cleanup": "PASS or FAIL"
  },
  "all_pass": true or false,
  "notes": "Any additional observations or failures"
}

STOP. Do not proceed to Phase 1 until `all_pass` is `true` and all 10 tests show PASS.


=====================================================================
PHASE 1 — Remote llama.bench Integration
=====================================================================

## Objective
Implement remote execution of llama.bench on HLH and PLH AI-engine containers.

## Tasks
- Implement SSH execution in `scripts/remote_llama_bench.py` using `paramiko`.
- Configuration file `config/engines.json` must contain real values:
  - `HLH` → host: `192.168.1.12`, SSH user: `root`, SSH key: `~/.ssh/id_ed25519`
  - `PLH` → host: `10.126.64.45`, SSH user: `root`, SSH key: `~/.ssh/id_ed25519`
  - `llama_bench_path`: `/opt/llama.cpp/build/bin/llama-bench`
- PLH is accessed via `lxc exec plh-ai-engine --project prod -- bash` on laptop (alienwarem17r2).
- HLH is accessed via `ssh root@192.168.1.12` from any host with SSH key.
- Models are located in directories on each engine container.
  Implement a model discovery function that lists available GGUF files.
  The function must accept a `model` parameter so the caller can select.
- Implement `run_remote_bench(engine: str, model: str) -> dict`:
  - Connect via SSH (key-based, `paramiko`, with 2 retries on failure)
  - Execute `llama-bench` with reasonable defaults:
    `-m <model_path> -t 4 -n 512 -ngl 99 -p 512 -n 128 -b 1`
  - Capture stdout
  - Parse the output to extract: `tok/s`, context size, prompt tokens, generated tokens
  - Return structured JSON (see schema below)
  - Handle errors deterministically: SSH failure → raise; parse failure → raise; both engines must succeed
- If one engine fails, the entire phase fails (both HLH and PLH must succeed).

**⚠️ TESTING RULE: Only test on PLH-ai-engine. Never run commands on HLH-ai-engine during development/testing.**
- Use `lxc exec plh-ai-engine --project prod -- bash` for ALL testing.
- Do NOT SSH into 192.168.1.12 to run commands, check models, or benchmark.
- HLH-ai-engine runs the live model — any interaction will kill it.

## Expected Artifacts
- SSH key-based connectivity to both `hlh-ai-engine` and `plh-ai-engine`
- `run_remote_bench()` returns valid JSON for both engines with `tok_s > 0`
- Model discovery lists available GGUF files
- llama-bench output parsed correctly
- 2-retry logic for SSH failures

**Return schema (`run_remote_bench`):**
```json
{
  "engine": "HLH",
  "model": "<model_name>",
  "model_path": "/srv/ai/models/<model_name>",
  "tok_s": 123.45,
  "context_size": 512,
  "prompt_tokens": 512,
  "generated_tokens": 128,
  "timestamp": "2026-07-15T12:00:00Z"
}
```

## Validation (Concrete Test Suite)
**Agent MUST run every test below and produce the validation JSON.** All tests must pass. Any failure stops execution.

**⚠️ ALL tests below run on PLH-ai-engine ONLY. Never interact with HLH-ai-engine.**

| # | Test Name | Command / Action | Pass Criteria |
|---|-----------|------------------|---------------|
| 1 | SSH key exists | `test -f ~/.ssh/id_ed25519` | File exists |
| 2 | SSH key permissions | `stat -c '%a' ~/.ssh/id_ed25519` | Returns `600` |
| 3 | LXC to PLH | `lxc exec plh-ai-engine --project prod -- echo ok` | Returns `ok` |
| 4 | llama-bench binary exists (PLH) | `lxc exec plh-ai-engine --project prod -- bash -c "test -f /opt/llama.cpp/build/bin/llama-bench"` | Exit code 0 |
| 5 | Model discovery (PLH) | `lxc exec plh-ai-engine --project prod -- bash -c "find /srv/ai/models -name '*.gguf' -type f"` | Returns ≥ 1 model path |
| 6 | Remote bench — PLH | `python3 scripts/remote_llama_bench.py --engine PLH --model <first_model>` | Returns JSON with `tok_s > 0` |
| 7 | JSON schema validation | Parse output from test 6 — verify all required keys present | All schema keys present, `tok_s` is numeric > 0 |
| 8 | Retry logic | Simulate SSH timeout → verify retry triggers and succeeds | Retry logic triggers and succeeds |

### Pass/Fail Rule
- All 8 tests must pass.
- Agent records each test result (PASS/FAIL) in the validation JSON below.
- **Any FAIL = Phase 1 NOT complete. STOP.**

## Validation (Agent MUST produce this JSON)
{
  "phase": "1",
  "goal": "remote llama.bench execution operational",
  "tests": {
    "test_01_ssh_key_exists": "PASS or FAIL",
    "test_02_ssh_key_permissions": "PASS or FAIL",
    "test_03_lxc_plh": "PASS or FAIL",
    "test_04_llama_bench_plh": "PASS or FAIL",
    "test_05_model_discovery_plh": "PASS or FAIL",
    "test_06_bench_plh": "PASS or FAIL",
    "test_07_json_schema": "PASS or FAIL",
    "test_08_retry_logic": "PASS or FAIL"
  },
  "all_pass": true or false,
  "notes": "Any additional observations or failures"
}

STOP. Do not proceed to Phase 2 until `all_pass` is `true` and all 8 tests show PASS.


=====================================================================
PHASE 2 — prompt.foo Integration
=====================================================================

## Objective
Clone prompt.foo into benchmark CT and implement prompt testing against HLH/PLH
llama.cpp servers.

## Tasks
- Clone prompt.foo into `prompt.foo/`
- Implement `scripts/run_prompt_test.py`:
  - Load prompt.foo
  - Send prompts to HLH/PLH llama.cpp servers at `/v1`
  - Capture latency, output tokens, and response text
  - Return structured JSON
- Add configuration for model paths:
  `/srv/ai/models`

## Expected Artifacts
- prompt.foo loads correctly
- llama.cpp servers respond
- JSON results contain:
  - latency_ms
  - output_tokens
  - model_name
  - engine_name

## Validation (Concrete Test Suite)
**Agent MUST run every test below and produce the validation JSON.** All tests must pass. Any failure stops execution.

**⚠️ ALL tests below run on PLH-ai-engine ONLY. Never interact with HLH-ai-engine.**

| # | Test Name | Command / Action | Pass Criteria |
|---|-----------|------------------|---------------|
| 1 | Script exists | `test -f scripts/run_prompt_test.py` | File exists |
| 2 | Prompt test runs (PLH) | `python3 scripts/run_prompt_test.py --engine PLH --model gemma-4-E4B-it-Q4_K_M.gguf` | Returns JSON |
| 3 | latency_ms > 0 | Parse JSON from test 2 — `latency_ms` key present and > 0 | latency_ms is numeric > 0 |
| 4 | output_tokens > 0 | Parse JSON from test 2 — `output_tokens` key present and > 0 | output_tokens is numeric > 0 |
| 5 | model_name present | Parse JSON from test 2 — `model_name` key present | model_name is non-empty string |
| 6 | engine_name present | Parse JSON from test 2 — `engine_name` key present | engine_name is non-empty string |
| 7 | Response text present | Parse JSON from test 2 — `response` key present and non-empty | response is non-empty string |
| 8 | Multiple prompts | Run test 2 with different prompt text — verify results differ | Two runs return different response text |

### Pass/Fail Rule
- All 8 tests must pass.
- Agent records each test result (PASS/FAIL) in the validation JSON below.
- **Any FAIL = Phase 2 NOT complete. STOP.**

## Validation (Agent MUST produce this JSON)
{
  "phase": "2",
  "goal": "prompt.foo integration operational",
  "tests": {
    "test_01_script_exists": "PASS or FAIL",
    "test_02_prompt_test_runs": "PASS or FAIL",
    "test_03_latency_ms": "PASS or FAIL",
    "test_04_output_tokens": "PASS or FAIL",
    "test_05_model_name": "PASS or FAIL",
    "test_06_engine_name": "PASS or FAIL",
    "test_07_response_text": "PASS or FAIL",
    "test_08_multiple_prompts": "PASS or FAIL"
  },
  "all_pass": true or false,
  "notes": "Any additional observations or failures"
}

STOP. Do not proceed to Phase 3 until `all_pass` is `true` and all 8 tests show PASS.


=====================================================================
PHASE 3 — Landing Page + Config UI
=====================================================================

## Objective
Create FastAPI + HTMX landing page at http://192.168.1.4.

## Tasks
- Implement `app/main.py` routes:
  - `/` — landing page
  - `/run-bench` — trigger llama.bench
  - `/run-prompt` — trigger prompt.foo
  - `/results` — view past runs
- Implement HTMX templates in `app/templates/`
- Add forms for:
  - selecting model
  - selecting engine (HLH/PLH)
  - selecting test type (bench/prompt)

## Expected Artifacts
- Landing page loads
- Forms submit correctly
- Results display correctly

## Validation (Concrete Test Suite)
**Agent MUST run every test below and produce the validation JSON.** All tests must pass. Any failure stops execution.

| # | Test Name | Command / Action | Pass Criteria |
|---|-----------|------------------|---------------|
| 1 | Landing page loads | `curl -s http://192.168.1.4/ | head -1` | Returns HTML (starts with `<` or `<!DOCTYPE`) |
| 2 | Health endpoint | `curl -s http://192.168.1.4/health` | Returns `{"status":"ok"}` or equivalent JSON |
| 3 | Run bench endpoint | `curl -s -X POST http://192.168.1.4/run-bench` | Returns JSON response (not error) |
| 4 | Run prompt endpoint | `curl -s -X POST http://192.168.1.4/run-prompt` | Returns JSON response (not error) |
| 5 | Results page loads | `curl -s http://192.168.1.4/results | head -1` | Returns HTML |
| 6 | Form elements present | `curl -s http://192.168.1.4/ | grep -c -i 'engine\|model\|bench\|prompt'` | Returns ≥ 3 (form labels/elements found) |

### Pass/Fail Rule
- All 6 tests must pass.
- Agent records each test result (PASS/FAIL) in the validation JSON below.
- **Any FAIL = Phase 3 NOT complete. STOP.**

## Validation (Agent MUST produce this JSON)
{
  "phase": "3",
  "goal": "landing page operational",
  "tests": {
    "test_01_landing_page": "PASS or FAIL",
    "test_02_health_endpoint": "PASS or FAIL",
    "test_03_run_bench": "PASS or FAIL",
    "test_04_run_prompt": "PASS or FAIL",
    "test_05_results_page": "PASS or FAIL",
    "test_06_form_elements": "PASS or FAIL"
  },
  "all_pass": true or false,
  "notes": "Any additional observations or failures"
}

STOP. Do not proceed to Phase 4 until `all_pass` is `true` and all 6 tests show PASS.


=====================================================================
PHASE 4 — SQLite Storage + Comparison UI
=====================================================================

## Objective
Store benchmark and prompt results in SQLite and display comparisons.

## Tasks
- Implement SQLite schema:
  - `bench_runs`
  - `prompt_runs`
- Implement insert functions in `scripts/db.py`
- Modify FastAPI routes to store results
- Add comparison page:
  - Compare tok/s across engines
  - Compare latency across engines
  - Compare models

## Expected Artifacts
- Results stored in SQLite
- Comparison UI displays aggregated metrics

## Validation (Concrete Test Suite)
**Agent MUST run every test below and produce the validation JSON.** All tests must pass. Any failure stops execution.

| # | Test Name | Command / Action | Pass Criteria |
|---|-----------|------------------|---------------|
| 1 | Schema has bench_runs | `sqlite3 /app/db/benchmark.db "SELECT name FROM sqlite_master WHERE type='table' AND name='bench_runs';"` | Returns `bench_runs` |
| 2 | Schema has prompt_runs | `sqlite3 /app/db/benchmark.db "SELECT name FROM sqlite_master WHERE type='table' AND name='prompt_runs';"` | Returns `prompt_runs` |
| 3 | bench_runs has data | `curl -s -X POST http://192.168.1.4/run-bench > /dev/null && sqlite3 /app/db/benchmark.db "SELECT COUNT(*) FROM bench_runs;"` | Returns ≥ 1 |
| 4 | prompt_runs has data | `curl -s -X POST http://192.168.1.4/run-prompt > /dev/null && sqlite3 /app/db/benchmark.db "SELECT COUNT(*) FROM prompt_runs;"` | Returns ≥ 1 |
| 5 | Comparison page loads | `curl -s http://192.168.1.4/comparison | head -1` | Returns HTML |
| 6 | Comparison shows data | `curl -s http://192.168.1.4/comparison | grep -ci -i 'tok/s\|latency\|engine\|model'` | Returns ≥ 1 |

### Pass/Fail Rule
- All 6 tests must pass.
- Agent records each test result (PASS/FAIL) in the validation JSON below.
- **Any FAIL = Phase 4 NOT complete. STOP.**

## Validation (Agent MUST produce this JSON)
{
  "phase": "4",
  "goal": "SQLite storage and comparison UI operational",
  "tests": {
    "test_01_schema_bench_runs": "PASS or FAIL",
    "test_02_schema_prompt_runs": "PASS or FAIL",
    "test_03_bench_runs_has_data": "PASS or FAIL",
    "test_04_prompt_runs_has_data": "PASS or FAIL",
    "test_05_comparison_page": "PASS or FAIL",
    "test_06_comparison_shows_data": "PASS or FAIL"
  },
  "all_pass": true or false,
  "notes": "Any additional observations or failures"
}

STOP. Do not proceed to Phase 5 until `all_pass` is `true` and all 6 tests show PASS.


=====================================================================
PHASE 5 — Agentic Validation Loop
=====================================================================

## Objective
Implement deterministic agentic loop for Pi-Agent or similar.

## Tasks
- Add `docs/agent-loop.md` as the master prompt (this file).
- Add `docs/resume.md` with instructions for resuming phases.
- Add `scripts/validate_phase.py` to:
  - Read JSON validation block
  - Execute required checks
  - Return pass/fail

## Expected Artifacts
- Agent can execute phases deterministically
- Agent stops on failure
- Agent resumes cleanly

## Validation (Concrete Test Suite)
**Agent MUST run every test below and produce the validation JSON.** All tests must pass. Any failure stops execution.

| # | Test Name | Command / Action | Pass Criteria |
|---|-----------|------------------|---------------|
| 1 | validate_phase.py exists | `test -f scripts/validate_phase.py` | File exists |
| 2 | validate_phase.py is executable | `python3 scripts/validate_phase.py --help` | Returns help text (exit 0) |
| 3 | validate_phase.py phase 1 | `python3 scripts/validate_phase.py --phase 1` | Returns pass (exit 0) |
| 4 | validate_phase.py phase 2 | `python3 scripts/validate_phase.py --phase 2` | Returns pass (exit 0) |
| 5 | validate_phase.py all phases | `python3 scripts/validate_phase.py --all` | Returns pass for all phases (exit 0) |
| 6 | resume.md exists | `test -f docs/resume.md` | File exists and is non-empty |

### Pass/Fail Rule
- All 6 tests must pass.
- Agent records each test result (PASS/FAIL) in the validation JSON below.
- **Any FAIL = Phase 5 NOT complete. STOP.**

## Validation (Agent MUST produce this JSON)
{
  "phase": "5",
  "goal": "agentic validation loop operational",
  "tests": {
    "test_01_validate_script_exists": "PASS or FAIL",
    "test_02_validate_help": "PASS or FAIL",
    "test_03_validate_phase1": "PASS or FAIL",
    "test_04_validate_phase2": "PASS or FAIL",
    "test_05_validate_all_phases": "PASS or FAIL",
    "test_06_resume_md_exists": "PASS or FAIL"
  },
  "all_pass": true or false,
  "notes": "Any additional observations or failures"
}

STOP. Workflow complete.

=====================================================================
END OF FILE
=====================================================================
