#!/usr/bin/env python3
"""
Prompt testing script for llm-benchmark-ct.
Phase 2: Send prompts to HLH/PLH llama.cpp servers and capture results.

Usage:
    python3 run_prompt_test.py --engine PLH --model gemma-4-E4B-it-Q4_K_M.gguf
    python3 run_prompt_test.py --engine PLH --model gemma-4-E4B-it-Q4_K_M.gguf --prompt "Hello world"
    python3 run_prompt_test.py --engine PLH --model gemma-4-E4B-it-Q4_K_M.gguf --prompt-file prompts.txt
    python3 run_prompt_test.py --engine PLH --model gemma-4-E4B-it-Q4_K_M.gguf --repeat 5
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

from openai import OpenAI


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(REPO_DIR, "config", "engines.json")

# Server URLs (OpenAI-compatible API endpoints)
SERVER_URLS = {
    "PLH": "http://127.0.0.1:80",
    "HLH": "http://192.168.1.12:80",
}

# Default test prompt
DEFAULT_PROMPT = "Write a concise 2-sentence summary of the history of artificial intelligence."


def load_config() -> dict:
    """Load engine configuration from config/engines.json."""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Prompt Test
# ---------------------------------------------------------------------------

def run_prompt_test(
    engine: str,
    model: str,
    prompt: str = DEFAULT_PROMPT,
    repeat: int = 1,
    max_tokens: int = 128,
) -> dict:
    """Send a prompt to the llama-server and capture results.

    Args:
        engine: Engine name (PLH or HLH)
        model: Model filename
        prompt: The prompt text to send
        repeat: Number of times to repeat the test
        max_tokens: Maximum tokens to generate

    Returns:
        Structured result dict
    """
    server_url = SERVER_URLS[engine]
    model_path = f"/srv/ai/models/{model}"

    # Create OpenAI client pointing to the llama-server
    client = OpenAI(
        api_key="not-needed",  # llama-server doesn't use API keys
        base_url=server_url,
    )

    results = []

    for i in range(repeat):
        start_time = time.time()
        response = client.chat.completions.create(
            model=model_path,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        elapsed = time.time() - start_time

        # Extract data from response
        # Some models (e.g., Gemma 4 with reasoning) put content in reasoning_content
        # when hitting max_tokens. Fall back if content is empty.
        msg = response.choices[0].message
        content = msg.content
        if not content:
            reasoning = getattr(msg, "reasoning_content", None)
            if reasoning:
                content = str(reasoning)
        usage = response.usage
        timings = response.model_extra.get("timings", {}) if hasattr(response, "model_extra") else {}

        # If model_extra doesn't work, try to access via raw dict
        if not timings:
            # OpenAI response may have raw data accessible differently
            # Fall back to timing-based calculation
            timings = {}

        result = {
            "engine": engine,
            "model_name": model,
            "model_path": model_path,
            "prompt": prompt[:100] + ("..." if len(prompt) > 100 else ""),
            "response": content,
            "latency_ms": round(elapsed * 1000, 2),
            "output_tokens": usage.completion_tokens if usage else 0,
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
            "prompt_latency_ms": round(timings.get("prompt_ms", elapsed * 1000), 2),
            "generation_latency_ms": round(timings.get("predicted_ms", 0), 2),
            "tokens_per_second": round(
                (usage.completion_tokens / elapsed) if usage and elapsed > 0 else 0, 2
            ),
            "repeat": i + 1,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        results.append(result)

    return {
        "test_type": "prompt",
        "engine": engine,
        "model_name": model,
        "prompt": prompt,
        "repeats": repeat,
        "results": results,
        "summary": {
            "avg_latency_ms": round(sum(r["latency_ms"] for r in results) / len(results), 2),
            "avg_output_tokens": round(sum(r["output_tokens"] for r in results) / len(results), 2),
            "avg_tokens_per_second": round(
                sum(r["tokens_per_second"] for r in results) / len(results), 2
            ),
            "total_tokens_generated": sum(r["output_tokens"] for r in results),
        },
    }


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run prompt tests against HLH/PLH llama.cpp servers"
    )
    parser.add_argument(
        "--engine", "-e", required=True, choices=["PLH", "HLH"],
        help="Target engine (PLH or HLH)"
    )
    parser.add_argument(
        "--model", "-m", required=True,
        help="Model filename (e.g., gemma-4-E4B-it-Q4_K_M.gguf)"
    )
    parser.add_argument(
        "--prompt", "-p", default=DEFAULT_PROMPT,
        help="Prompt text to send (default: history of AI)"
    )
    parser.add_argument(
        "--prompt-file", "-f", default=None,
        help="File containing prompt(s), one per line"
    )
    parser.add_argument(
        "--repeat", "-r", type=int, default=1,
        help="Number of times to repeat the test (default: 1)"
    )
    parser.add_argument(
        "--max-tokens", type=int, default=128,
        help="Maximum tokens to generate (default: 128)"
    )
    parser.add_argument(
        "--discover", "-d", action="store_true",
        help="List available models on the engine and exit"
    )

    args = parser.parse_args()

    config = load_config()

    if args.discover:
        try:
            models_resp = json.loads(
                __import__("urllib.request").urlopen(
                    f"{SERVER_URLS[args.engine]}/v1/models", timeout=10
                ).read().decode()
            )
            model_list = [m["id"] for m in models_resp.get("data", [])]
            print(json.dumps({"engine": args.engine, "models": model_list}, indent=2))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.exit(1)
        return

    # Load prompts from file if specified
    if args.prompt_file:
        with open(args.prompt_file, "r") as f:
            prompts = [line.strip() for line in f if line.strip()]
        if not prompts:
            print(json.dumps({"error": "No prompts found in file"}))
            sys.exit(1)
        # Run test for each prompt
        all_results = []
        for prompt in prompts:
            try:
                result = run_prompt_test(
                    engine=args.engine,
                    model=args.model,
                    prompt=prompt,
                    repeat=args.repeat,
                    max_tokens=args.max_tokens,
                )
                all_results.append(result)
            except Exception as e:
                print(json.dumps({"error": f"Failed for prompt: {prompt[:50]}... {str(e)}"}), file=sys.stderr)
        print(json.dumps(all_results, indent=2))
    else:
        try:
            result = run_prompt_test(
                engine=args.engine,
                model=args.model,
                prompt=args.prompt,
                repeat=args.repeat,
                max_tokens=args.max_tokens,
            )
            print(json.dumps(result, indent=2))
        except Exception as e:
            error_result = {
                "error": str(e),
                "engine": args.engine,
                "model": args.model,
            }
            print(json.dumps(error_result, indent=2), file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
