"""
FastAPI application for LLM Benchmark Container.

Routes:
    /              - Landing page (HTMX)
    /health        - Health check (JSON)
    /run-bench     - Trigger benchmark (JSON or HTMX)
    /run-prompt    - Trigger prompt test (JSON or HTMX)
    /results       - View past runs (HTMX)
    /models        - List available models (JSON)
    /comparison    - Comparison dashboard (HTMX)
"""

import json
import os
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates


def _format_time_for_display(timestamp: str) -> str:
    """Format timestamp for display.

    New format: '2026-07-16 07:50:45 PM EDT' → '07-16 07:50:45 PM'
    Old ISO format: '2026-07-16T21:50:17' → '07-16 09:50:17 PM'
    """
    if "T" in str(timestamp):  # old ISO format
        dt = datetime.fromisoformat(str(timestamp))
        return dt.strftime("%m-%d %I:%M:%S %p")
    else:  # already formatted
        ts = str(timestamp)
        # '2026-07-16 07:50:45 PM EDT'
        parts = ts.split(" ")
        date_part = parts[0]  # '2026-07-16'
        date_formatted = date_part[5:]  # '07-16'
        time_part = parts[1]  # '07:50:45'
        ampm = parts[2]  # 'PM'
        return f"{date_formatted} {time_part} {ampm}"


def format_time_filter(timestamp: str) -> str:
    """Jinja2 filter for formatted display timestamps."""
    return _format_time_for_display(timestamp)

from app import db as db_module
from app.models import (
    SERVER_URLS,
    CTX_SIZES,
    MTP_OPTIONS,
    discover_models,
    discover_models_ssh,
    get_model_path,
    run_bench_via_api,
    run_prompt_via_api,
)

# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------

# Determine template directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(SCRIPT_DIR, "templates")

templates = Jinja2Templates(directory=TEMPLATE_DIR)
templates.env.filters["format_time"] = format_time_filter

