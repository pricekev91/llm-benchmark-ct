# backend/endpoints.py
from fastapi import APIRouter, Depends, HTTPException
from . import schemas, auth
from .models import EndpointConfig, ModelConfig, BenchmarkRun, PromptPreset
from .db import get_db_connection
from .benchmark import run_full_benchmark_flow
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime
from typing import Optional

# --- Dependency Injection ---
def get_db():
    db = get_db_connection()
    if db:
        try:
            yield db
        finally:
            db.close()

# --- Endpoint Config Router ---
config_router = APIRouter(prefix="/endpoints", tags=["endpoints"])

@config_router.post("/save")
def save_endpoint_config(config: schemas.EndpointConfigSchema, db: Session = Depends(get_db)):
    """Saves a new endpoint configuration."""
    print(f"Saving endpoint: {config.name} at {config.base_url}")
    # In a real app, we would serialize config to a JSON file in the mounted volume.
    return {"message": "Endpoint configuration saved successfully (stub)"}

@config_router.get("/list")
def list_endpoint_configs(db: Session = Depends(get_db)):
    """Lists all available endpoint configurations."""
    print("Listing endpoint configurations (stub)")
    return {"endpoints": [EndpointConfig(id="e1", name="Test API", base_url="http://test.com")]}

@config_router.get("/models/list")
def list_model_configs():
    """Lists all available LLM models."""
    print("Listing models (stub)")
    return {"models": [ModelConfig(id="m1", name="GPT-4o", provider="OpenAI")]}

# --- Prompt Preset Router ---
preset_router = APIRouter(prefix="/presets", tags=["presets"])

@preset_router.post("/save")
def save_prompt_preset(preset: schemas.PromptPresetSchema, db: Session = Depends(get_db)):
    """Saves a new prompt preset."""
    print(f"Saving preset: {preset.name}")
    return {"message": "Prompt preset saved successfully (stub)"}

@preset_router.get("/list")
def list_prompt_presets(db: Session = Depends(get_db)):
    """Lists all available prompt presets."""
    print("Listing prompt presets (stub)")
    return {"presets": [PromptPreset(id="p1", name="Explain QC", template="Explain quantum computing simply.")]}


# --- Benchmark Router ---
benchmark_router = APIRouter(prefix="/benchmark", tags=["benchmark"])

@benchmark_router.post("/run")
def run_benchmark_endpoint(request_body: schemas.BenchmarkRunRequest):
    """
    Initiates and runs the full benchmark flow.
    """
    # 1. Resolve IDs (STUB: In production, these come from user input/DB lookup)
    endpoint_id = request_body.endpoint_id 
    model_id = request_body.model_id 
    prompt_text = request_body.prompt_text
    max_tokens = request_body.max_tokens
    
    # 2. Run the engine
    try:
        benchmark_run, metrics = run_full_benchmark_flow(endpoint_id, model_id, prompt_text, max_tokens)
        
        # 3. Return structured response
        return {
            "status": "success",
            "message": "Benchmark completed successfully.",
            "run_data": benchmark_run.to_dict(),
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- History and Comparison Router ---
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])

@analytics_router.get("/history/filter")
def filter_history(
    model: Optional[str] = None, 
    endpoint: Optional[str] = None, 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Filters benchmark runs based on criteria (model, endpoint, date range).
    Returns a list of BenchmarkRun objects.
    """
    print("Filtering benchmark history based on parameters.")
    # STUB: Actual SQL filtering logic would go here.
    if model and endpoint:
        return {"runs": [BenchmarkRun(
            run_id="h1", model_name=model, endpoint_id=endpoint, prompt_text="Test Prompt", 
            response_text="Result text", latency_ms=100.0, tokens_generated=10, output_length=20, timestamp=datetime.now())]
        }
    return {"runs": []}

@analytics_router.get("/compare/run")
def comparison_run(model_id: str, preset_id: str):
    """
    Compares a specified run against a historical average/baseline.
    """
    print(f"Comparing run for Model {model_id} vs Preset {preset_id}.")
    return {"comparison": "Model performance is 15% faster than historical average for this task."}

@analytics_router.get("/compare/trends")
def trends_data(model_id: str):
    """
    Returns trend data (e.g., latency over time) for a specific model.
    """
    print(f"Generating performance trends for Model {model_id}.")
    return {"trends": [{"date": "2026-07-01", "avg_latency": 1200.5}, {"date": "2026-07-13", "avg_latency": 1150.0}]}