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
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app import db as db_module
from app.models import (
    SERVER_URLS,
    discover_models,
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
    # Discover models from both engines
    models_plh = discover_models("PLH")
    models_hlh = discover_models("HLH")

    # Get recent results
    results = db_module.get_all_runs(limit=10)

    return templates.TemplateResponse(
        request, "landing.html",
        context={
            "models_plh": models_plh,
            "models_hlh": models_hlh,
            "bench_runs": results.get("bench_runs", []),
            "prompt_runs": results.get("prompt_runs", []),
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
    """List available models."""
    if engine:
        models = discover_models(engine)
    else:
        models = discover_models("HLH")
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
):
    """Run benchmark and return JSON result."""
    try:
        # Determine model to benchmark
        if not model:
            models = discover_models(engine, _get_server_url(engine))
            if not models:
                return JSONResponse(
                    status_code=200,
                    content=_error_response(
                        Exception(f"No models found on {engine}"),
                        engine=engine,
                    ),
                )
            model = models[0]["name"]

        result = run_bench_via_api(
            engine=engine,
            model=model,
            base_url=_get_server_url(engine),
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
):
    """Run prompt test and return JSON result."""
    try:
        # Determine model
        if not model:
            models = discover_models(engine, _get_server_url(engine))
            if not models:
                return JSONResponse(
                    status_code=200,
                    content=_error_response(
                        Exception(f"No models found on {engine}"),
                        engine=engine,
                    ),
                )
            model = models[0]["name"]

        result = run_prompt_via_api(
            engine=engine,
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            base_url=_get_server_url(engine),
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
):
    """HTMX endpoint for benchmark — returns partial HTML."""
    try:
        if not model:
            models = discover_models(engine, _get_server_url(engine))
            if not models:
                return templates.TemplateResponse(
                    request, "partials/error.html",
                    context={"error": f"No models found on {engine}"},
                )
            model = models[0]["name"]

        result = run_bench_via_api(
            engine=engine,
            model=model,
            base_url=_get_server_url(engine),
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
):
    """HTMX endpoint for prompt — returns partial HTML."""
    try:
        if not model:
            models = discover_models(engine, _get_server_url(engine))
            if not models:
                return templates.TemplateResponse(
                    request, "partials/error.html",
                    context={"error": f"No models found on {engine}"},
                )
            model = models[0]["name"]

        result = run_prompt_via_api(
            engine=engine,
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            base_url=_get_server_url(engine),
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
