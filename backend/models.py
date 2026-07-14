# backend/models.py
from datetime import datetime
from typing import Optional


class PromptPreset:
    def __init__(self, id: str, name: str, template: str, category: str = "general"):
        self.id = id
        self.name = name
        self.template = template
        self.category = category

    def to_dict(self):
        return {"id": self.id, "name": self.name, "template": self.template, "category": self.category}


class EndpointConfig:
    def __init__(self, id: str, name: str, base_url: str, provider: str = "OpenAI", api_key: str = ""):
        self.id = id
        self.name = name
        self.base_url = base_url
        self.provider = provider
        self.api_key = api_key

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "base_url": self.base_url,
            "provider": self.provider, "api_key": self.api_key
        }


class ModelConfig:
    def __init__(self, id: str, name: str, provider: str):
        self.id = id
        self.name = name
        self.provider = provider

    def to_dict(self):
        return {"id": self.id, "name": self.name, "provider": self.provider}


class BenchmarkRun:
    def __init__(
        self, run_id: str, model_name: str, endpoint_id: str,
        prompt_text: str, response_text: str = "",
        latency_ms: Optional[float] = None,
        tokens_generated: Optional[int] = None,
        output_length: int = 0,
        throughput_tps: Optional[float] = None,
        timestamp: Optional[datetime] = None,
        prompt_preset_id: Optional[str] = None
    ):
        self.run_id = run_id
        self.model_name = model_name
        self.endpoint_id = endpoint_id
        self.prompt_text = prompt_text
        self.response_text = response_text
        self.latency_ms = latency_ms
        self.tokens_generated = tokens_generated
        self.output_length = output_length
        self.throughput_tps = throughput_tps
        self.timestamp = timestamp or datetime.utcnow()
        self.prompt_preset_id = prompt_preset_id

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "model_name": self.model_name,
            "endpoint_id": self.endpoint_id,
            "prompt_text": self.prompt_text,
            "response_text": self.response_text,
            "latency_ms": self.latency_ms,
            "tokens_generated": self.tokens_generated,
            "output_length": self.output_length,
            "throughput_tps": self.throughput_tps,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "prompt_preset_id": self.prompt_preset_id,
        }
