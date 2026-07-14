# backend/endpoints.py
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from . import schemas
from .db import (
    fetch_all_endpoints, save_endpoint, delete_endpoint,
    fetch_all_presets, save_preset,
    fetch_benchmark_runs, fetch_benchmark_run,
    fetch_comparison_stats, fetch_trends,
    fetch_endpoint_by_id,
)
from .benchmark import run_full_benchmark_flow

# --- Routers ---
config_router = APIRouter(prefix="/endpoints", tags=["endpoints"])
preset_router = APIRouter(prefix="/presets", tags=["presets"])
benchmark_router = APIRouter(prefix="/benchmark", tags=["benchmark"])
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])

# --- Endpoint Config Routes ---

@config_router.get("/list")
def list_endpoint_configs():
    """Lists all endpoint configurations from the database."""
    endpoints = fetch_all_endpoints()
    return {"endpoints": endpoints}


@config_router.post("/save")
def save_endpoint_config(config: schemas.EndpointConfigSchema):
    """Saves or updates an endpoint configuration."""
    save_endpoint(config.model_dump())
    return {"message": f"Endpoint '{config.name}' saved.", "id": config.id, "status": "success"}


@config_router.delete("/{endpoint_id}")
def delete_endpoint_config(endpoint_id: str):
    """Deletes an endpoint configuration."""
    if not delete_endpoint(endpoint_id):
        raise HTTPException(status_code=404, detail=f"Endpoint '{endpoint_id}' not found.")
    return {"message": f"Endpoint '{endpoint_id}' deleted.", "status": "success"}


@config_router.get("/models/list")
def list_model_configs():
    """Lists available LLM models based on configured endpoints."""
    endpoints = fetch_all_endpoints()

    # Map providers to known models
    provider_models = {
        "OpenAI": ["GPT-4o", "GPT-4o-mini", "GPT-3.5-turbo"],
        "llama.cpp": ["Llama-3-8B-Instruct", "Llama-3-70B-Instruct", "Mistral-7B-Instruct"],
        "LiteLLM": ["claude-3-sonnet", "claude-3-haiku", "gpt-4o"],
        "llama-swap": ["Llama-3-8B", "Llama-2-13B", "Mixtral-8x7B"],
        "vLLM": ["Llama-3-8B-Instruct", "Qwen-2-7B", "Mistral-7B"],
    }

    models = []
    seen_providers = set()
    for ep in endpoints:
        provider = ep.get("provider", "OpenAI")
        if provider not in seen_providers:
            seen_providers.add(provider)
            for model_name in provider_models.get(provider, [f"{provider}-default"]):
                models.append({
                    "id": f"model_{provider.lower()}_{model_name.replace('-', '_')}",
                    "name": model_name,
                    "provider": provider,
                    "endpoint_id": ep["id"],
                })

    return {"models": models}


# --- Preset Routes ---

@preset_router.get("/list")
def list_prompt_presets():
    """Lists all prompt presets from the database."""
    presets = fetch_all_presets()
    return {"presets": presets}


@preset_router.post("/save")
def save_prompt_preset(preset: schemas.PromptPresetSchema):
    """Saves a new prompt preset."""
    save_preset(preset.model_dump())
    return {"message": f"Preset '{preset.name}' saved.", "id": preset.id, "status": "success"}


# --- Benchmark Routes ---

@benchmark_router.post("/run")
def run_benchmark(request_body: schemas.BenchmarkRunRequest):
    """Initiates and runs the full benchmark flow."""
    endpoint_id = request_body.endpoint_id
    model_id = request_body.model_id
    prompt_text = request_body.prompt_text
    max_tokens = request_body.max_tokens

    # Fetch endpoint from DB
    ep = fetch_endpoint_by_id(endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail=f"Endpoint '{endpoint_id}' not found.")

    try:
        benchmark_run, metrics = run_full_benchmark_flow(
            endpoint_id=endpoint_id,
            model_id=model_id,
            prompt_text=prompt_text,
            max_tokens=max_tokens,
            endpoint_data=ep,
            model_name_override=request_body.model_name,
        )

        return {
            "status": "success",
            "message": "Benchmark completed.",
            "run_data": benchmark_run.to_dict(),
            "metrics": metrics,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Benchmark failed: {str(e)}")


# --- Analytics / History Routes ---

@analytics_router.get("/history/filter")
def filter_history(
    model_name: Optional[str] = Query(None),
    endpoint_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
):
    """Filters benchmark runs from the database."""
    filters = {}
    if model_name:
        filters["model_name"] = model_name
    if endpoint_id:
        filters["endpoint_id"] = endpoint_id
    if start_date:
        filters["start_date"] = start_date
    if end_date:
        filters["end_date"] = end_date
    if limit:
        filters["limit"] = limit

    runs = fetch_benchmark_runs(filters if filters else None)
    return {"runs": runs, "count": len(runs)}


@analytics_router.get("/run/{run_id}")
def get_run(run_id: str):
    """Fetch a single benchmark run by ID."""
    run = fetch_benchmark_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return {"run": run}


@analytics_router.get("/compare/run")
def compare_run(model_name: str):
    """Compares a model's runs against historical averages."""
    stats = fetch_comparison_stats(model_name)
    return {"comparison": stats, "model_name": model_name}


@analytics_router.get("/compare/trends")
def trends_data(model_name: str):
    """Returns latency trends over time for a model."""
    trends = fetch_trends(model_name)
    return {"trends": trends, "model_name": model_name}
