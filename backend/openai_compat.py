# backend/openai_compat.py
import time
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


class LLMAdapter:
    """Abstract Base Class (Interface) for all LLM service adapters."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = config.get("provider", "unknown")
        self.base_url = config.get("base_url", "")
        self.api_key = config.get("api_key", "")
        self.model_name = config.get("model_name", "gpt-3.5-turbo")
        print(f"[Adapter] Initialized {self.provider} adapter for model={self.model_name}")

    def query(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        raise NotImplementedError("Query method must be implemented by a subclass.")


# --- OpenAI / OpenAI-Compatible Adapter ---
class OpenAIAdapter(LLMAdapter):
    """Adapter for OpenAI API and any OpenAI-compatible endpoint."""

    def query(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": False,
        }

        start_time = time.time()
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "response_text": f"ERROR: {str(e)}",
                "latency_ms": elapsed_ms,
                "tokens_generated": 0,
                "output_length": 0,
                "throughput_tps": 0,
            }

        elapsed_ms = (time.time() - start_time) * 1000
        content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = raw.get("usage", {})
        tokens = usage.get("total_tokens", usage.get("completion_tokens", 0))
        output_len = len(content)
        throughput = round((tokens / elapsed_ms) * 1000, 2) if elapsed_ms > 0 else 0

        return {
            "response_text": content,
            "latency_ms": round(elapsed_ms, 2),
            "tokens_generated": tokens,
            "output_length": output_len,
            "throughput_tps": throughput,
        }


# --- llama.cpp Adapter ---
class LlamaCppAdapter(LLMAdapter):
    """Adapter for llama.cpp server (OpenAI-compatible or native)."""

    def query(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        # llama.cpp has a chat completions endpoint similar to OpenAI
        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": False,
        }

        start_time = time.time()
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "response_text": f"ERROR: {str(e)}",
                "latency_ms": elapsed_ms,
                "tokens_generated": 0,
                "output_length": 0,
                "throughput_tps": 0,
            }

        elapsed_ms = (time.time() - start_time) * 1000
        content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = raw.get("usage", {})
        tokens = usage.get("total_tokens", usage.get("completion_tokens", 0))
        output_len = len(content)
        throughput = round((tokens / elapsed_ms) * 1000, 2) if elapsed_ms > 0 else 0

        return {
            "response_text": content,
            "latency_ms": round(elapsed_ms, 2),
            "tokens_generated": tokens,
            "output_length": output_len,
            "throughput_tps": throughput,
        }


# --- LiteLLM Adapter ---
class LiteLLMAdapter(LLMAdapter):
    """Adapter for LiteLLM proxy (OpenAI-compatible interface)."""

    def query(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": False,
        }

        start_time = time.time()
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "response_text": f"ERROR: {str(e)}",
                "latency_ms": elapsed_ms,
                "tokens_generated": 0,
                "output_length": 0,
                "throughput_tps": 0,
            }

        elapsed_ms = (time.time() - start_time) * 1000
        content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = raw.get("usage", {})
        tokens = usage.get("total_tokens", usage.get("completion_tokens", 0))
        output_len = len(content)
        throughput = round((tokens / elapsed_ms) * 1000, 2) if elapsed_ms > 0 else 0

        return {
            "response_text": content,
            "latency_ms": round(elapsed_ms, 2),
            "tokens_generated": tokens,
            "output_length": output_len,
            "throughput_tps": throughput,
        }


# --- vLLM Adapter ---
class VLLMAdapter(LLMAdapter):
    """Adapter for vLLM server (OpenAI-compatible)."""

    def query(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": False,
        }

        start_time = time.time()
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "response_text": f"ERROR: {str(e)}",
                "latency_ms": elapsed_ms,
                "tokens_generated": 0,
                "output_length": 0,
                "throughput_tps": 0,
            }

        elapsed_ms = (time.time() - start_time) * 1000
        content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = raw.get("usage", {})
        tokens = usage.get("total_tokens", usage.get("completion_tokens", 0))
        output_len = len(content)
        throughput = round((tokens / elapsed_ms) * 1000, 2) if elapsed_ms > 0 else 0

        return {
            "response_text": content,
            "latency_ms": round(elapsed_ms, 2),
            "tokens_generated": tokens,
            "output_length": output_len,
            "throughput_tps": throughput,
        }


# --- Llama-Swap Adapter ---
class LlamaSwapAdapter(LLMAdapter):
    """Adapter for Llama-Swap service."""

    def query(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }

        start_time = time.time()
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "response_text": f"ERROR: {str(e)}",
                "latency_ms": elapsed_ms,
                "tokens_generated": 0,
                "output_length": 0,
                "throughput_tps": 0,
            }

        elapsed_ms = (time.time() - start_time) * 1000
        content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = raw.get("usage", {})
        tokens = usage.get("total_tokens", usage.get("completion_tokens", 0))
        output_len = len(content)
        throughput = round((tokens / elapsed_ms) * 1000, 2) if elapsed_ms > 0 else 0

        return {
            "response_text": content,
            "latency_ms": round(elapsed_ms, 2),
            "tokens_generated": tokens,
            "output_length": output_len,
            "throughput_tps": throughput,
        }


# --- Adapter Factory ---
ADAPTER_MAP = {
    "OpenAI": OpenAIAdapter,
    "openai": OpenAIAdapter,
    "llama.cpp": LlamaCppAdapter,
    "llama_cpp": LlamaCppAdapter,
    "LiteLLM": LiteLLMAdapter,
    "litellm": LiteLLMAdapter,
    "vLLM": VLLMAdapter,
    "vllm": VLLMAdapter,
    "llama-swap": LlamaSwapAdapter,
    "llama_swap": LlamaSwapAdapter,
}


def get_llm_adapter(config: Dict[str, Any]) -> LLMAdapter:
    """Factory function to instantiate the correct adapter based on provider."""
    provider = config.get("provider", "OpenAI")
    adapter_class = ADAPTER_MAP.get(provider)
    if not adapter_class:
        # Fall back to OpenAI-compatible adapter for unknown providers
        adapter_class = OpenAIAdapter
        print(f"[Adapter] Unknown provider '{provider}', falling back to OpenAI-compatible.")
    return adapter_class(config)