# Runtime state
_server_url_override: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB on startup."""
    db_module.init_db()
    yield


app = FastAPI(
    title="LLM Benchmark Container",
    description="Benchmark and test LLMs on HLH/PLH AI Engines",
    version="0.3.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_server_url(engine: str) -> str:
    """Get the appropriate server URL for an engine."""
    if _server_url_override:
        return _server_url_override
    return SERVER_URLS.get(engine, SERVER_URLS["HLH"])


def _error_response(exc: Exception, engine: str = "", model: str = "") -> dict:
    """Build a consistent error response dict."""
    return {
        "error": True,
        "message": str(exc),
        "traceback": traceback.format_exc(),
        "engine": engine,
        "model": model,
    }


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Landing Page
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    """Landing page with model/engine selection forms."""
    # Discover models: SSH filesystem scan preferred (lists ALL GGUF files)
    models_hlh = discover_models_ssh("HLH")
    if not models_hlh:
        models_hlh = discover_models("HLH")  # fallback to API
    models_plh = discover_models_ssh("PLH")
    if not models_plh:
        models_plh = discover_models("PLH")  # fallback to API

    # Get recent results
    results = db_module.get_all_runs(limit=10)

    return templates.TemplateResponse(
        request, "landing.html",
        context={
            "models_plh": models_plh,
            "models_hlh": models_hlh,
            "bench_runs": results.get("bench_runs", []),
            "prompt_runs": results.get("prompt_runs", []),
            "ctx_sizes": CTX_SIZES,
            "mtp_options": MTP_OPTIONS,
        },
    )


# ---------------------------------------------------------------------------
# Results Page
# ---------------------------------------------------------------------------

@app.get("/results", response_class=HTMLResponse)
async def results_page(request: Request):
    """Results page showing past benchmark and prompt runs."""
    engine = request.query_params.get("engine")
    test_type = request.query_params.get("type", "all")

    if test_type == "bench":
        runs = db_module.get_bench_runs(limit=50, engine=engine)
    elif test_type == "prompt":
        runs = db_module.get_prompt_runs(limit=50, engine=engine)
    else:
        all_data = db_module.get_all_runs(limit=50)
        runs = all_data.get("bench_runs", []) + all_data.get("prompt_runs", [])

    return templates.TemplateResponse(
        request, "results.html",
        context={"runs": runs, "current_engine": engine, "current_type": test_type},
    )


# ---------------------------------------------------------------------------
# Comparison Page
# ---------------------------------------------------------------------------

@app.get("/comparison", response_class=HTMLResponse)
async def comparison_page(request: Request):
    """Comparison dashboard."""
    comparison = db_module.get_comparison()
    return templates.TemplateResponse(
        request, "comparison.html",
        context={"comparison": comparison},
    )


# ---------------------------------------------------------------------------
# Models API
# ---------------------------------------------------------------------------

@app.get("/models")
async def models_api(engine: Optional[str] = None):
    """List available models (SSH filesystem scan preferred)."""
    target = engine or "HLH"
    models = discover_models_ssh(target)
    if not models:
        models = discover_models(target)
    return {"models": models}


# ---------------------------------------------------------------------------
# Run Bench (API + HTMX)
# ---------------------------------------------------------------------------

@app.post("/run-bench")
async def run_bench(
    request: Request,
    engine: str = Form(default="HLH"),
    model: str = Form(default=""),
    max_tokens: int = Form(default=128),
    ctx_size: int = Form(default=8192),
    mtp: int = Form(default=0),
):
    """Run benchmark and return JSON result."""
    try:
        # Determine model to benchmark
        if not model:
            models = discover_models_ssh(engine)
            if not models:
                models = discover_models(engine, _get_server_url(engine))
            if not models:
                return JSONResponse(
                    status_code=200,
                    content=_error_response(
                        Exception(f"No models found on {engine}"),
                        engine=engine,
                    ),
                )
            model = models[0]["id"]

        result = run_bench_via_api(
            engine=engine,
            model=model,
            base_url=_get_server_url(engine),
            ctx_size=ctx_size,
            mtp=mtp,
        )

        # Store in DB
        db_module.insert_bench_run(result)

        return JSONResponse(content=result)

    except Exception as e:
        return JSONResponse(
            content=_error_response(e, engine=engine, model=model),
        )


# ---------------------------------------------------------------------------
# Run Prompt (API + HTMX)
# ---------------------------------------------------------------------------

@app.post("/run-prompt")
async def run_prompt(
    request: Request,
    engine: str = Form(default="HLH"),
    model: str = Form(default=""),
    prompt: str = Form(
        default="Write a concise 2-sentence summary of the history of artificial intelligence."
    ),
    max_tokens: int = Form(default=128),
    ctx_size: int = Form(default=8192),
    mtp: int = Form(default=0),
):
    """Run prompt test and return JSON result."""
    try:
        # Determine model
        if not model:
            models = discover_models_ssh(engine)
            if not models:
                models = discover_models(engine, _get_server_url(engine))
            if not models:
                return JSONResponse(
                    status_code=200,
                    content=_error_response(
                        Exception(f"No models found on {engine}"),
                        engine=engine,
                    ),
                )
            model = models[0]["id"]

        result = run_prompt_via_api(
            engine=engine,
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            base_url=_get_server_url(engine),
            ctx_size=ctx_size,
            mtp=mtp,
        )

        # Store in DB
        db_module.insert_prompt_run(result)

        return JSONResponse(content=result)

    except Exception as e:
        return JSONResponse(
            content=_error_response(e, engine=engine, model=model),
        )


# ---------------------------------------------------------------------------
# HTMX Partial: Run Bench Result
# ---------------------------------------------------------------------------

@app.post("/run-bench/htmx")
async def run_bench_hxmx(
    request: Request,
    engine: str = Form(default="HLH"),
    model: str = Form(default=""),
    max_tokens: int = Form(default=128),
    ctx_size: int = Form(default=8192),
    mtp: int = Form(default=0),
):
    """HTMX endpoint for benchmark — returns partial HTML."""
    try:
        if not model:
            models = discover_models_ssh(engine)
            if not models:
                models = discover_models(engine, _get_server_url(engine))
            if not models:
                return templates.TemplateResponse(
                    request, "partials/error.html",
                    context={"error": f"No models found on {engine}"},
                )
            model = models[0]["id"]

        result = run_bench_via_api(
            engine=engine,
            model=model,
            base_url=_get_server_url(engine),
            ctx_size=ctx_size,
            mtp=mtp,
        )
        db_module.insert_bench_run(result)

        return templates.TemplateResponse(
            request, "partials/bench_result.html",
            context={"result": result},
        )

    except Exception as e:
        return templates.TemplateResponse(
            request, "partials/error.html",
            context={"error": str(e)},
        )


# ---------------------------------------------------------------------------
# HTMX Partial: Run Prompt Result
# ---------------------------------------------------------------------------

@app.post("/run-prompt/htmx")
async def run_prompt_htmx(
    request: Request,
    engine: str = Form(default="HLH"),
    model: str = Form(default=""),
    prompt: str = Form(
        default="Write a concise 2-sentence summary of the history of artificial intelligence."
    ),
    max_tokens: int = Form(default=128),
    ctx_size: int = Form(default=8192),
    mtp: int = Form(default=0),
):
    """HTMX endpoint for prompt — returns partial HTML."""
    try:
        if not model:
            models = discover_models_ssh(engine)
            if not models:
                models = discover_models(engine, _get_server_url(engine))
            if not models:
                return templates.TemplateResponse(
                    request, "partials/error.html",
                    context={"error": f"No models found on {engine}"},
                )
            model = models[0]["id"]

        result = run_prompt_via_api(
            engine=engine,
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            base_url=_get_server_url(engine),
            ctx_size=ctx_size,
            mtp=mtp,
        )
        db_module.insert_prompt_run(result)

        return templates.TemplateResponse(
            request, "partials/prompt_result.html",
            context={"result": result},
        )

    except Exception as e:
        return templates.TemplateResponse(
            request, "partials/error.html",
            context={"error": str(e)},
        )
