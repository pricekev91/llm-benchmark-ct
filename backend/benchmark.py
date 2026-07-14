# backend/benchmark.py
import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

from .models import BenchmarkRun, EndpointConfig
from .openai_compat import get_llm_adapter
from .db import save_benchmark_run, fetch_endpoint_by_id


def execute_benchmark(endpoint_data: Dict[str, Any], model_name: str,
                      prompt_text: str, max_tokens: int) -> Tuple[BenchmarkRun, Dict[str, Any]]:
    """
    Executes the benchmark against a specific model/endpoint combination.
    Returns (BenchmarkRun, raw_metrics).
    """
    # Build adapter config from endpoint data
    adapter_config = {
        "provider": endpoint_data.get("provider", "OpenAI"),
        "base_url": endpoint_data.get("base_url", ""),
        "api_key": endpoint_data.get("api_key", ""),
        "model_name": model_name,
    }

    # Initialize adapter
    try:
        adapter = get_llm_adapter(adapter_config)
    except ValueError as e:
        raise Exception(f"Configuration error: {e}")

    # Run query and capture metrics
    try:
        raw_metrics = adapter.query(prompt_text, max_tokens)
    except Exception as e:
        raise Exception(f"Benchmark failed during execution: {e}")

    # Create BenchmarkRun object
    run_id = str(uuid.uuid4())
    response_text = raw_metrics.get("response_text", "")
    latency_ms = raw_metrics.get("latency_ms", 0)
    tokens = raw_metrics.get("tokens_generated", 0)
    output_length = raw_metrics.get("output_length", len(response_text))
    throughput = raw_metrics.get("throughput_tps", 0)

    benchmark_run = BenchmarkRun(
        run_id=run_id,
        model_name=model_name,
        endpoint_id=endpoint_data.get("id", "unknown"),
        prompt_text=prompt_text,
        response_text=response_text,
        latency_ms=latency_ms,
        tokens_generated=tokens,
        output_length=output_length,
        throughput_tps=throughput,
        timestamp=datetime.now(),
    )

    return benchmark_run, raw_metrics


def run_full_benchmark_flow(
    endpoint_id: str,
    model_id: str,
    prompt_text: str,
    max_tokens: int,
    endpoint_data: Optional[Dict[str, Any]] = None,
    model_name_override: Optional[str] = None,
) -> Tuple[BenchmarkRun, Dict[str, Any]]:
    """High-level orchestrator function for a full benchmark flow."""

    # Fetch endpoint from DB if not provided
    if endpoint_data is None:
        endpoint_data = fetch_endpoint_by_id(endpoint_id)
        if not endpoint_data:
            raise Exception(f"Endpoint '{endpoint_id}' not found.")

    # Determine model name
    model_name = model_name_override or model_id

    print(f"[Benchmark] Running {model_name} on endpoint {endpoint_data.get('name', endpoint_id)}...")

    # 1. Execute benchmark
    benchmark_run, metrics = execute_benchmark(
        endpoint_data=endpoint_data,
        model_name=model_name,
        prompt_text=prompt_text,
        max_tokens=max_tokens,
    )

    # 2. Save to DB
    save_benchmark_run(benchmark_run.to_dict())

    # 3. Return results
    return benchmark_run, metrics
