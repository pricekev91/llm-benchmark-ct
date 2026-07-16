#!/usr/bin/env python3
"""
Remote llama.bench execution script.
Phase 1: full implementation with SSH/LXC execution, model discovery,
and output parsing. Supports two modes:
  1. llama-bench binary (HLH)
  2. llama-server API fallback (PLH, or any engine with a running server)
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

import paramiko


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(REPO_DIR, "config", "engines.json")


def load_config() -> dict:
    """Load engine configuration from config/engines.json."""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Model Discovery
# ---------------------------------------------------------------------------

def discover_models(engine: str, config: dict) -> list[str]:
    """Discover available GGUF models on a remote engine.

    Args:
        engine: Engine name (HLH or PLH)
        config: Parsed engines.json

    Returns:
        List of model filenames (basename only)
    """
    engine_cfg = config["engines"][engine]
    model_base = "/srv/ai/models"
    host = engine_cfg["hostname"]

    if engine == "PLH":
        cmd = (
            f"lxc exec plh-ai-engine --project prod -- "
            f"find {model_base} -name '*.gguf' -type f 2>/dev/null"
        )
    else:
        cmd = (
            f"ssh -i {engine_cfg['ssh_key']} -o StrictHostKeyChecking=no "
            f"{engine_cfg['ssh_user']}@{host} "
            f"find {model_base} -name '*.gguf' -type f 2>/dev/null"
        )

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Model discovery failed for {engine}: {result.stderr.strip()}")

    models = [os.path.basename(line.strip()) for line in result.stdout.strip().split("\n") if line.strip()]
    return models


def discover_models_full(engine: str, config: dict) -> list[dict]:
    """Discover models with full path info.

    Returns:
        List of dicts: {"name": "model.gguf", "path": "/srv/ai/models/model.gguf"}
    """
    models = discover_models(engine, config)
    return [{"name": m, "path": f"/srv/ai/models/{m}"} for m in models]


# ---------------------------------------------------------------------------
# Remote Execution Helpers
# ---------------------------------------------------------------------------

def run_remote_command(engine: str, command: str, retries: int = 2, timeout: int = 60) -> str:
    """Execute a command on a remote engine with retry logic.

    Args:
        engine: Engine name (HLH or PLH)
        command: Shell command to execute
        retries: Number of retries on failure
        timeout: Timeout per attempt in seconds

    Returns:
        stdout string from the command

    Raises:
        RuntimeError: On repeated failures
    """
    engine_cfg = load_config()["engines"][engine]
    host = engine_cfg["hostname"]
    last_error = None

    for attempt in range(1 + retries):
        try:
            if engine == "PLH":
                # PLH accessed via LXC exec on laptop
                full_cmd = (
                    f"lxc exec plh-ai-engine --project prod -- "
                    f"bash -c \"{command}\""
                )
            else:
                full_cmd = (
                    f"ssh -i {engine_cfg['ssh_key']} "
                    f"-o StrictHostKeyChecking=no "
                    f"-o ConnectTimeout=15 "
                    f"-o ServerAliveInterval=5 "
                    f"{engine_cfg['ssh_user']}@{host} "
                    f"'{command}'"
                )

            result = subprocess.run(
                full_cmd, shell=True, capture_output=True, text=True,
                timeout=timeout
            )
            if result.returncode == 0:
                return result.stdout
            else:
                last_error = result.stderr.strip()
                time.sleep(2 ** attempt)

        except subprocess.TimeoutExpired:
            last_error = "Command timed out"
            time.sleep(2 ** attempt)
        except Exception as e:
            last_error = str(e)
            time.sleep(2 ** attempt)

    raise RuntimeError(
        f"Failed to execute '{command}' on {engine} after "
        f"{1 + retries} attempt(s). Last error: {last_error}"
    )


# ---------------------------------------------------------------------------
# llama-bench Execution & Parsing
# ---------------------------------------------------------------------------

def _check_llama_server(engine: str) -> tuple[bool, str]:
    """Check if llama-server is running on a remote engine.

    Args:
        engine: Engine name (HLH or PLH)

    Returns:
        (is_running, base_url)
    """
    if engine == "PLH":
        try:
            req = urllib.request.Request(
                "http://127.0.0.1/v1/models",
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True, "http://127.0.0.1:80"
        except Exception:
            pass
    return False, ""


def run_llama_server_bench(engine: str, model: str) -> dict:
    """Benchmark via llama-server API (fallback when llama-bench binary is broken).

    Args:
        engine: Engine name (HLH or PLH)
        model: Model filename

    Returns:
        Structured benchmark result
    """
    model_path = f"/srv/ai/models/{model}"

    if engine == "PLH":
        server_url = "http://127.0.0.1:80"
    elif engine == "HLH":
        server_url = "http://192.168.1.12:80"
    else:
        raise RuntimeError(f"API benchmarking not configured for {engine}")

    # Benchmark: generation throughput (128 tokens)
    # Use a fixed prompt for consistent benchmarking
    prompt = "Write a 128 word story about a robot who learns to love poetry. " * 10
    prompt_tokens = len(prompt.split())

    gen_req = urllib.request.Request(
        f"{server_url}/v1/chat/completions",
        data=json.dumps({
            "model": model_path,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 128
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    start = time.time()
    # Allow up to 120s for large models (e.g., 35B on CPU)
    with urllib.request.urlopen(gen_req, timeout=120) as resp:
        gen_data = json.loads(resp.read().decode())
        elapsed_gen = time.time() - start

    gen_tokens = gen_data.get("usage", {}).get("completion_tokens", 0)
    gen_tok_s = gen_tokens / elapsed_gen if elapsed_gen > 0 else 0

    # Get prompt timing from usage data
    timings = gen_data.get("timings", {})
    prompt_eval_ms = timings.get("prompt_ms", elapsed_gen * 1000)
    eval_ms = timings.get("predicted_ms", elapsed_gen * 1000)

    return {
        "tok_s": round(gen_tok_s, 2),
        "eval_ms": round(eval_ms, 2),
        "prompt_eval_ms": round(prompt_eval_ms, 2),
    }


def run_llama_bench(engine: str, model: str) -> str:
    """Execute llama-bench on a remote engine.

    Args:
        engine: Engine name (HLH or PLH)
        model: Model filename

    Returns:
        Raw stdout from llama-bench
    """
    engine_cfg = load_config()["engines"][engine]
    model_path = f"/srv/ai/models/{model}"
    bench_cmd = (
        f"{engine_cfg['llama_bench_path']} "
        f"-m {model_path} "
        f"-t 4 "
        f"-n 512 "
        f"-ngl 99 "
        f"-p 512 "
        f"-n 128 "
        f"-b 1"
    )
    # Use short timeout - llama-bench should either work or fail quickly
    return run_remote_command(engine, bench_cmd, retries=2, timeout=30)


def parse_llama_bench_output(raw_output: str) -> dict:
    """Parse llama-bench stdout into structured metrics.

    llama-bench outputs a summary line at the end containing:
    tok/s: <value>, prompt_eval: <ms>ms, eval: <ms>ms

    Args:
        raw_output: stdout from llama-bench command

    Returns:
        Dict with parsed metrics
    """
    lines = raw_output.strip().split("\n")

    # Find the summary line - llama-bench outputs "tok/s:" or "eval:" lines
    tok_s = 0.0
    eval_ms = 0.0
    prompt_eval_ms = 0.0

    for line in lines:
        line_lower = line.lower().strip()

        # tok/s line (most common format)
        if "tok/s:" in line_lower or "tok/s:" in line:
            match = re.search(r'tok/s:\s*([\d.]+)', line, re.IGNORECASE)
            if match:
                tok_s = float(match.group(1))
                continue

        # eval time line
        if re.search(r'eval.*?:\s*\d+\s*ms', line_lower) or re.search(r'eval.*?time', line, re.IGNORECASE):
            match = re.search(r'([\d.]+)\s*ms', line)
            if match and 'prompt' not in line_lower:
                eval_ms = float(match.group(1))

        # prompt eval time
        if 'prompt' in line_lower and re.search(r'time.*?:\s*\d+\s*ms', line):
            match = re.search(r'([\d.]+)\s*ms', line)
            if match:
                prompt_eval_ms = float(match.group(1))

        # CSV-style output (llama-bench --output-format csv)
        if tok_s == 0 and ',' in line:
            parts = line.split(',')
            if len(parts) >= 2:
                try:
                    val = float(parts[-1].strip())
                    if val > 0:
                        tok_s = val
                except ValueError:
                    pass

    # Fallback: try to find any number that looks like tok/s
    if tok_s == 0:
        for line in lines:
            match = re.search(r'(\d+\.?\d*)\s*tok/s', line, re.IGNORECASE)
            if match:
                tok_s = float(match.group(1))
                break

    if tok_s == 0:
        raise RuntimeError(f"Could not parse tok/s from llama-bench output:\n{raw_output}")

    return {
        "tok_s": round(tok_s, 2),
        "eval_ms": round(eval_ms, 2),
        "prompt_eval_ms": round(prompt_eval_ms, 2),
    }


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def run_remote_bench(engine: str, model: str) -> dict:
    """Execute llama-bench on a remote engine and return structured results.

    Tries llama-bench binary first. If it fails, falls back to
    llama-server API benchmarking (for engines like PLH where
    the llama-bench binary is broken but llama-server works).

    Args:
        engine: Engine name (HLH or PLH)
        model: Model filename (e.g., "qwen2.5-7b-instruct-q4_k_m.gguf")

    Returns:
        Structured result dict matching the Phase 1 schema:
        {
            "engine": str,
            "model": str,
            "model_path": str,
            "tok_s": float,
            "context_size": int,
            "prompt_tokens": int,
            "generated_tokens": int,
            "timestamp": str
        }
    """
    config = load_config()
    engine_cfg = config["engines"][engine]
    model_path = f"/srv/ai/models/{model}"

    parsed = None
    source = "llama-bench"

    # Try llama-bench binary first
    try:
        raw_output = run_llama_bench(engine, model)
        parsed = parse_llama_bench_output(raw_output)
    except RuntimeError as e:
        # llama-bench failed — try API fallback
        source = "llama-server"
        print(f"llama-bench failed ({str(e)}), trying llama-server API...", file=sys.stderr)
        try:
            parsed = run_llama_server_bench(engine, model)
        except Exception as api_err:
            raise RuntimeError(
                f"Both llama-bench and llama-server API failed. "
                f"llama-bench: {str(e)}, llama-server: {str(api_err)}"
            )

    context_size = 512
    prompt_tokens = 512
    generated_tokens = 128

    return {
        "engine": engine,
        "model": model,
        "model_path": model_path,
        "tok_s": parsed["tok_s"],
        "context_size": context_size,
        "prompt_tokens": prompt_tokens,
        "generated_tokens": generated_tokens,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "eval_ms": parsed["eval_ms"],
        "prompt_eval_ms": parsed["prompt_eval_ms"],
        "benchmark_source": source,
    }


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run remote llama-bench on HLH or PLH engine"
    )
    parser.add_argument(
        "--engine", "-e", required=True, choices=["HLH", "PLH"],
        help="Target engine"
    )
    parser.add_argument(
        "--model", "-m", default=None,
        help="Model filename (if not provided, will use first available model)"
    )
    parser.add_argument(
        "--discover", "-d", action="store_true",
        help="List available models and exit"
    )

    args = parser.parse_args()

    config = load_config()

    if args.discover:
        models = discover_models_full(args.engine, config)
        print(json.dumps({"engine": args.engine, "models": models}, indent=2))
        return

    if args.model is None:
        models = discover_models(args.engine, config)
        if not models:
            print(json.dumps({"error": f"No GGUF models found on {args.engine}"}))
            sys.exit(1)
        args.model = models[0]
        print(f"Using first available model: {args.model}")

    try:
        result = run_remote_bench(args.engine, args.model)
        print(json.dumps(result, indent=2))
    except RuntimeError as e:
        error_result = {
            "engine": args.engine,
            "model": args.model,
            "error": str(e),
        }
        print(json.dumps(error_result, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
