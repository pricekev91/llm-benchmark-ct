# backend/models.py
from datetime import datetime
from typing import Optional

class PromptPreset:
    """Conceptual Model for a reusable prompt template."""
    def __init__(self, id: str, name: str, template: str):
        self.id = id
        self.name = name
        self.template = template

class EndpointConfig:
    """Conceptual Model for a configured API endpoint."""
    def __init__(self, id: str, name: str, base_url: str):
        self.id = id
        self.name = name
        self.base_url = base_url

class ModelConfig:
    """Conceptual Model for an LLM provider/model."""
    def __init__(self, id: str, name: str, provider: str):
        self.id = id
        self.name = name
        self.provider = provider

class BenchmarkRun:
    """Conceptual Model for a single benchmark run."""
    def __init__(self, run_id: str, model_name: str, endpoint_id: str, prompt_text: str, response_text: str, latency_ms: Optional[float], tokens_generated: Optional[int], output_length: int, timestamp: Optional[datetime]):
        self.run_id = run_id
        self.model_name = model_name
        self.endpoint_id = endpoint_id
        self.prompt_text = prompt_text
        self.response_text = response_text
        self.latency_ms = latency_ms
        self.tokens_generated = tokens_generated
        self.output_length = output_length
        self.timestamp = timestamp if timestamp else datetime.utcnow()

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
            "timestamp": self.timestamp.isoformat()
        }