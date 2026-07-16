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
- Implement SSH execution in `scripts/remote_llama_bench.py`.
- Hardcode remote paths:
  `/opt/llama.cpp/build/bin/llama-bench`
- Add configuration file:
  `config/engines.json`
  containing:
  - HLH hostname/IP
  - PLH hostname/IP
  - SSH user
  - SSH key path
- Implement function to:
  - Execute llama.bench remotely
  - Capture stdout
  - Parse tok/s
  - Return structured JSON

## Expected Artifacts
- Remote execution works for both HLH and PLH
- tok/s parsed correctly
- Errors handled deterministically

## Validation
{
  "phase": "1",
  "goal": "remote llama.bench execution operational",
  "check": "running remote_llama_bench.py returns JSON with tok_s > 0 for both HLH and PLH"
}

STOP. Do not proceed to Phase 2 until validation passes.


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

## Validation
{
  "phase": "2",
  "goal": "prompt.foo integration operational",
  "check": "run_prompt_test.py returns JSON with latency_ms > 0 and output_tokens > 0"
}

STOP. Do not proceed to Phase 3 until validation passes.


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

## Validation
{
  "phase": "3",
  "goal": "landing page operational",
  "check": "GET / returns HTML; POST /run-bench triggers remote execution; POST /run-prompt triggers prompt.foo"
}

STOP. Do not proceed to Phase 4 until validation passes.


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

## Validation
{
  "phase": "4",
  "goal": "SQLite storage and comparison UI operational",
  "check": "bench_runs and prompt_runs contain rows; comparison page loads aggregated metrics"
}

STOP. Do not proceed to Phase 5 until validation passes.


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

## Validation
{
  "phase": "5",
  "goal": "agentic validation loop operational",
  "check": "validate_phase.py returns pass for all phases when executed sequentially"
}

STOP. Workflow complete.

=====================================================================
END OF FILE
=====================================================================
