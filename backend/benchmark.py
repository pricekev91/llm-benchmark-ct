# backend/benchmark.py
import uuid
from datetime import datetime
from typing import Dict, Any, Tuple

from .models import BenchmarkRun, EndpointConfig, ModelConfig
from .openai_compat import get_llm_adapter
from .db import get_db_connection

def execute_benchmark(endpoint_config: EndpointConfig, model_config: ModelConfig, prompt_text: str, max_tokens: int) -> Tuple[BenchmarkRun, Dict[str, Any]]:
    """
    Executes the benchmark against a specific model/endpoint combination.

    Returns:
        Tuple[BenchmarkRun, Dict[str, Any]] - The created run object and raw metrics.
    """
    
    # 1. Initialize Adapter
    try:
        adapter = get_llm_adapter(model_config.__dict__)
    except ValueError as e:
        raise Exception(f"Configuration Error: {e}")

    # 2. Run Query & Capture Raw Metrics
    try:
        raw_metrics = adapter.query(prompt_text, max_tokens)
    except Exception as e:
        print(f"Error during LLM query: {e}")
        raise Exception(f"Benchmark failed during execution: {e}")

    # 3. Create BenchmarkRun Object
    run_id = str(uuid.uuid4())
    
    benchmark_run = BenchmarkRun(
        run_id=run_id,
        model_name=model_config.name,
        endpoint_id=endpoint_config.id,
        prompt_text=prompt_text,
        response_text=raw_metrics.get("response_text", ""),
        latency_ms=raw_metrics.get("latency_ms"),
        tokens_generated=raw_metrics.get("tokens_generated"),
        output_length=raw_metrics.get("output_length", 0),
        timestamp=datetime.now()
    )
    
    return benchmark_run, raw_metrics

def save_run_to_db(run: BenchmarkRun):
    """Persists the completed benchmark run to the SQLite database."""
    conn = get_db_connection()
    if not conn:
        raise ConnectionError("Could not connect to database.")
    
    cursor = conn.cursor()
    
    # Map the run object to database parameters
    params = (
        run.run_id,
        run.model_name,
        run.endpoint_id,
        run.prompt_text,
        run.response_text,
        run.latency_ms,
        run.tokens_generated,
        run.output_length,
        run.timestamp
    )
    
    try:
        cursor.execute("""
            INSERT INTO benchmark_runs (
                run_id, model_name, endpoint_id, prompt_text, response_text, 
                latency_ms, tokens_generated, output_length, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, params)
        conn.commit()
        print(f"Successfully saved run ID: {run.run_id}")
    except Exception as e:
        print(f"Database save failed: {e}")
        raise
    finally:
        conn.close()

def run_full_benchmark_flow(endpoint_id: str, model_id: str, prompt_text: str, max_tokens: int):
    """High-level orchestrator function."""
    
    # --- STUB: In a real app, these would be fetched from configuration/DB ---
    # Simulation of fetching configs
    endpoint_config = EndpointConfig(id=endpoint_id, name="Test API", base_url="http://test.com")
    model_config = ModelConfig(id=model_id, name="GPT-4o", provider="OpenAI")
    
    print(f"Starting benchmark for {model_config.name} on endpoint {endpoint_config.name}...")
    
    # 1. Execute
    benchmark_run, metrics = execute_benchmark(endpoint_config, model_config, prompt_text, max_tokens)
    
    # 2. Save
    save_run_to_db(benchmark_run)
    
    return benchmark_run, metrics