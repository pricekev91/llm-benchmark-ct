"""
Models and configuration for llm-benchmark-ct.

Provides:
- Engine configuration loading
- Model discovery via llama-server API
- Server URLs for each engine
"""

import json
import os
import re
import urllib.request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

import paramiko


def _format_timestamp() -> str:
    """Return current timestamp in EST, 12-hour format with seconds: '2026-07-16 07:50:45 PM EDT'."""
    try:
        eastern = ZoneInfo("US/Eastern")
    except Exception:
        eastern = timezone(timedelta(hours=-5))
    now = datetime.now(eastern)
    return now.strftime("%Y-%m-%d %I:%M:%S %p %Z")

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

# Default context sizes (suggested options for the UI)
CTX_SIZES = [512, 1024, 2048, 4096, 8192, 131072]

# MTP options
MTP_OPTIONS = list(range(7))  # 0-6


def load_config() -> dict:
    """Load engine configuration from config/engines.json."""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Filename Metadata Parsing
# ---------------------------------------------------------------------------

def _parse_model_filename(filename: str) -> dict:
    """Extract quantization, MTP level, and estimated context size from model filename.

    Args:
        filename: Model filename (e.g. "Qwen3.6-35B-A3B-MTP-Q4_K_M.gguf")

    Returns:
        Dict with quantization, mtp, context_size
    """
    name = filename.replace(".gguf", "")

    # Quantization: Q2_K, Q3_K_S, Q3_K_M, Q4_0, Q4_K_M, Q4_K_S, Q5_0, Q5_K_M,
    #              Q5_K_S, Q6_K, Q8_0
    quant = "unknown"
    quant_pattern = r'(Q[2-8]_?(?:K_[MS])?|Q[2-8]_0)'
    match = re.search(quant_pattern, name)
    if match:
        quant = match.group(1)

    # MTP: MTP-0 through MTP-6 or MTP-3 style
    mtp = 0
    mtp_pattern = r'MTP[-–]?\s*(\d+)'
    match = re.search(mtp_pattern, name)
    if match:
        mtp = min(int(match.group(1)), 6)

    # Estimated context size from model parameter count
    ctx = 8192  # default
    size_pattern = r'(\d+)B'
    match = re.search(size_pattern, name)
    if match:
        size = int(match.group(1))
        if size <= 3:
            ctx = 32768
        elif size <= 14:
            ctx = 8192
        elif size <= 35:
            ctx = 8192
        else:  # 36B+
            ctx = 131072

    return {"quantization": quant, "mtp": mtp, "context_size": ctx}


# ---------------------------------------------------------------------------
# SSH-based Model Discovery
# ---------------------------------------------------------------------------

def _ssh_to_engine(engine: str) -> paramiko.SSHClient:
    """Create SSH connection to engine using the configured key.

    Returns:
        paramiko.SSHClient or None if key is unavailable
    """
    try:
        config = load_config()
    except Exception:
        return None

    engine_cfg = config["engines"].get(engine)
    if not engine_cfg:
        return None

    host = engine_cfg["hostname"]
    ssh_key_path = engine_cfg.get("ssh_key", "")

    if not ssh_key_path or not os.path.exists(ssh_key_path):
        return None

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            username=engine_cfg.get("ssh_user", "root"),
            key_filename=ssh_key_path,
            timeout=10,
            allow_agent=False,
        )
    except Exception:
        client.close()
        return None

    return client


def discover_models_ssh(engine: str) -> list[dict]:
    """Discover models by SSH-ing to engine and scanning /srv/ai/models/*.gguf.

    Args:
        engine: Engine name (HLH or PLH)

    Returns:
        List of model dicts with id, name, quantization, mtp, etc.
    """
    client = _ssh_to_engine(engine)
    if not client:
        return []

    try:
        stdin, stdout, stderr = client.exec_command(
            "find /srv/ai/models -maxdepth 1 -name '*.gguf' -type f 2>/dev/null | sort"
        )
        output = stdout.read().decode().strip()
    except Exception:
        return []
    finally:
        client.close()

    if not output:
        return []

    models = []
    for line in output.split("\n"):
        if not line.strip():
            continue
        model_file = os.path.basename(line.strip())
        meta = _parse_model_filename(model_file)
        display_name = model_file.replace(".gguf", "")
        extra = ""
        if meta["mtp"] > 0:
            extra += f" (MTP-{meta['mtp']})"
        if meta["quantization"] != "unknown":
            extra += f", {meta['quantization']}"

        models.append({
            "id": model_file,
            "name": f"{display_name}{extra}",
            "model_file": model_file,
            "model_path": f"/srv/ai/models/{model_file}",
            "quantization": meta["quantization"],
            "mtp": meta["mtp"],
            "context_size": meta["context_size"],
        })

    return models


# ---------------------------------------------------------------------------
# Model Discovery (public API)
# ---------------------------------------------------------------------------

def discover_models(engine: str, base_url: Optional[str] = None) -> list[dict]:
    """Discover available models.

    Tries SSH-based filesystem scanning first (lists all GGUF files on disk).
    Falls back to llama-server /v1/models API if SSH is unavailable.

    Args:
        engine: Engine name (PLH or HLH)
        base_url: Override base URL (for container vs laptop testing)

    Returns:
        List of model dicts with id, name, and metadata
    """
    # Try SSH-based discovery first (filesystem listing)
    ssh_models = discover_models_ssh(engine)
    if ssh_models:
        return ssh_models

    # Fall back to llama-server API
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

def run_bench_via_api(
    engine: str,
    model: str,
    base_url: Optional[str] = None,
    ctx_size: int = 8192,
    mtp: int = 0,
) -> dict:
    """Run a quick benchmark via llama-server API.

    Args:
        engine: Engine name (PLH or HLH)
        model: Model filename
        base_url: Override base URL
        ctx_size: Context window size to use for prompt
        mtp: Multi-token prediction level (0-6)
    """
    url = base_url or SERVER_URLS.get(engine, SERVER_URLS["HLH"])
    model_path = get_model_path(engine, model)

    # Build prompt to match desired context size
    # ~6 chars per token, so target ctx_size tokens worth of text
    chars_per_token = 4
    target_chars = ctx_size * chars_per_token
    base_text = "The sky is blue because of the scattering of sunlight by molecules in the atmosphere. "
    repeat_count = max(1, target_chars // len(base_text))
    prompt = base_text * repeat_count

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
        "context_size": ctx_size,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "generated_tokens": gen_tokens,
        "mtp": mtp,
        "eval_ms": round(timings.get("predicted_ms", 0), 2),
        "prompt_eval_ms": round(timings.get("prompt_ms", 0), 2),
        "latency_ms": round(elapsed_ms, 2),
        "timestamp": _format_timestamp(),
    }


def run_prompt_via_api(
    engine: str,
    model: str,
    prompt: str = "Write a concise 2-sentence summary of the history of artificial intelligence.",
    max_tokens: int = 128,
    base_url: Optional[str] = None,
    ctx_size: int = 8192,
    mtp: int = 0,
) -> dict:
    """Run a single prompt test via llama-server API.

    Args:
        engine: Engine name (PLH or HLH)
        model: Model filename
        prompt: User prompt text
        max_tokens: Max generation tokens
        base_url: Override base URL
        ctx_size: Context window size
        mtp: Multi-token prediction level (0-6)
    """
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
        "ctx_size": ctx_size,
        "mtp": mtp,
        "timestamp": _format_timestamp(),
    }
