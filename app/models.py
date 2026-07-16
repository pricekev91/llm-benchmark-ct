"""
Models and configuration for llm-benchmark-ct.

Provides:
- Engine configuration loading
- Model discovery via llama-server API
- Server URLs for each engine
"""

import json
import os
import urllib.request
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(REPO_DIR, "config", "engines.json")

# Server URLs
# HLH: reachable via macvlan from the benchmark container
# PLH: accessible from laptop via lxc exec; from container we use a helper
SERVER_URLS = {
    "PLH": "http://127.0.0.1:80",        # PLH llama-server (laptop / LXC)
    "HLH": "http://192.168.1.12:80",      # HLH llama-server API (macvlan)
}


def load_config() -> dict:
    """Load engine configuration from config/engines.json."""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Model Discovery
# ---------------------------------------------------------------------------

def discover_models(engine: str, base_url: Optional[str] = None) -> list[dict]:
    """Discover available models via llama-server /v1/models endpoint.

    Args:
        engine: Engine name (PLH or HLH)
        base_url: Override base URL (for container vs laptop testing)

    Returns:
        List of model dicts with id, name, and metadata
    """
    url = base_url or SERVER_URLS.get(engine, SERVER_URLS["HLH"])
    models_url = f"{url}/v1/models"

    try:
        req = urllib.request.Request(models_url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        models = []
        for m in data.get("data", []):
            model_id = m.get("id", m.get("name", "unknown"))
            models.append({
                "id": model_id,
                "name": os.path.basename(model_id),
                "size": m.get("size", 0),
                "quantization": m.get("meta", {}).get("ftype", "unknown"),
                "params": m.get("meta", {}).get("n_params", 0),
                "context": m.get("meta", {}).get("n_ctx", 0),
            })
        return models

    except Exception as e:
        print(f"Warning: Could not discover models from {models_url}: {e}")
        return []


def discover_models_from_config(engine: str) -> list[dict]:
    """Discover models using the config file's server URLs."""
    return discover_models(engine)


def get_model_path(engine: str, model_name: str) -> str:
    """Get full model path for a given engine and model name.

    Args:
        engine: Engine name (PLH or HLH)
        model_name: Model filename or full path

    Returns:
        Full model path string
    """
    if model_name.startswith("/"):
        return model_name
    return f"/srv/ai/models/{model_name}"


# ---------------------------------------------------------------------------
# Benchmark & Prompt Helpers
# ---------------------------------------------------------------------------

def run_bench_via_api(engine: str, model: str, base_url: Optional[str] = None) -> dict:
    """Run a quick benchmark via llama-server API.

    Uses a fixed prompt for consistent benchmarking.
    """
    url = base_url or SERVER_URLS.get(engine, SERVER_URLS["HLH"])
    model_path = get_model_path(engine, model)
    prompt = "The sky is blue because of the scattering of sunlight by molecules in the atmosphere. " * 5

    bench_req = urllib.request.Request(
        f"{url}/v1/chat/completions",
        data=json.dumps({
            "model": model_path,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 128,
            "temperature": 0.7,
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = datetime.now(timezone.utc)
    with urllib.request.urlopen(bench_req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    usage = data.get("usage", {})
    timings = data.get("timings", {})
    gen_tokens = usage.get("completion_tokens", 0)
    gen_tok_s = gen_tokens / (elapsed_ms / 1000) if elapsed_ms > 0 else 0

    return {
        "engine": engine,
        "model": model,
        "model_path": model_path,
        "tok_s": round(gen_tok_s, 2),
        "context_size": 512,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "generated_tokens": gen_tokens,
        "eval_ms": round(timings.get("predicted_ms", 0), 2),
        "prompt_eval_ms": round(timings.get("prompt_ms", 0), 2),
        "latency_ms": round(elapsed_ms, 2),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def run_prompt_via_api(
    engine: str,
    model: str,
    prompt: str = "Write a concise 2-sentence summary of the history of artificial intelligence.",
    max_tokens: int = 128,
    base_url: Optional[str] = None,
) -> dict:
    """Run a single prompt test via llama-server API."""
    url = base_url or SERVER_URLS.get(engine, SERVER_URLS["HLH"])
    model_path = get_model_path(engine, model)

    chat_req = urllib.request.Request(
        f"{url}/v1/chat/completions",
        data=json.dumps({
            "model": model_path,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = datetime.now(timezone.utc)
    with urllib.request.urlopen(chat_req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    msg = data.get("choices", [{}])[0].get("message", {})
    # Content fallback: some reasoning models (Gemma-4) use reasoning_content
    content = msg.get("content", "")
    if not content:
        reasoning = msg.get("reasoning_content", "")
        if reasoning:
            content = reasoning

    usage = data.get("usage", {})
    timings = data.get("timings", {})

    return {
        "engine": engine,
        "model_name": model,
        "model_path": model_path,
        "prompt": prompt[:200],
        "response": content,
        "latency_ms": round(elapsed_ms, 2),
        "output_tokens": usage.get("completion_tokens", 0),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "tokens_per_second": round(
            usage.get("completion_tokens", 0) / (elapsed_ms / 1000), 2
        ) if elapsed_ms > 0 else 0,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
